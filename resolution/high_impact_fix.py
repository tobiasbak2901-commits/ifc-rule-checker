from __future__ import annotations

"""Deterministic v1 high-impact single-move fix ranking.

Score:
    resolved * 100 - new * 200 - move_distance_mm * 0.2 - z_move_penalty

Tune:
    - `HighImpactFixConfig.step_sizes_mm` controls trial distances.
    - `HighImpactFixConfig.top_hot_elements` controls breadth.
    - `HighImpactFixConfig.top_k` controls output size.
"""

from dataclasses import dataclass, field
import math
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from geometry import aabb_distance_and_points, aabb_intersects


Vec3 = Tuple[float, float, float]
AABB = Tuple[float, float, float, float, float, float]
ProgressCallback = Callable[[int, int, int, int], None]
CancelCallback = Callable[[], bool]


@dataclass(frozen=True)
class Clash:
    id: str
    aId: str
    bId: str
    type: str = "hard"  # hard | soft | clearance
    pA: Optional[Vec3] = None
    pB: Optional[Vec3] = None
    clearanceMm: Optional[float] = None


@dataclass
class FixCandidate:
    id: str
    kind: str
    moveElementId: str
    vectorMm: Vec3
    score: float
    metrics: Dict[str, object]
    evidence: Dict[str, object]
    explanation: Dict[str, object]


@dataclass(frozen=True)
class HotElement:
    elementId: str
    clashCount: int
    clashIds: Tuple[str, ...]
    opponentIds: Tuple[str, ...]


@dataclass(frozen=True)
class TrialResult:
    elementId: str
    vectorMm: Vec3
    moveDistanceMm: float
    resolvedClashIds: Tuple[str, ...]
    impactedClashIds: Tuple[str, ...]
    unresolvedClashIds: Tuple[str, ...]
    newClashCount: int
    newClashPairIds: Tuple[str, ...]
    perClashReason: Dict[str, str]
    worstClearanceAfterMm: Optional[float]
    avgClearanceAfterMm: Optional[float]
    score: float


@dataclass(frozen=True)
class HighImpactFixConfig:
    top_hot_elements: int = 10
    top_k: int = 8
    step_sizes_mm: Tuple[float, ...] = (25.0, 50.0, 75.0, 100.0, 150.0, 200.0)
    max_move_mm: float = 250.0
    z_move_allowed: bool = True
    z_move_penalty: float = 30.0
    clearance_default_mm: float = 50.0
    soft_required_clearance_mm: float = 0.0
    hard_required_clearance_mm: float = 0.0
    new_clash_required_clearance_mm: float = 0.0
    grid_cell_size_m: float = 2.0
    model_unit_to_meter: float = 1.0
    protected_element_ids: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class PipelineResult:
    hotElements: Tuple[HotElement, ...]
    fixes: Tuple[FixCandidate, ...]
    trialsTested: int
    cancelled: bool


class BBoxGrid:
    def __init__(self, cell_size: float):
        self.cell_size = max(1e-6, float(cell_size))
        self._buckets: Dict[Tuple[int, int, int], Set[str]] = {}

    def _key_range(self, aabb: AABB) -> Tuple[range, range, range]:
        min_x = int(math.floor(aabb[0] / self.cell_size))
        min_y = int(math.floor(aabb[1] / self.cell_size))
        min_z = int(math.floor(aabb[2] / self.cell_size))
        max_x = int(math.floor(aabb[3] / self.cell_size))
        max_y = int(math.floor(aabb[4] / self.cell_size))
        max_z = int(math.floor(aabb[5] / self.cell_size))
        return (
            range(min_x, max_x + 1),
            range(min_y, max_y + 1),
            range(min_z, max_z + 1),
        )

    def insert(self, element_id: str, aabb: AABB) -> None:
        rx, ry, rz = self._key_range(aabb)
        for ix in rx:
            for iy in ry:
                for iz in rz:
                    self._buckets.setdefault((ix, iy, iz), set()).add(element_id)

    def query(self, aabb: AABB) -> Set[str]:
        ids: Set[str] = set()
        rx, ry, rz = self._key_range(aabb)
        for ix in rx:
            for iy in ry:
                for iz in rz:
                    ids.update(self._buckets.get((ix, iy, iz), set()))
        return ids


def build_bbox_grid(element_aabbs: Dict[str, AABB], cell_size_m: float) -> BBoxGrid:
    grid = BBoxGrid(cell_size_m)
    for element_id, aabb in sorted(element_aabbs.items(), key=lambda x: x[0]):
        grid.insert(element_id, aabb)
    return grid


