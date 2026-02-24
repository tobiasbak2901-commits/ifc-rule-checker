from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import replace
import math
import time
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from geometry import aabb_distance_and_points

from .workflow import (
    Action,
    AiCardPayload,
    AiCardState,
    AiCardStateStore,
    AiChip,
    AiDiagnostics,
    AiHeader,
    AiStep,
    AiStepperItem,
    AiTrace,
    AiTraceNode,
    AssumptionItem,
    Block,
    BlockAssumptions,
    BlockChecklist,
    BlockCitations,
    BlockFixList,
    BlockSummary,
    BlockTable,
    BlockTrace,
    ChecklistItem,
    CitationItem,
    FixCandidate,
    FixCandidateSummary,
    STEP_LABELS,
    STEP_ORDER,
    TableRow,
)


def build_ai_card(
    issue_context: Dict[str, Any],
    project_context: Dict[str, Any],
    rulepacks: Any,
    geometry_engine: Dict[str, Any],
    store: AiCardStateStore,
) -> tuple[AiCardState, AiCardPayload]:
    issue_id = str(issue_context.get("issue_id") or "").strip() or "__no_issue__"
    state = store.load_state(issue_id)
    if state.issue_id != issue_id:
        state = replace(state, issue_id=issue_id)

    citations = _extract_rule_citations(issue_context, rulepacks)
    rulepack_loaded = bool(rulepacks is not None)
    moveability_ok, moveability_missing = _moveability_status(issue_context)
    grouping = build_clash_groups(
        list(project_context.get("issues") or []),
        dict(project_context.get("aabbs") or {}),
        distance_threshold_m=float(project_context.get("group_distance_threshold_m") or 2.0),
    )
    group_id = grouping["issue_to_group"].get(issue_id)
    group_ids = grouping["groups"].get(group_id, []) if group_id else []
    grouping_ok = bool(group_id)

    fix_candidates = list(issue_context.get("fix_candidates") or [])
    if not fix_candidates:
        cached = (project_context.get("fix_cache") or {}).get(issue_id)
        if isinstance(cached, list):
            fix_candidates = cached

    blockers: Dict[AiStep, List[str]] = {step: [] for step in STEP_ORDER}
    if _responsibility_missing(issue_context):
        blockers[AiStep.RESPONSIBILITY].append(
            "Discipline/classification mangler for begge elementer."
        )
    if not rulepack_loaded:
        blockers[AiStep.RULE_BASIS].append("Ingen rulepack indlæst.")
    if not citations:
        blockers[AiStep.RULE_BASIS].append("Ingen matchende regel/citation fundet.")
    if not moveability_ok:
        blockers[AiStep.MOVEABILITY].append("Manglende constraints/free-space input.")
        blockers[AiStep.MOVEABILITY].extend(moveability_missing)
    if not grouping_ok:
        blockers[AiStep.HIGH_IMPACT].append("Clash grouping er ikke beregnet endnu.")
    if not state.chosen_fix_id:
        blockers[AiStep.APPLY].append("Ingen fix valgt.")

    state = _derive_completed_steps(state, citations, fix_candidates)
    stepper = _build_stepper(state, blockers)
    active_blockers = list(blockers.get(state.active_step) or [])

    owner_suggestion, owner_confidence = _owner_suggestion(issue_context)
    assumptions = _build_assumptions(issue_context, citations, moveability_missing)
    blocks: List[Block] = []
    if active_blockers:
        blocks.append(_unlock_block(state.active_step, active_blockers))
    blocks.extend(
        _blocks_for_active_step(
            state=state,
            issue_context=issue_context,
            project_context=project_context,
            citations=citations,
            assumptions=assumptions,
            owner_suggestion=owner_suggestion,
            owner_confidence=owner_confidence,
            fix_candidates=fix_candidates,
            group_id=group_id,
            group_issue_ids=group_ids,
        )
    )

    diagnostics = _diagnostics(
        issue_context=issue_context,
        has_citations=bool(citations),
        moveability_ok=moveability_ok,
        has_fixes=bool(fix_candidates),
        missing=list(dict.fromkeys(active_blockers)),
    )
    trace = _build_trace(
        issue_context=issue_context,
        project_context=project_context,
        citations=citations,
        moveability_ok=moveability_ok,
        moveability_missing=moveability_missing,
        fix_candidates=fix_candidates,
        chosen_fix_id=state.chosen_fix_id,
    )

    chips = _chips(issue_context, owner_suggestion, owner_confidence, diagnostics)
    status_badge = _status_badge(issue_context)
    severity_badge = str(issue_context.get("severity") or "-")
    header = AiHeader(
        title="Ponker AI Card",
        status_badge=status_badge,
        severity_badge=severity_badge,
    )
    actions = _actions_for_active_step(
        state=state,
        active_blockers=active_blockers,
        owner_suggestion=owner_suggestion,
        fix_candidates=fix_candidates,
        has_citations=bool(citations),
    )
    payload = AiCardPayload(
        header=header,
        chips=chips,
        stepper=stepper,
        blocks=blocks,
        actions=actions,
        diagnostics=diagnostics,
        trace=trace,
    )
    return state, payload


