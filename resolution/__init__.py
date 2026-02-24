from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from detection import SpatialIndex, evaluate_pair
from geometry import aabb_expand, normalize
from models import CandidateFix, Issue, Recommendation, SimResult
from resolution.high_impact_fix import (
    Clash,
    FixCandidate as HighImpactFixCandidate,
    HighImpactFixConfig,
    buildElementClashMap,
    buildElementDegree,
    evaluateTrialAgainstClashes,
    estimateNewClashes,
    findBestSingleMoveFixes,
    generateTranslationTrials,
    getHotElements,
    rankFixes,
    selectTopElementsByDegree,
)


AABB = Tuple[float, float, float, float, float, float]


def translate_aabb(aabb: AABB, vec: Tuple[float, float, float]) -> AABB:
    return (
        aabb[0] + vec[0],
        aabb[1] + vec[1],
        aabb[2] + vec[2],
        aabb[3] + vec[0],
        aabb[4] + vec[1],
        aabb[5] + vec[2],
    )


def _discipline_weight(discipline: str) -> float:
    weights = {
        "Electrical": 0.0,
        "Plumbing": 0.1,
        "Drainage": 0.2,
        "MEP": 0.2,
        "HVAC": 0.2,
        "Unknown": 0.3,
        "Structural": 1.0,
    }
    return weights.get(discipline, 0.3)


def _type_weight(ifc_type: str) -> float:
    hard = ("IfcWall", "IfcSlab", "IfcBeam", "IfcColumn")
    if ifc_type in hard:
        return 1.0
    return 0.0


def choose_movable(issue: Issue, elements: Dict[str, object]) -> Tuple[str, str, str]:
    a = elements.get(issue.guid_a)
    b = elements.get(issue.guid_b)
    if a is None and b is None:
        return issue.guid_b, "Unknown", "Unknown"
    if a is None:
        return issue.guid_b, getattr(b, "discipline", "Unknown"), getattr(b, "type", "Unknown")
    if b is None:
        return issue.guid_a, getattr(a, "discipline", "Unknown"), getattr(a, "type", "Unknown")

    wa = _discipline_weight(getattr(a, "discipline", "Unknown")) + _type_weight(getattr(a, "type", ""))
    wb = _discipline_weight(getattr(b, "discipline", "Unknown")) + _type_weight(getattr(b, "type", ""))
    if wa <= wb:
        return issue.guid_a, getattr(a, "discipline", "Unknown"), getattr(a, "type", "Unknown")
    return issue.guid_b, getattr(b, "discipline", "Unknown"), getattr(b, "type", "Unknown")


def _move_direction(issue: Issue, movable_guid: str) -> Tuple[float, float, float]:
    if not issue.direction or issue.direction == (0.0, 0.0, 0.0):
        return (1.0, 0.0, 0.0)
    if movable_guid == issue.guid_a:
        return issue.direction
    return (-issue.direction[0], -issue.direction[1], -issue.direction[2])


def generate_candidate_fixes(
    issue: Issue,
    respect: float,
    tolerance: float,
    movable_guid: str,
    discipline: str,
    ifc_type: str,
    steps_mm: List[int] | None = None,
) -> List[CandidateFix]:
    if steps_mm is None:
        steps_mm = [10, 25, 50]
    direction = normalize(_move_direction(issue, movable_guid))
    base = max(0.0, -issue.clearance)
    weight = _discipline_weight(discipline) + _type_weight(ifc_type)

    fixes: List[CandidateFix] = []
    for step in steps_mm:
        dist = base + (step / 1000.0)
        vec = (direction[0] * dist, direction[1] * dist, direction[2] * dist)
        cost = abs(dist) + weight
        fixes.append(
            CandidateFix(
                action="translate",
                params={"guid": movable_guid, "vector_m": vec, "vector_mm": (vec[0] * 1000, vec[1] * 1000, vec[2] * 1000)},
                cost=cost,
            )
        )
    return fixes


def simulate_fix(
    issue: Issue,
    fix: CandidateFix,
    aabbs: Dict[str, AABB],
    index: SpatialIndex,
    respect: float,
    tolerance: float,
    neighbor_radius: float = 2.0,
    max_offset_m: float = 0.5,
) -> SimResult:
    vec = fix.params.get("vector_m", (0.0, 0.0, 0.0))
    moved_guid = fix.params.get("guid")
    moved_aabb = translate_aabb(aabbs[moved_guid], vec)
    solved = 0
    creates = 0
    violations = 0
    if (vec[0] ** 2 + vec[1] ** 2 + vec[2] ** 2) ** 0.5 > max_offset_m:
        violations = 1

    # Check original issue
    eval_issue = evaluate_pair(
        issue.guid_a,
        issue.guid_b,
        aabbs[issue.guid_a] if issue.guid_a != moved_guid else moved_aabb,
        aabbs[issue.guid_b] if issue.guid_b != moved_guid else moved_aabb,
        respect,
        tolerance,
        issue.rule_id,
        issue.severity,
    )
    if eval_issue.clearance >= 0:
        solved = 1
    else:
        violations = 1

    # Check neighbors
    query = aabb_expand(moved_aabb, neighbor_radius)
    for guid, aabb in index.query(query):
        if guid in (issue.guid_a, issue.guid_b):
            continue
        eval_pair = evaluate_pair(
            guid,
            moved_guid,
            aabb,
            moved_aabb,
            respect,
            tolerance,
            issue.rule_id,
            issue.severity,
        )
        if eval_pair.clearance < 0:
            creates += 1

    score = solves_score(solved, creates, fix.cost)
    return SimResult(solves=solved, creates=creates, violations=violations, score=score)


def solves_score(solves: int, creates: int, cost: float, w1: float = 10.0, w2: float = 20.0, w3: float = 1.0) -> float:
    return solves * w1 - creates * w2 - cost * w3


def recommend_fixes(
    issue: Issue,
    aabbs: Dict[str, AABB],
    index: SpatialIndex,
    respect: float,
    tolerance: float,
    elements: Dict[str, object],
) -> Recommendation:
    movable_guid, discipline, ifc_type = choose_movable(issue, elements)
    issue.movable_guid = movable_guid
    issue.movable_discipline = discipline
    issue.movable_type = ifc_type
    candidates = generate_candidate_fixes(issue, respect, tolerance, movable_guid, discipline, ifc_type)
    scored: List[Tuple[CandidateFix, SimResult]] = []
    for fix in candidates:
        res = simulate_fix(issue, fix, aabbs, index, respect, tolerance)
        fix.solves = res.solves
        fix.creates = res.creates
        fix.violations = res.violations
        fix.score = res.score
        scored.append((fix, res))
    scored.sort(key=lambda x: x[1].score, reverse=True)
    top = scored[0][0]
    alts = [f for f, _ in scored[1:3]]
    explanation = (
        f"Top fix score {scored[0][1].score:.2f}, solves={scored[0][1].solves}, "
        f"creates={scored[0][1].creates}, cost={top.cost:.3f}"
    )
    return Recommendation(top_fix=top, alternatives=alts, explanation=explanation)