def buildElementClashMap(clashes: Sequence[Clash]) -> Dict[str, List[str]]:
    clash_map: Dict[str, List[str]] = {}
    for clash in _sorted_clashes(clashes):
        clash_map.setdefault(clash.aId, []).append(clash.id)
        clash_map.setdefault(clash.bId, []).append(clash.id)
    for value in clash_map.values():
        value.sort()
    return clash_map


def buildElementDegree(clashes: Sequence[Clash]) -> Dict[str, int]:
    clash_map = buildElementClashMap(clashes)
    return {element_id: len(clash_ids) for element_id, clash_ids in clash_map.items()}


def selectTopElementsByDegree(clashes: Sequence[Clash], n: int = 10) -> List[str]:
    degree = buildElementDegree(clashes)
    ordered = sorted(degree.items(), key=lambda x: (-x[1], x[0]))
    return [element_id for element_id, _count in ordered[: max(0, n)]]


def getHotElements(clashes: Sequence[Clash], topN: int = 10) -> List[HotElement]:
    clash_map = buildElementClashMap(clashes)
    clash_by_id = {c.id: c for c in _sorted_clashes(clashes)}
    hot: List[HotElement] = []
    for element_id in sorted(clash_map.keys()):
        clash_ids = tuple(sorted(clash_map[element_id]))
        opponents: Set[str] = set()
        for clash_id in clash_ids:
            clash = clash_by_id[clash_id]
            opponents.add(clash.bId if clash.aId == element_id else clash.aId)
        hot.append(
            HotElement(
                elementId=element_id,
                clashCount=len(clash_ids),
                clashIds=clash_ids,
                opponentIds=tuple(sorted(opponents)),
            )
        )
    hot.sort(key=lambda item: (-item.clashCount, item.elementId))
    return hot[: max(0, topN)]


def generateTranslationTrials(
    elementId: str,
    stepSizesMm: Sequence[float],
    maxMoveMm: float,
    zMoveAllowed: bool,
) -> List[Vec3]:
    del elementId  # kept for interface stability
    steps = [float(v) for v in stepSizesMm if float(v) > 0.0 and float(v) <= float(maxMoveMm)]
    steps = sorted(set(steps))
    axes: List[Vec3] = [(1.0, 0.0, 0.0), (-1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, -1.0, 0.0)]
    if zMoveAllowed:
        axes.extend(((0.0, 0.0, 1.0), (0.0, 0.0, -1.0)))
    trials: List[Vec3] = []
    for axis in axes:
        for step in steps:
            trials.append((axis[0] * step, axis[1] * step, axis[2] * step))
    return trials