def build_clash_groups(
    issues: Sequence[Dict[str, Any]],
    aabbs: Dict[str, Tuple[float, float, float, float, float, float]],
    *,
    distance_threshold_m: float = 2.0,
) -> Dict[str, Dict[str, List[str]]]:
    nodes: Dict[str, Dict[str, Any]] = {}
    for idx, raw in enumerate(list(issues or []), start=1):
        issue_id = str(raw.get("issue_id") or raw.get("id") or f"issue-{idx}")
        guid_a = str(raw.get("guid_a") or "")
        guid_b = str(raw.get("guid_b") or "")
        if not issue_id or not guid_a or not guid_b:
            continue
        pair = _discipline_pair(raw)
        center = _issue_center(raw, aabbs)
        nodes[issue_id] = {
            "issue_id": issue_id,
            "guid_a": guid_a,
            "guid_b": guid_b,
            "pair": pair,
            "center": center,
        }

    adjacency: Dict[str, set[str]] = {issue_id: set() for issue_id in nodes}
    ids = sorted(nodes.keys())
    for i, left_id in enumerate(ids):
        left = nodes[left_id]
        for right_id in ids[i + 1 :]:
            right = nodes[right_id]
            shares = bool(
                {left["guid_a"], left["guid_b"]} & {right["guid_a"], right["guid_b"]}
            )
            same_pair = left["pair"] == right["pair"]
            near = False
            if left["center"] and right["center"] and same_pair:
                near = _distance(left["center"], right["center"]) <= float(distance_threshold_m)
            if shares or near:
                adjacency[left_id].add(right_id)
                adjacency[right_id].add(left_id)

    issue_to_group: Dict[str, str] = {}
    groups: Dict[str, List[str]] = {}
    visited: set[str] = set()
    group_idx = 0
    for issue_id in ids:
        if issue_id in visited:
            continue
        group_idx += 1
        group_id = f"group-{group_idx:03d}"
        stack = [issue_id]
        members: List[str] = []
        visited.add(issue_id)
        while stack:
            current = stack.pop()
            members.append(current)
            issue_to_group[current] = group_id
            for nxt in sorted(adjacency.get(current, [])):
                if nxt in visited:
                    continue
                visited.add(nxt)
                stack.append(nxt)
        groups[group_id] = sorted(members)
    return {"issue_to_group": issue_to_group, "groups": groups}


def generate_high_impact_fixes(
    issue_context: Dict[str, Any],
    project_context: Dict[str, Any],
    rulepacks: Any,
    geometry_engine: Dict[str, Any],
    group_issue_ids: Sequence[str],
) -> List[FixCandidate]:
    issue_id = str(issue_context.get("issue_id") or "")
    issues_by_id = {
        str(item.get("issue_id") or item.get("id")): item
        for item in list(project_context.get("issues") or [])
        if str(item.get("issue_id") or item.get("id") or "").strip()
    }
    active = issues_by_id.get(issue_id) or issue_context
    if not active:
        return []

    group_issues = [issues_by_id[item_id] for item_id in group_issue_ids if item_id in issues_by_id]
    if not group_issues:
        group_issues = [active]

    aabbs = dict(project_context.get("aabbs") or {})
    if not aabbs:
        return []

    default_clearance_m = float(
        issue_context.get("required_clearance_m")
        or issue_context.get("metrics", {}).get("required_clearance_m")
        or 0.0
    )
    if default_clearance_m <= 0 and rulepacks is not None:
        try:
            default_clearance_m = float(getattr(rulepacks, "default_clearance_mm", 0.0)) / 1000.0
        except Exception:
            default_clearance_m = 0.0

    rules_citations = [item.source_id for item in _extract_rule_citations(issue_context, rulepacks)]
    cancel = geometry_engine.get("cancel_token")
    model_unit_to_meter = float(geometry_engine.get("model_unit_to_meter") or 1.0)
    del model_unit_to_meter  # kept for engine interface stability

    element_counts = Counter()
    for item in group_issues:
        element_counts[str(item.get("guid_a") or "")] += 1
        element_counts[str(item.get("guid_b") or "")] += 1
    ordered_targets = [guid for guid, _count in element_counts.most_common() if guid in aabbs]

    directions = (
        (1.0, 0.0, 0.0),
        (-1.0, 0.0, 0.0),
        (0.0, 1.0, 0.0),
        (0.0, -1.0, 0.0),
        (0.0, 0.0, 1.0),
        (0.0, 0.0, -1.0),
    )
    magnitudes = (0.01, 0.02, 0.05, 0.10, 0.15)
    fixes: List[FixCandidate] = []

    constraints_by_guid = _constraints_by_guid(project_context)
    for target in ordered_targets[:8]:
        target_constraints = constraints_by_guid.get(target, {})
        max_move_m = float(target_constraints.get("max_move_m") or 999.0)
        z_allowed = target_constraints.get("z_allowed")
        protected = bool(target_constraints.get("protected"))
        has_slope = bool(target_constraints.get("slope"))

        for axis in directions:
            for magnitude in magnitudes:
                if callable(cancel) and bool(cancel()):
                    return rank_fix_candidates(fixes)[:5]
                dx = axis[0] * magnitude
                dy = axis[1] * magnitude
                dz = axis[2] * magnitude
                move_distance_m = math.sqrt(dx * dx + dy * dy + dz * dz)
                violations: List[str] = []
                if protected:
                    violations.append("target is protected")
                if move_distance_m > max_move_m + 1e-9:
                    violations.append("move exceeds max_move_m")
                if z_allowed is False and abs(dz) > 1e-9:
                    violations.append("z_move not allowed")

                moved = _translate_aabb(aabbs.get(target), dx, dy, dz)
                if moved is None:
                    continue

                created_estimate = _estimate_created_issues(
                    moved_aabb=moved,
                    moved_guid=target,
                    all_aabbs=aabbs,
                    clearance_m=max(0.0, default_clearance_m),
                )
                if created_estimate > 10:
                    continue

                solved: List[str] = []
                min_clearance_after = 0.0
                seen_clearance = False
                for issue in group_issues:
                    guid_a = str(issue.get("guid_a") or "")
                    guid_b = str(issue.get("guid_b") or "")
                    if target not in (guid_a, guid_b):
                        continue
                    other = guid_b if target == guid_a else guid_a
                    other_aabb = aabbs.get(other)
                    if not other_aabb:
                        continue
                    dist, _p0, _p1 = aabb_distance_and_points(moved, other_aabb)
                    req = float(issue.get("required_clearance_m") or default_clearance_m or 0.0)
                    clearance_after = float(dist) - req
                    if not seen_clearance or clearance_after < min_clearance_after:
                        min_clearance_after = clearance_after
                        seen_clearance = True
                    if clearance_after >= 0:
                        solved.append(str(issue.get("issue_id") or issue.get("id") or ""))
                if not seen_clearance:
                    min_clearance_after = -1.0

                bonus = 0.0
                if has_slope and abs(dz) < 1e-9:
                    bonus += 5.0
                if move_distance_m <= max_move_m:
                    bonus += 2.0
                score = (
                    (len([v for v in solved if v]) * 10.0)
                    - (created_estimate * 20.0)
                    - (len(violations) * 50.0)
                    - (move_distance_m * 5.0)
                    + bonus
                )

                why = [
                    f"Solves {len([v for v in solved if v])} issue(s).",
                    f"Creates est. {created_estimate} new issue(s).",
                    f"Move {dx:+.3f}/{dy:+.3f}/{dz:+.3f} m.",
                ]
                if violations:
                    why.append("Violations: " + ", ".join(violations))
                if has_slope and abs(dz) < 1e-9:
                    why.append("Slope-preserving move.")
                fix_id = f"{target}:{dx:+.3f},{dy:+.3f},{dz:+.3f}"
                fixes.append(
                    FixCandidate(
                        fix_id=fix_id,
                        target_element=_target_side(active, target),
                        type="translate",
                        vector=(dx, dy, dz),
                        solves_issue_ids=[v for v in solved if v],
                        creates_new_issue_estimate=created_estimate,
                        min_clearance_after=float(min_clearance_after),
                        violates_constraints=violations,
                        score=float(score),
                        explanation=why,
                        citations=rules_citations,
                        preview_payload={
                            "guid": target,
                            "overlay_lines": [f"vector={dx:+.3f},{dy:+.3f},{dz:+.3f}m"],
                        },
                    )
                )
    return rank_fix_candidates(fixes)[:5]


