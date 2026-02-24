from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from ai.models import (
    AIContext,
    ActiveIssueContext,
    ClassificationSummary,
    FixAvailability,
    MeasurementState,
    ProjectMemoryNote,
    RuleTraceEntry,
    SectionBoxState,
    SelectionItem,
    StandardRef,
    ViewerState,
)
from ai.project_memory import relevant_notes


def _safe_float(value: object) -> Optional[float]:
    try:
        out = float(value)
    except Exception:
        return None
    return out


def _safe_int(value: object) -> Optional[int]:
    try:
        return int(value)
    except Exception:
        return None


def _safe_point(value: object) -> Optional[Tuple[float, float, float]]:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        return None
    out = (_safe_float(value[0]), _safe_float(value[1]), _safe_float(value[2]))
    if any(v is None for v in out):
        return None
    return (float(out[0]), float(out[1]), float(out[2]))


def _safe_bounds(value: object) -> Optional[Tuple[float, float, float, float, float, float]]:
    if not isinstance(value, (list, tuple)) or len(value) != 6:
        return None
    numbers = [_safe_float(v) for v in value]
    if any(v is None for v in numbers):
        return None
    return (
        float(numbers[0]),
        float(numbers[1]),
        float(numbers[2]),
        float(numbers[3]),
        float(numbers[4]),
        float(numbers[5]),
    )


def load_standard_registry(registry_path: Path) -> Dict[str, StandardRef]:
    if not registry_path.exists():
        return {}
    try:
        raw = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}
    if not isinstance(raw, dict):
        return {}
    sources = raw.get("sources")
    if not isinstance(sources, list):
        return {}
    out: Dict[str, StandardRef] = {}
    for item in sources:
        if not isinstance(item, dict):
            continue
        sid = str(item.get("id") or "").strip()
        if not sid:
            continue
        ref = StandardRef(
            id=sid,
            title=str(item.get("title") or sid).strip(),
            doc_file=str(item.get("doc_file") or "").strip(),
            page_range=str(item.get("page_range") or "").strip() or None,
            excerpt=str(item.get("excerpt") or "").strip(),
            tags=[str(tag).strip() for tag in list(item.get("tags") or []) if str(tag).strip()],
        )
        out[sid] = ref
    return out


def _rulepack_standard_refs(rulepack: object, rule_id: str) -> List[str]:
    rid = str(rule_id or "").strip()
    if not rid or rulepack is None:
        return []

    for generated in list(getattr(rulepack, "generated_rules", []) or []):
        if not isinstance(generated, dict):
            continue
        if str(generated.get("id") or "") != rid:
            continue
        refs = list(generated.get("standard_refs") or [])
        source = generated.get("source")
        if isinstance(source, dict):
            refs.extend(list(source.get("standard_refs") or []))
        return [str(ref).strip() for ref in refs if str(ref).strip()]

    for utility_rule in list(getattr(rulepack, "utility_rules", []) or []):
        if str(getattr(utility_rule, "rule_id", "") or "") != rid:
            continue
        refs = list(getattr(utility_rule, "standard_refs", []) or [])
        source = getattr(utility_rule, "source", None)
        if isinstance(source, dict):
            refs.extend(list(source.get("standard_refs") or []))
        return [str(ref).strip() for ref in refs if str(ref).strip()]

    return []