def evaluateTrialAgainstClashes(
    moveElementId: str,
    vectorMm: Vec3,
    clashesByElement: Dict[str, List[Clash]],
    elementAabbs: Dict[str, AABB],
    config: HighImpactFixConfig,
) -> TrialResult:
    impacted = list(clashesByElement.get(moveElementId, []))
    impacted.sort(key=lambda clash: clash.id)

    resolved_ids: List[str] = []
    unresolved_ids: List[str] = []
    per_reason: Dict[str, str] = {}
    after_clearances_mm: List[float] = []

    moved_aabb = _translate_aabb_mm(
        elementAabbs.get(moveElementId),
        vectorMm,
        config.model_unit_to_meter,
    )

    for clash in impacted:
        required_mm = _required_clearance_mm(clash, config)
        static_id = clash.bId if clash.aId == moveElementId else clash.aId
        after_clearance_mm: Optional[float] = None

        if clash.pA is not None and clash.pB is not None:
            moved_point = clash.pA if clash.aId == moveElementId else clash.pB
            static_point = clash.pB if clash.aId == moveElementId else clash.pA
            d = (
                static_point[0] - moved_point[0],
                static_point[1] - moved_point[1],
                static_point[2] - moved_point[2],
            )
            t_model = _mm_vec_to_model(vectorMm, config.model_unit_to_meter)
            d_after = (d[0] - t_model[0], d[1] - t_model[1], d[2] - t_model[2])
            distance_model = _norm(d_after)
            distance_mm = _model_to_mm(distance_model, config.model_unit_to_meter)
            after_clearance_mm = distance_mm - required_mm
            if distance_mm + 1e-9 >= required_mm:
                resolved_ids.append(clash.id)
                per_reason[clash.id] = (
                    f"point-distance {distance_mm:.1f}mm >= required {required_mm:.1f}mm"
                )
            else:
                unresolved_ids.append(clash.id)
                per_reason[clash.id] = (
                    f"point-distance {distance_mm:.1f}mm < required {required_mm:.1f}mm"
                )
        elif moved_aabb is not None and static_id in elementAabbs:
            static_aabb = elementAabbs[static_id]
            dist_model, _p_a, _p_b = aabb_distance_and_points(moved_aabb, static_aabb)
            dist_mm = _model_to_mm(dist_model, config.model_unit_to_meter)
            after_clearance_mm = dist_mm - required_mm
            if dist_mm + 1e-9 >= required_mm and not aabb_intersects(moved_aabb, static_aabb):
                resolved_ids.append(clash.id)
                per_reason[clash.id] = f"bbox separated by {dist_mm:.1f}mm"
            elif dist_mm + 1e-9 >= required_mm:
                resolved_ids.append(clash.id)
                per_reason[clash.id] = (
                    f"bbox threshold met ({dist_mm:.1f}mm >= {required_mm:.1f}mm)"
                )
            else:
                unresolved_ids.append(clash.id)
                per_reason[clash.id] = f"bbox still below required ({dist_mm:.1f}mm)"
        else:
            unresolved_ids.append(clash.id)
            per_reason[clash.id] = "insufficient geometry data for evaluation"

        if after_clearance_mm is not None:
            after_clearances_mm.append(after_clearance_mm)

    worst_after = min(after_clearances_mm) if after_clearances_mm else None
    avg_after = sum(after_clearances_mm) / len(after_clearances_mm) if after_clearances_mm else None

    return TrialResult(
        elementId=moveElementId,
        vectorMm=vectorMm,
        moveDistanceMm=_norm(vectorMm),
        resolvedClashIds=tuple(sorted(resolved_ids)),
        impactedClashIds=tuple(clash.id for clash in impacted),
        unresolvedClashIds=tuple(sorted(unresolved_ids)),
        newClashCount=0,
        newClashPairIds=tuple(),
        perClashReason=per_reason,
        worstClearanceAfterMm=worst_after,
        avgClearanceAfterMm=avg_after,
        score=0.0,
    )


def estimateNewClashes(
    moveElementId: str,
    vectorMm: Vec3,
    elementAabbs: Dict[str, AABB],
    bboxGrid: BBoxGrid,
    existingOpponentIds: Optional[Iterable[str]],
    config: HighImpactFixConfig,
) -> Tuple[int, Tuple[str, ...], Optional[float]]:
    moved_aabb = _translate_aabb_mm(
        elementAabbs.get(moveElementId),
        vectorMm,
        config.model_unit_to_meter,
    )
    if moved_aabb is None:
        return 0, tuple(), None

    existing = set(existingOpponentIds or [])
    pair_ids: List[str] = []
    worst_after_mm: Optional[float] = None

    nearby = sorted(bboxGrid.query(moved_aabb))
    for other_id in nearby:
        if other_id == moveElementId:
            continue
        if other_id in existing:
            continue
        other_aabb = elementAabbs.get(other_id)
        if other_aabb is None:
            continue
        dist_model, _p_a, _p_b = aabb_distance_and_points(moved_aabb, other_aabb)
        dist_mm = _model_to_mm(dist_model, config.model_unit_to_meter)
        clearance_mm = dist_mm - float(config.new_clash_required_clearance_mm)
        if worst_after_mm is None or clearance_mm < worst_after_mm:
            worst_after_mm = clearance_mm
        if dist_mm + 1e-9 < float(config.new_clash_required_clearance_mm) or aabb_intersects(moved_aabb, other_aabb):
            pair_ids.append(_pair_id(moveElementId, other_id))

    pair_ids.sort()
    return len(pair_ids), tuple(pair_ids), worst_after_mm