def rank_fix_candidates(candidates: Sequence[FixCandidate]) -> List[FixCandidate]:
    return sorted(
        list(candidates or []),
        key=lambda item: (
            -float(item.score),
            int(item.creates_new_issue_estimate),
            len(item.violates_constraints),
            _vec_len(item.vector),
            item.fix_id,
        ),
    )


def _derive_completed_steps(
    state: AiCardState,
    citations: Sequence[CitationItem],
    fix_candidates: Sequence[FixCandidate],
) -> AiCardState:
    completed = set(state.completed_steps)
    completed.add(AiStep.CREATED)
    if state.chosen_owner:
        completed.add(AiStep.RESPONSIBILITY)
    if citations:
        completed.add(AiStep.RULE_BASIS)
    if fix_candidates:
        completed.add(AiStep.HIGH_IMPACT)
    if state.chosen_fix_id:
        completed.add(AiStep.DECISION)
    return replace(state, completed_steps=completed)


def _build_stepper(state: AiCardState, blockers: Dict[AiStep, List[str]]) -> List[AiStepperItem]:
    out: List[AiStepperItem] = []
    for step in STEP_ORDER:
        status = "pending"
        blocked_reason = "; ".join(blockers.get(step) or [])
        if blocked_reason:
            status = "blocked"
        if step in state.completed_steps:
            status = "completed"
        if step == state.active_step:
            status = "active" if not blocked_reason else "blocked"
        out.append(
            AiStepperItem(
                step=step,
                label=STEP_LABELS.get(step, step.value),
                status=status,
                blocked_reason=blocked_reason,
            )
        )
    return out