def build_context(app_state: Dict[str, Any]) -> AIContext:
    project_root = Path(str(app_state.get("project_root") or ".")).resolve()
    project_id = str(app_state.get("project_id") or "ponker-project").strip() or "ponker-project"
    registry_path = Path(str(app_state.get("standards_registry_path") or project_root / "standards" / "registry.yaml"))
    if not registry_path.is_absolute():
        registry_path = (project_root / registry_path).resolve()
    registry = load_standard_registry(registry_path)

    camera = dict(app_state.get("camera") or {})
    viewer = ViewerState(
        active_mode=str(app_state.get("active_mode") or "Analyze"),
        camera_position=_safe_point(camera.get("position")),
        camera_target=_safe_point(camera.get("target")),
        camera_zoom=_safe_float(camera.get("zoom")),
        search_set_a=str((app_state.get("search_scope") or {}).get("left") or "").strip() or None,
        search_set_b=str((app_state.get("search_scope") or {}).get("right") or "").strip() or None,
    )

    selection: List[SelectionItem] = []
    for item in list(app_state.get("selection") or []):
        if not isinstance(item, dict):
            continue
        element_id = str(item.get("element_id") or item.get("id") or "").strip()
        if not element_id:
            continue
        selection.append(
            SelectionItem(
                element_id=element_id,
                ifc_type=str(item.get("ifc_type") or "").strip() or None,
                discipline=str(item.get("discipline") or "").strip() or None,
                system=str(item.get("system") or "").strip() or None,
                diameter_mm=_safe_float(item.get("diameter_mm")),
                length_m=_safe_float(item.get("length_m")),
                class_name=str(item.get("class_name") or "").strip() or None,
                class_confidence=_safe_float(item.get("class_confidence")),
            )
        )

    issue_payload = app_state.get("active_issue")
    active_issue: Optional[ActiveIssueContext] = None
    if isinstance(issue_payload, dict):
        active_issue = ActiveIssueContext(
            issue_id=str(issue_payload.get("issue_id") or "").strip() or None,
            guid_a=str(issue_payload.get("guid_a") or "").strip() or None,
            guid_b=str(issue_payload.get("guid_b") or "").strip() or None,
            rule_id=str(issue_payload.get("rule_id") or "").strip() or None,
            clash_verdict=str(issue_payload.get("clash_verdict") or "").strip() or None,
            clash_type=str(issue_payload.get("clash_type") or "").strip() or None,
            method=str(issue_payload.get("method") or "").strip() or None,
            min_distance_m=_safe_float(issue_payload.get("min_distance_m")),
            required_clearance_m=_safe_float(issue_payload.get("required_clearance_m")),
            tolerance_m=_safe_float(issue_payload.get("tolerance_m")),
            search_scope_left=[str(v).strip() for v in list(issue_payload.get("search_scope_left") or []) if str(v).strip()],
            search_scope_right=[str(v).strip() for v in list(issue_payload.get("search_scope_right") or []) if str(v).strip()],
            search_count_left=_safe_int(issue_payload.get("search_count_left")),
            search_count_right=_safe_int(issue_payload.get("search_count_right")),
        )

    measurement_payload = app_state.get("measurement")
    measurement: Optional[MeasurementState] = None
    if isinstance(measurement_payload, dict):
        measurement = MeasurementState(
            enabled=bool(measurement_payload.get("enabled")),
            measurement_id=str(measurement_payload.get("measurement_id") or "").strip() or None,
            kind=str(measurement_payload.get("kind") or "").strip() or None,
            value_mm=_safe_float(measurement_payload.get("value_mm")),
            method=str(measurement_payload.get("method") or "").strip() or None,
        )

    section_payload = app_state.get("section_box")
    section_box: Optional[SectionBoxState] = None
    if isinstance(section_payload, dict):
        section_box = SectionBoxState(
            enabled=bool(section_payload.get("enabled")),
            bounds=_safe_bounds(section_payload.get("bounds")),
        )

    classification_summary: List[ClassificationSummary] = []
    for item in list(app_state.get("classification_summary") or []):
        if not isinstance(item, dict):
            continue
        element_id = str(item.get("element_id") or "").strip()
        if not element_id:
            continue
        classification_summary.append(
            ClassificationSummary(
                element_id=element_id,
                discipline=str(item.get("discipline") or "").strip() or None,
                system=str(item.get("system") or "").strip() or None,
                ai_class=str(item.get("ai_class") or "").strip() or None,
                confidence=float(_safe_float(item.get("confidence")) or 0.0),
                top_candidates=[str(v).strip() for v in list(item.get("top_candidates") or []) if str(v).strip()][:3],
            )
        )

    rulepack = app_state.get("rulepack")
    rules_fired: List[RuleTraceEntry] = []
    standard_ref_ids: List[str] = []
    for item in list(app_state.get("rules_fired") or []):
        if not isinstance(item, dict):
            continue
        rule_id = str(item.get("rule_id") or "").strip()
        if not rule_id:
            continue
        raw_refs = [str(v).strip() for v in list(item.get("standard_refs") or []) if str(v).strip()]
        if not raw_refs:
            raw_refs = _rulepack_standard_refs(rulepack, rule_id)
        resolved_refs = [ref for ref in raw_refs if ref in registry]
        standard_ref_ids.extend(resolved_refs)
        rules_fired.append(
            RuleTraceEntry(
                rule_id=rule_id,
                status=str(item.get("status") or "fired").strip() or "fired",
                reason=str(item.get("reason") or "").strip() or "Rule fired.",
                trace_steps=[str(v).strip() for v in list(item.get("trace_steps") or []) if str(v).strip()],
                standard_refs=resolved_refs,
            )
        )

    seen = set()
    standard_refs: List[StandardRef] = []
    for ref_id in standard_ref_ids:
        if ref_id in seen:
            continue
        seen.add(ref_id)
        ref = registry.get(ref_id)
        if ref is not None:
            standard_refs.append(ref)

    memory_tags: List[str] = [
        str(tag).strip()
        for tag in list(app_state.get("memory_tags") or [])
        if str(tag).strip()
    ]
    if not memory_tags:
        for item in classification_summary:
            if item.discipline:
                memory_tags.append(item.discipline)
            if item.system:
                memory_tags.append(item.system)
            if item.ai_class:
                memory_tags.append(item.ai_class)
    project_notes = relevant_notes(project_root, memory_tags, limit=3)
    project_memory: List[ProjectMemoryNote] = []
    for note in project_notes:
        project_memory.append(
            ProjectMemoryNote(
                id=str(note.get("id") or "").strip() or "note",
                created_at=str(note.get("created_at") or "").strip(),
                scope=str(note.get("scope") or "project").strip() or "project",
                text=str(note.get("text") or "").strip(),
                tags=[str(tag).strip() for tag in list(note.get("tags") or []) if str(tag).strip()],
                source_issue_id=str(note.get("source_issue_id") or "").strip() or None,
            )
        )

    fix_availability_payload = app_state.get("fix_availability")
    fix_availability: Optional[FixAvailability] = None
    if isinstance(fix_availability_payload, dict):
        fix_availability = FixAvailability(
            status=str(fix_availability_payload.get("status") or "UNKNOWN").strip() or "UNKNOWN",
            reasons=[
                {
                    "code": str(item.get("code") or "").strip(),
                    "message": str(item.get("message") or "").strip(),
                }
                for item in list(fix_availability_payload.get("reasons") or [])
                if isinstance(item, dict)
            ],
        )

    return AIContext(
        project_id=project_id,
        project_root=str(project_root),
        viewer_state=viewer,
        selection=selection,
        active_issue=active_issue,
        measurement=measurement,
        section_box=section_box,
        classification_summary=classification_summary,
        rules_fired=rules_fired,
        standard_refs=standard_refs,
        project_memory=project_memory,
        fix_availability=fix_availability,
        question=str(app_state.get("question") or "").strip() or None,
    )


def context_to_debug_dict(context: AIContext) -> Dict[str, Any]:
    return asdict(context)