def rankFixes(
    trials: Sequence[TrialResult],
    topK: int,
    zMovePenalty: float,
) -> List[FixCandidate]:
    ranked_trials = sorted(
        trials,
        key=lambda trial: (
            -trial.score,
            -len(trial.resolvedClashIds),
            trial.newClashCount,
            trial.moveDistanceMm,
            -(trial.worstClearanceAfterMm if trial.worstClearanceAfterMm is not None else -1e12),
            trial.elementId,
            trial.vectorMm,
        ),
    )
    out: List[FixCandidate] = []
    for trial in ranked_trials[: max(0, int(topK))]:
        dx, dy, dz = trial.vectorMm
        z_penalty = float(zMovePenalty) if abs(dz) > 1e-9 else 0.0
        short = (
            f"Flyt {trial.elementId} {dx:+.0f}/{dy:+.0f}/{dz:+.0f} mm -> "
            f"resolves {len(trial.resolvedClashIds)} clashes "
            f"(skaber {trial.newClashCount} nye)"
        )
        bullets = [
            "Resolved clashes: " + str(len(trial.resolvedClashIds)),
            "Nye clashes: " + str(trial.newClashCount),
            f"Flytning: {trial.moveDistanceMm:.0f} mm",
        ]
        if trial.worstClearanceAfterMm is not None:
            bullets.append(f"Worst clearance efter: {trial.worstClearanceAfterMm:.1f} mm")
        if z_penalty:
            bullets.append(f"Z-penalty: {z_penalty:.1f}")
        out.append(
            FixCandidate(
                id=_trial_id(trial.elementId, trial.vectorMm),
                kind="translate_single",
                moveElementId=trial.elementId,
                vectorMm=trial.vectorMm,
                score=float(trial.score),
                metrics={
                    "resolvedClashes": len(trial.resolvedClashIds),
                    "unresolvedClashes": len(trial.unresolvedClashIds),
                    "newClashes": trial.newClashCount,
                    "worstClearanceAfterMm": trial.worstClearanceAfterMm,
                    "avgClearanceAfterMm": trial.avgClearanceAfterMm,
                },
                evidence={
                    "impactedClashIds": list(trial.impactedClashIds),
                    "resolvedClashIds": list(trial.resolvedClashIds),
                    "newClashPairIds": list(trial.newClashPairIds),
                    "perClashReason": dict(sorted(trial.perClashReason.items(), key=lambda x: x[0])),
                },
                explanation={"short": short, "bullets": bullets},
            )
        )
    return out


def findBestSingleMoveFixes(
    clashes: Sequence[Clash],
    elementAabbs: Dict[str, AABB],
    config: Optional[HighImpactFixConfig] = None,
    progressCallback: Optional[ProgressCallback] = None,
    shouldCancel: Optional[CancelCallback] = None,
) -> PipelineResult:
    cfg = config or HighImpactFixConfig()
    clashes_sorted = _sorted_clashes(clashes)
    hot_elements = getHotElements(clashes_sorted, topN=cfg.top_hot_elements)
    clash_by_element: Dict[str, List[Clash]] = {}
    for clash in clashes_sorted:
        clash_by_element.setdefault(clash.aId, []).append(clash)
        clash_by_element.setdefault(clash.bId, []).append(clash)
    for value in clash_by_element.values():
        value.sort(key=lambda c: c.id)

    bbox_grid = build_bbox_grid(elementAabbs, cfg.grid_cell_size_m)
    trials: List[TrialResult] = []
    cancelled = False
    trial_counter = 0

    for element_idx, hot in enumerate(hot_elements, start=1):
        if shouldCancel and shouldCancel():
            cancelled = True
            break
        if hot.elementId in cfg.protected_element_ids:
            continue

        vectors = generateTranslationTrials(
            elementId=hot.elementId,
            stepSizesMm=cfg.step_sizes_mm,
            maxMoveMm=cfg.max_move_mm,
            zMoveAllowed=cfg.z_move_allowed,
        )
        total_trials_for_element = len(vectors)
        for trial_idx, vector_mm in enumerate(vectors, start=1):
            if shouldCancel and shouldCancel():
                cancelled = True
                break
            if progressCallback:
                progressCallback(element_idx, len(hot_elements), trial_idx, total_trials_for_element)

            base = evaluateTrialAgainstClashes(
                moveElementId=hot.elementId,
                vectorMm=vector_mm,
                clashesByElement=clash_by_element,
                elementAabbs=elementAabbs,
                config=cfg,
            )
            new_count, new_pairs, worst_new_after_mm = estimateNewClashes(
                moveElementId=hot.elementId,
                vectorMm=vector_mm,
                elementAabbs=elementAabbs,
                bboxGrid=bbox_grid,
                existingOpponentIds=hot.opponentIds,
                config=cfg,
            )
            trial = _with_new_clashes(base, new_count, new_pairs, worst_new_after_mm)
            score = _score_trial(trial, cfg.z_move_penalty)
            trials.append(
                TrialResult(
                    elementId=trial.elementId,
                    vectorMm=trial.vectorMm,
                    moveDistanceMm=trial.moveDistanceMm,
                    resolvedClashIds=trial.resolvedClashIds,
                    impactedClashIds=trial.impactedClashIds,
                    unresolvedClashIds=trial.unresolvedClashIds,
                    newClashCount=trial.newClashCount,
                    newClashPairIds=trial.newClashPairIds,
                    perClashReason=trial.perClashReason,
                    worstClearanceAfterMm=trial.worstClearanceAfterMm,
                    avgClearanceAfterMm=trial.avgClearanceAfterMm,
                    score=score,
                )
            )
            trial_counter += 1
        if cancelled:
            break

    fixes = rankFixes(trials, topK=cfg.top_k, zMovePenalty=cfg.z_move_penalty)
    return PipelineResult(
        hotElements=tuple(hot_elements),
        fixes=tuple(fixes),
        trialsTested=trial_counter,
        cancelled=cancelled,
    )