def _blocks_for_active_step(
    *,
    state: AiCardState,
    issue_context: Dict[str, Any],
    project_context: Dict[str, Any],
    citations: Sequence[CitationItem],
    assumptions: Sequence[str],
    owner_suggestion: str,
    owner_confidence: float,
    fix_candidates: Sequence[FixCandidate],
    group_id: Optional[str],
    group_issue_ids: Sequence[str],
) -> List[Block]:
    step = state.active_step
    blocks: List[Block] = []
    metrics = dict(issue_context.get("metrics") or {})
    class_a = str(issue_context.get("class_a") or "Unknown")
    class_b = str(issue_context.get("class_b") or "Unknown")

    if step == AiStep.CREATED:
        blocks.append(
            BlockSummary(
                kind="summary",
                id="created_summary",
                title="Created",
                bullets=[
                    f"Issue: {issue_context.get('issue_id') or '-'}",
                    f"Elements: {class_a} vs {class_b}",
                    (
                        "Geometry: minDistance="
                        f"{float(metrics.get('min_distance_m') or 0.0):.4f}m, overlap="
                        f"{float(metrics.get('overlap_m') or 0.0):.4f}m"
                    ),
                ],
            )
        )
        blocks.append(
            BlockTable(
                kind="table",
                id="created_metrics",
                title="Computed Facts",
                rows=[
                    TableRow("Method", str(metrics.get("method") or "-")),
                    TableRow("EPS", f"{float(metrics.get('eps') or 0.0):.6f}"),
                    TableRow("Padding", f"{float(metrics.get('padding') or 0.0):.4f}m"),
                ],
            )
        )
    elif step == AiStep.RESPONSIBILITY:
        blocks.append(
            BlockSummary(
                kind="summary",
                id="resp_summary",
                title="Suggested owner",
                bullets=[
                    f"Suggestion: {owner_suggestion or '-'}",
                    f"Confidence: {owner_confidence:.2f}",
                    "Confirm owner explicitly before moving forward.",
                ],
            )
        )
        blocks.append(
            BlockTable(
                kind="table",
                id="resp_sources",
                title="Owner Evidence",
                rows=[
                    TableRow("Element A class", class_a),
                    TableRow("Element B class", class_b),
                    TableRow("Element A discipline", str(issue_context.get("discipline_a") or "-")),
                    TableRow("Element B discipline", str(issue_context.get("discipline_b") or "-")),
                ],
            )
        )
    elif step == AiStep.CONTEXT:
        blocks.append(
            BlockSummary(
                kind="summary",
                id="context_summary",
                title="Where in project",
                bullets=[
                    f"Storey: {issue_context.get('storey') or 'Unknown'}",
                    f"Space: {issue_context.get('space') or 'Unknown'}",
                    "Use focus/section/measure actions for deterministic spatial review.",
                ],
            )
        )
        blocks.append(
            BlockTable(
                kind="table",
                id="context_scope",
                title="Scope",
                rows=[
                    TableRow("Search set A", str(issue_context.get("search_set_a") or "-")),
                    TableRow("Search set B", str(issue_context.get("search_set_b") or "-")),
                    TableRow("Camera", str(project_context.get("camera_label") or "-")),
                ],
            )
        )
    elif step == AiStep.RULE_BASIS:
        if citations:
            blocks.append(
                BlockCitations(
                    kind="citations",
                    id="rule_citations",
                    title="Rule basis / citations",
                    citations=list(citations),
                )
            )
        else:
            blocks.append(
                BlockSummary(
                    kind="summary",
                    id="rule_missing",
                    title="Rule basis",
                    bullets=[
                        "No citations available.",
                        "No standard linked yet.",
                        "Open rulepack mapping to connect rules and standards.",
                    ],
                )
            )
    elif step == AiStep.MOVEABILITY:
        constraints = _constraints_table(issue_context)
        blocks.append(
            BlockTable(
                kind="table",
                id="moveability_table",
                title="Moveability",
                rows=constraints,
            )
        )
    elif step == AiStep.HIGH_IMPACT:
        blocks.append(
            BlockSummary(
                kind="summary",
                id="group_summary",
                title="Clash group",
                bullets=[
                    f"Group ID: {group_id or '-'}",
                    f"Issues in group: {len(list(group_issue_ids or []))}",
                    "Candidates score: solved*10 - created*20 - violations*50 - distance*5",
                ],
            )
        )
        blocks.append(
            BlockFixList(
                kind="fix_list",
                id="high_impact_fixes",
                title="High-impact suggestions",
                fixes=[_fix_summary(item) for item in list(fix_candidates)[:5]],
            )
        )
    elif step == AiStep.DECISION:
        blocks.append(
            BlockFixList(
                kind="fix_list",
                id="decision_fixes",
                title="Decision",
                fixes=[_fix_summary(item) for item in list(fix_candidates)[:5]],
            )
        )
        assumption_rows = [
            AssumptionItem(
                id=f"a-{idx+1}",
                text=text,
                accepted=text in set(state.pinned_assumptions),
            )
            for idx, text in enumerate(list(assumptions)[:8])
        ]
        blocks.append(
            BlockAssumptions(
                kind="assumptions",
                id="decision_assumptions",
                title="Assumptions",
                assumptions=assumption_rows,
            )
        )
    elif step == AiStep.APPLY:
        chosen = next((item for item in fix_candidates if item.fix_id == state.chosen_fix_id), None)
        lines = ["No fix selected."]
        if chosen is not None:
            lines = [
                f"Chosen fix: {chosen.fix_id}",
                f"Move: {chosen.vector[0]:+.3f}/{chosen.vector[1]:+.3f}/{chosen.vector[2]:+.3f}m",
                f"Solves {len(chosen.solves_issue_ids)} issue(s), creates {chosen.creates_new_issue_estimate}.",
            ]
        blocks.append(
            BlockSummary(kind="summary", id="apply_summary", title="Apply / Export", bullets=lines)
        )

    trace_lines = _trace_preview_lines(
        issue_context=issue_context,
        citations_count=len(citations),
        fixes_count=len(fix_candidates),
    )
    blocks.append(
        BlockTrace(
            kind="trace",
            id="trace_preview",
            title="Trace preview",
            trace_preview_lines=trace_lines,
        )
    )
    return blocks


def _unlock_block(active_step: AiStep, blockers: Sequence[str]) -> BlockChecklist:
    items: List[ChecklistItem] = []
    for idx, line in enumerate(list(blockers), start=1):
        action: Optional[Action] = None
        lower = str(line).lower()
        if "classification" in lower or "discipline" in lower:
            action = Action(action_id="help_classify", label="Hjælp mig med at klassificere")
        elif "rulepack" in lower or "citation" in lower:
            action = Action(action_id="open_rulepack_mapping", label="Open rulepack mapping")
        elif "fix" in lower:
            action = Action(action_id="generate_fixes", label="Generér fixes")
        items.append(
            ChecklistItem(
                id=f"unlock-{idx}",
                text=str(line),
                done=False,
                action=action,
            )
        )
    return BlockChecklist(
        kind="checklist",
        id=f"unlock_{active_step.value.lower()}",
        title="Unlock next step",
        items=items,
    )


def _actions_for_active_step(
    *,
    state: AiCardState,
    active_blockers: Sequence[str],
    owner_suggestion: str,
    fix_candidates: Sequence[FixCandidate],
    has_citations: bool,
) -> List[Action]:
    blocked = bool(active_blockers)
    next_map = {
        AiStep.CREATED: AiStep.RESPONSIBILITY,
        AiStep.RESPONSIBILITY: AiStep.CONTEXT,
        AiStep.CONTEXT: AiStep.RULE_BASIS,
        AiStep.RULE_BASIS: AiStep.MOVEABILITY,
        AiStep.MOVEABILITY: AiStep.HIGH_IMPACT,
        AiStep.HIGH_IMPACT: AiStep.DECISION,
        AiStep.DECISION: AiStep.APPLY,
    }
    actions: List[Action] = [
        Action(action_id="focus_clash", label="Fokusér clash"),
        Action(action_id="section_around_clash", label="Section omkring clash"),
        Action(action_id="measure_distance", label="Mål afstand"),
    ]
    if state.active_step in next_map:
        next_step = next_map[state.active_step]
        actions.append(
            Action(
                action_id="goto_step",
                label=f"Gå til {STEP_LABELS[next_step]}",
                enabled=not blocked,
                reason="Unlock next step først." if blocked else "",
                params={"step": next_step.value},
            )
        )
    if state.active_step == AiStep.RESPONSIBILITY:
        if owner_suggestion:
            actions.append(
                Action(
                    action_id="set_owner",
                    label=f"Sæt owner: {owner_suggestion}",
                    params={"owner": owner_suggestion},
                )
            )
        for owner in ("VVS", "EL", "Kloak", "Ventilation"):
            if owner == owner_suggestion:
                continue
            actions.append(
                Action(action_id="set_owner", label=f"Sæt owner: {owner}", params={"owner": owner})
            )
        actions.append(Action(action_id="help_classify", label="Hjælp mig med at klassificere"))
    if state.active_step == AiStep.RULE_BASIS and not has_citations:
        actions.append(Action(action_id="open_rulepack_mapping", label="Open rulepack mapping"))
    if state.active_step in (AiStep.HIGH_IMPACT, AiStep.DECISION):
        actions.append(Action(action_id="generate_fixes", label="Generér fixes"))
        if fix_candidates:
            actions.append(
                Action(
                    action_id="preview_fix",
                    label="Preview",
                    params={"fix_id": fix_candidates[0].fix_id},
                )
            )
            actions.append(
                Action(
                    action_id="accept_fix",
                    label="Acceptér fix",
                    params={"fix_id": fix_candidates[0].fix_id},
                )
            )
    if state.active_step == AiStep.APPLY:
        actions.append(
            Action(
                action_id="export_fix",
                label="Export",
                enabled=bool(state.chosen_fix_id),
                reason="" if state.chosen_fix_id else "Vælg fix før export.",
            )
        )
    actions.append(Action(action_id="save_assumption", label="Gem note/antagelse"))
    if blocked:
        for idx, item in enumerate(actions):
            if item.action_id in {"focus_clash", "section_around_clash", "measure_distance", "help_classify"}:
                continue
            actions[idx] = replace(item, enabled=False, reason="Unlock next step først.")
    return actions


def _build_assumptions(
    issue_context: Dict[str, Any],
    citations: Sequence[CitationItem],
    moveability_missing: Sequence[str],
) -> List[str]:
    assumptions: List[str] = []
    class_a = str(issue_context.get("class_a") or "Unknown")
    class_b = str(issue_context.get("class_b") or "Unknown")
    if class_a.lower() == "unknown" or class_b.lower() == "unknown":
        assumptions.append("Classification unknown for one or more elements.")
    if not citations:
        assumptions.append("No standard linked yet; rule basis is internal rulepack only.")
    for item in list(moveability_missing or []):
        assumptions.append(str(item))
    return assumptions


def _diagnostics(
    *,
    issue_context: Dict[str, Any],
    has_citations: bool,
    moveability_ok: bool,
    has_fixes: bool,
    missing: Sequence[str],
) -> AiDiagnostics:
    metrics = dict(issue_context.get("metrics") or {})
    min_distance = metrics.get("min_distance_m")
    geometry_score = 1.0 if isinstance(min_distance, (int, float)) else 0.0

    class_conf_a = float(issue_context.get("class_confidence_a") or 0.0)
    class_conf_b = float(issue_context.get("class_confidence_b") or 0.0)
    class_name_a = str(issue_context.get("class_a") or "Unknown")
    class_name_b = str(issue_context.get("class_b") or "Unknown")
    class_score_a = class_conf_a if class_name_a.lower() != "unknown" else 0.2
    class_score_b = class_conf_b if class_name_b.lower() != "unknown" else 0.2
    class_score = max(0.0, min(1.0, (class_score_a + class_score_b) * 0.5))

    rule_score = 1.0 if has_citations else 0.35
    move_score = 1.0 if moveability_ok else 0.3
    fix_score = 1.0 if has_fixes else 0.4
    breakdown = {
        "geometry": round(geometry_score, 3),
        "classification": round(class_score, 3),
        "rule_basis": round(rule_score, 3),
        "moveability": round(move_score, 3),
        "fix_signal": round(fix_score, 3),
    }
    confidence = (
        geometry_score * 0.35
        + class_score * 0.20
        + rule_score * 0.20
        + move_score * 0.15
        + fix_score * 0.10
    )
    confidence = max(0.0, min(1.0, confidence))
    return AiDiagnostics(
        confidence=round(confidence, 3),
        confidence_breakdown=breakdown,
        missing=[str(v) for v in list(missing or []) if str(v).strip()],
    )