def _sorted_clashes(clashes: Sequence[Clash]) -> List[Clash]:
    return sorted(
        list(clashes),
        key=lambda clash: (str(clash.id), str(clash.aId), str(clash.bId)),
    )


def _trial_id(element_id: str, vector_mm: Vec3) -> str:
    dx, dy, dz = vector_mm
    return f"hif::{element_id}::{int(round(dx))}_{int(round(dy))}_{int(round(dz))}"


def _pair_id(a: str, b: str) -> str:
    x, y = sorted((a, b))
    return f"{x}|{y}"


def _required_clearance_mm(clash: Clash, config: HighImpactFixConfig) -> float:
    ctype = str(clash.type or "hard").strip().lower()
    if ctype == "clearance":
        if clash.clearanceMm is not None and clash.clearanceMm > 0:
            return float(clash.clearanceMm)
        return float(config.clearance_default_mm)
    if ctype == "soft":
        return float(config.soft_required_clearance_mm)
    return float(config.hard_required_clearance_mm)


def _score_trial(trial: TrialResult, z_move_penalty: float) -> float:
    dz = trial.vectorMm[2]
    z_penalty = float(z_move_penalty) if abs(dz) > 1e-9 else 0.0
    return (
        float(len(trial.resolvedClashIds)) * 100.0
        - float(trial.newClashCount) * 200.0
        - float(trial.moveDistanceMm) * 0.2
        - z_penalty
    )


def _with_new_clashes(
    trial: TrialResult,
    new_clash_count: int,
    new_pairs: Tuple[str, ...],
    worst_new_after_mm: Optional[float],
) -> TrialResult:
    worst_after = trial.worstClearanceAfterMm
    if worst_new_after_mm is not None:
        if worst_after is None:
            worst_after = worst_new_after_mm
        else:
            worst_after = min(worst_after, worst_new_after_mm)
    return TrialResult(
        elementId=trial.elementId,
        vectorMm=trial.vectorMm,
        moveDistanceMm=trial.moveDistanceMm,
        resolvedClashIds=trial.resolvedClashIds,
        impactedClashIds=trial.impactedClashIds,
        unresolvedClashIds=trial.unresolvedClashIds,
        newClashCount=int(new_clash_count),
        newClashPairIds=tuple(sorted(new_pairs)),
        perClashReason=trial.perClashReason,
        worstClearanceAfterMm=worst_after,
        avgClearanceAfterMm=trial.avgClearanceAfterMm,
        score=trial.score,
    )


def _mm_vec_to_model(vector_mm: Vec3, model_unit_to_meter: float) -> Vec3:
    if model_unit_to_meter <= 0:
        model_unit_to_meter = 1.0
    scale = 0.001 / model_unit_to_meter
    return (vector_mm[0] * scale, vector_mm[1] * scale, vector_mm[2] * scale)


def _translate_aabb_mm(
    aabb: Optional[AABB],
    vector_mm: Vec3,
    model_unit_to_meter: float,
) -> Optional[AABB]:
    if aabb is None:
        return None
    tx, ty, tz = _mm_vec_to_model(vector_mm, model_unit_to_meter)
    return (
        aabb[0] + tx,
        aabb[1] + ty,
        aabb[2] + tz,
        aabb[3] + tx,
        aabb[4] + ty,
        aabb[5] + tz,
    )


def _model_to_mm(value_model: float, model_unit_to_meter: float) -> float:
    if model_unit_to_meter <= 0:
        model_unit_to_meter = 1.0
    return float(value_model) * model_unit_to_meter * 1000.0


def _norm(v: Vec3) -> float:
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