def _build_trace(
    *,
    issue_context: Dict[str, Any],
    project_context: Dict[str, Any],
    citations: Sequence[CitationItem],
    moveability_ok: bool,
    moveability_missing: Sequence[str],
    fix_candidates: Sequence[FixCandidate],
    chosen_fix_id: Optional[str],
) -> AiTrace:
    metrics = dict(issue_context.get("metrics") or {})
    element_a = {
        "globalId": str(issue_context.get("guid_a") or ""),
        "name": str(issue_context.get("name_a") or "") or None,
        "type": str(issue_context.get("type_a") or "") or None,
        "class": str(issue_context.get("class_a") or "") or None,
        "class_confidence": issue_context.get("class_confidence_a"),
        "properties_used": list(issue_context.get("properties_used_a") or []),
    }
    element_b = {
        "globalId": str(issue_context.get("guid_b") or ""),
        "name": str(issue_context.get("name_b") or "") or None,
        "type": str(issue_context.get("type_b") or "") or None,
        "class": str(issue_context.get("class_b") or "") or None,
        "class_confidence": issue_context.get("class_confidence_b"),
        "properties_used": list(issue_context.get("properties_used_b") or []),
    }
    geometry = {
        "method": str(metrics.get("method") or "-"),
        "minDistance": metrics.get("min_distance_m"),
        "overlap": metrics.get("overlap_m"),
        "eps": metrics.get("eps"),
        "padding": metrics.get("padding"),
        "bboxA": metrics.get("bbox_a"),
        "bboxB": metrics.get("bbox_b"),
    }
    scope = {
        "searchSets": [
            str(issue_context.get("search_set_a") or ""),
            str(issue_context.get("search_set_b") or ""),
        ],
        "rulepack_ids": [str(v) for v in list(project_context.get("rulepack_ids") or []) if str(v).strip()],
    }

    step_nodes = [
        AiTraceNode(
            id="classification",
            kind="classification",
            title="Classification",
            data={
                "a": {"class": element_a["class"], "confidence": element_a["class_confidence"]},
                "b": {"class": element_b["class"], "confidence": element_b["class_confidence"]},
            },
            children=[],
            ok=all(
                str(item.get("class") or "").strip().lower() != "unknown"
                for item in (element_a, element_b)
            ),
            warnings=["Unknown class present."] if (
                str(element_a.get("class") or "").lower() == "unknown"
                or str(element_b.get("class") or "").lower() == "unknown"
            ) else [],
            errors=[],
        ),
        AiTraceNode(
            id="rule_match",
            kind="rule_match",
            title="Rule match",
            data={"rule_id": str(issue_context.get("rule_id") or ""), "citations": [c.source_id for c in citations]},
            children=[],
            ok=bool(citations),
            warnings=[] if citations else ["No standard-linked citation."],
            errors=[],
        ),
        AiTraceNode(
            id="constraint_eval",
            kind="constraint_eval",
            title="Constraint eval",
            data={"constraints": issue_context.get("constraints") or {}},
            children=[],
            ok=bool(moveability_ok),
            warnings=list(moveability_missing),
            errors=[],
        ),
        AiTraceNode(
            id="moveability",
            kind="moveability",
            title="Moveability",
            data={"ok": bool(moveability_ok)},
            children=[],
            ok=bool(moveability_ok),
            warnings=list(moveability_missing),
            errors=[],
        ),
        AiTraceNode(
            id="fix_generation",
            kind="fix_generation",
            title="Fix generation",
            data={"candidate_count": len(list(fix_candidates or []))},
            children=[],
            ok=bool(fix_candidates),
            warnings=[] if fix_candidates else ["No candidates generated yet."],
            errors=[],
        ),
        AiTraceNode(
            id="ranking",
            kind="ranking",
            title="Ranking",
            data={
                "top_fix_id": str(fix_candidates[0].fix_id) if fix_candidates else "",
                "top_score": float(fix_candidates[0].score) if fix_candidates else None,
            },
            children=[],
            ok=bool(fix_candidates),
            warnings=[],
            errors=[],
        ),
        AiTraceNode(
            id="export",
            kind="export",
            title="Export",
            data={"chosen_fix_id": str(chosen_fix_id or "")},
            children=[],
            ok=bool(chosen_fix_id),
            warnings=[] if chosen_fix_id else ["No chosen fix."],
            errors=[],
        ),
    ]
    return AiTrace(
        trace_version=1,
        issue_id=str(issue_context.get("issue_id") or "__no_issue__"),
        timestamp=float(time.time()),
        inputs={
            "elementA": element_a,
            "elementB": element_b,
            "geometry": geometry,
            "scope": scope,
        },
        steps=step_nodes,
    )


def _extract_rule_citations(issue_context: Dict[str, Any], rulepacks: Any) -> List[CitationItem]:
    rule_id = str(issue_context.get("rule_id") or "").strip()
    if not rule_id or rulepacks is None:
        return []
    out: List[CitationItem] = []

    for generated in list(getattr(rulepacks, "generated_rules", []) or []):
        if not isinstance(generated, dict):
            continue
        if str(generated.get("id") or "") != rule_id:
            continue
        src = dict(generated.get("source") or {}) if isinstance(generated.get("source"), dict) else {}
        standard = str(src.get("doc") or src.get("standard") or "").strip()
        section = str(src.get("section") or src.get("clause") or "").strip()
        excerpt = str(src.get("quote") or src.get("excerpt") or src.get("note") or "").strip()
        title = f"{standard} {section}".strip() if standard else f"Rule {rule_id}"
        out.append(
            CitationItem(
                source_id=f"rule:{rule_id}",
                title=title,
                ref=section or rule_id,
                excerpt=excerpt,
            )
        )
        break

    if not out:
        for utility_rule in list(getattr(rulepacks, "utility_rules", []) or []):
            if str(getattr(utility_rule, "rule_id", "") or "") != rule_id:
                continue
            src = getattr(utility_rule, "source", None)
            src_map = dict(src or {}) if isinstance(src, dict) else {}
            standard = str(src_map.get("doc") or src_map.get("standard") or "").strip()
            section = str(src_map.get("section") or src_map.get("clause") or "").strip()
            excerpt = str(src_map.get("quote") or src_map.get("excerpt") or src_map.get("note") or "").strip()
            title = f"{standard} {section}".strip() if standard else f"Rule {rule_id}"
            out.append(
                CitationItem(
                    source_id=f"rule:{rule_id}",
                    title=title,
                    ref=section or rule_id,
                    excerpt=excerpt,
                )
            )
            break
    return out


def _owner_suggestion(issue_context: Dict[str, Any]) -> tuple[str, float]:
    class_a = str(issue_context.get("class_a") or "")
    class_b = str(issue_context.get("class_b") or "")
    discipline_a = str(issue_context.get("discipline_a") or "")
    discipline_b = str(issue_context.get("discipline_b") or "")
    hints = " ".join([class_a, class_b, discipline_a, discipline_b]).lower()

    if any(token in hints for token in ("pipe", "sanitary", "vvs")):
        return "VVS", 0.9
    if any(token in hints for token in ("drain", "kloak")):
        return "Kloak", 0.9
    if any(token in hints for token in ("cable", "conduit", "tray", "el", "elect")):
        return "EL", 0.9
    if any(token in hints for token in ("duct", "vent")):
        return "Ventilation", 0.9
    if discipline_a or discipline_b:
        owner = discipline_a or discipline_b
        return owner, 0.6
    return "", 0.3


def _responsibility_missing(issue_context: Dict[str, Any]) -> bool:
    class_a = str(issue_context.get("class_a") or "").strip()
    class_b = str(issue_context.get("class_b") or "").strip()
    discipline_a = str(issue_context.get("discipline_a") or "").strip()
    discipline_b = str(issue_context.get("discipline_b") or "").strip()
    class_known = any(item and item.lower() != "unknown" for item in (class_a, class_b))
    discipline_known = bool(discipline_a or discipline_b)
    return not class_known and not discipline_known


def _moveability_status(issue_context: Dict[str, Any]) -> tuple[bool, List[str]]:
    constraints = issue_context.get("constraints")
    if not isinstance(constraints, dict):
        return False, ["Constraints payload mangler."]
    missing: List[str] = []
    for side in ("A", "B"):
        side_data = constraints.get(side) or {}
        if not isinstance(side_data, dict):
            missing.append(f"{side}: constraints mangler.")
            continue
        if side_data.get("max_move_m") is None:
            missing.append(f"{side}: max_move_m mangler.")
        if side_data.get("z_allowed") is None:
            missing.append(f"{side}: z_allowed mangler.")
    return len(missing) == 0, missing


def _chips(
    issue_context: Dict[str, Any],
    owner: str,
    owner_confidence: float,
    diagnostics: AiDiagnostics,
) -> List[AiChip]:
    metrics = dict(issue_context.get("metrics") or {})
    return [
        AiChip("Issue", str(issue_context.get("issue_id") or "-")),
        AiChip(
            "Class",
            f"{issue_context.get('class_a') or 'Unknown'} vs {issue_context.get('class_b') or 'Unknown'}",
        ),
        AiChip("Rule", str(issue_context.get("rule_id") or "-")),
        AiChip(
            "Geometry",
            (
                f"{float(metrics.get('min_distance_m') or 0.0):.3f}m / "
                f"{float(metrics.get('required_clearance_m') or 0.0):.3f}m"
            ),
        ),
        AiChip("Owner", f"{owner or '-'} ({owner_confidence:.2f})"),
        AiChip("Confidence", f"{diagnostics.confidence:.2f}"),
    ]


def _status_badge(issue_context: Dict[str, Any]) -> str:
    metrics = dict(issue_context.get("metrics") or {})
    min_d = float(metrics.get("min_distance_m") or 0.0)
    req = float(metrics.get("required_clearance_m") or 0.0)
    eps = float(metrics.get("eps") or 0.0001)
    if min_d <= eps:
        return "CLASH"
    if min_d < req:
        return "WARNING"
    return "OK"


def _constraints_table(issue_context: Dict[str, Any]) -> List[TableRow]:
    rows: List[TableRow] = []
    constraints = issue_context.get("constraints") or {}
    for side in ("A", "B"):
        side_data = constraints.get(side) or {}
        rows.append(TableRow(f"{side}.movability", str(side_data.get("movability") or "-")))
        rows.append(
            TableRow(
                f"{side}.max_move_m",
                str(side_data.get("max_move_m") if side_data.get("max_move_m") is not None else "-"),
            )
        )
        rows.append(
            TableRow(
                f"{side}.z_allowed",
                str(side_data.get("z_allowed") if side_data.get("z_allowed") is not None else "-"),
            )
        )
        rows.append(TableRow(f"{side}.protected", str(bool(side_data.get("protected")))))
    return rows


def _trace_preview_lines(
    *,
    issue_context: Dict[str, Any],
    citations_count: int,
    fixes_count: int,
) -> List[str]:
    metrics = dict(issue_context.get("metrics") or {})
    return [
        f"issue={issue_context.get('issue_id') or '-'}",
        f"rule={issue_context.get('rule_id') or '-'} citations={citations_count}",
        f"method={metrics.get('method') or '-'} minDistance={metrics.get('min_distance_m')}",
        f"fixCandidates={fixes_count}",
    ]


def _fix_summary(item: FixCandidate) -> FixCandidateSummary:
    dx, dy, dz = item.vector
    return FixCandidateSummary(
        fix_id=item.fix_id,
        target_element=item.target_element,
        solves_text=f"Solves {len(item.solves_issue_ids)} issues",
        creates_text=f"Creates {int(item.creates_new_issue_estimate)} new",
        move_text=f"Move {dx:+.3f},{dy:+.3f},{dz:+.3f} m",
        clearance_text=f"Min clearance after: {item.min_clearance_after:.3f} m",
        violations_text=(
            ", ".join(item.violates_constraints) if item.violates_constraints else "None"
        ),
        why=list(item.explanation or []),
        score=float(item.score),
    )


def _discipline_pair(issue: Dict[str, Any]) -> str:
    a = str(issue.get("discipline_a") or issue.get("class_a") or "unknown").strip().lower()
    b = str(issue.get("discipline_b") or issue.get("class_b") or "unknown").strip().lower()
    return "|".join(sorted([a, b]))


def _issue_center(
    issue: Dict[str, Any],
    aabbs: Dict[str, Tuple[float, float, float, float, float, float]],
) -> Optional[Tuple[float, float, float]]:
    center = issue.get("center")
    if isinstance(center, (tuple, list)) and len(center) == 3:
        try:
            return (float(center[0]), float(center[1]), float(center[2]))
        except Exception:
            return None
    guid_a = str(issue.get("guid_a") or "")
    guid_b = str(issue.get("guid_b") or "")
    bbox_a = aabbs.get(guid_a)
    bbox_b = aabbs.get(guid_b)
    if not bbox_a or not bbox_b:
        return None
    c_a = (
        (float(bbox_a[0]) + float(bbox_a[3])) * 0.5,
        (float(bbox_a[1]) + float(bbox_a[4])) * 0.5,
        (float(bbox_a[2]) + float(bbox_a[5])) * 0.5,
    )
    c_b = (
        (float(bbox_b[0]) + float(bbox_b[3])) * 0.5,
        (float(bbox_b[1]) + float(bbox_b[4])) * 0.5,
        (float(bbox_b[2]) + float(bbox_b[5])) * 0.5,
    )
    return ((c_a[0] + c_b[0]) * 0.5, (c_a[1] + c_b[1]) * 0.5, (c_a[2] + c_b[2]) * 0.5)


def _distance(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> float:
    return math.sqrt(
        (float(a[0]) - float(b[0])) ** 2
        + (float(a[1]) - float(b[1])) ** 2
        + (float(a[2]) - float(b[2])) ** 2
    )


def _translate_aabb(
    aabb: Optional[Tuple[float, float, float, float, float, float]],
    dx: float,
    dy: float,
    dz: float,
) -> Optional[Tuple[float, float, float, float, float, float]]:
    if not aabb:
        return None
    return (
        float(aabb[0]) + float(dx),
        float(aabb[1]) + float(dy),
        float(aabb[2]) + float(dz),
        float(aabb[3]) + float(dx),
        float(aabb[4]) + float(dy),
        float(aabb[5]) + float(dz),
    )


def _estimate_created_issues(
    *,
    moved_aabb: Tuple[float, float, float, float, float, float],
    moved_guid: str,
    all_aabbs: Dict[str, Tuple[float, float, float, float, float, float]],
    clearance_m: float,
) -> int:
    count = 0
    for other_guid, other_aabb in all_aabbs.items():
        if other_guid == moved_guid:
            continue
        dist, _pa, _pb = aabb_distance_and_points(moved_aabb, other_aabb)
        if float(dist) < float(clearance_m):
            count += 1
    return int(count)


def _vec_len(vector: Iterable[float]) -> float:
    vals = list(vector)
    if len(vals) != 3:
        return 0.0
    return math.sqrt(float(vals[0]) ** 2 + float(vals[1]) ** 2 + float(vals[2]) ** 2)


def _constraints_by_guid(project_context: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = defaultdict(dict)
    for issue in list(project_context.get("issues") or []):
        guid_a = str(issue.get("guid_a") or "")
        guid_b = str(issue.get("guid_b") or "")
        constraints = issue.get("constraints") or {}
        if guid_a:
            out[guid_a].update(constraints.get("A") or {})
        if guid_b:
            out[guid_b].update(constraints.get("B") or {})
    return out


def _target_side(active_issue: Dict[str, Any], moved_guid: str) -> str:
    if str(active_issue.get("guid_a") or "") == moved_guid:
        return "A"
    if str(active_issue.get("guid_b") or "") == moved_guid:
        return "B"
    return "A"
