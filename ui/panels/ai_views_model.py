from __future__ import annotations

from dataclasses import dataclass
import math
import re
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from models import Element, Issue


@dataclass(frozen=True)
class AiCardRow:
    id: str
    label: str
    count: int = 0
    subtitle: str = ""
    element_ids: Tuple[str, ...] = tuple()
    risk_score: float = 0.0


@dataclass(frozen=True)
class AiViewCard:
    id: str
    priority: int
    icon: str
    title: str
    count: int
    description: str
    primary_label: str
    secondary_label: str
    primary_enabled: bool
    secondary_enabled: bool
    primary_disabled_reason: str = ""
    secondary_disabled_reason: str = ""
    rows: Tuple[AiCardRow, ...] = tuple()
    element_ids: Tuple[str, ...] = tuple()


@dataclass(frozen=True)
class ModelHealthBullet:
    id: str
    text: str
    target_card_id: str


@dataclass(frozen=True)
class ModelHealthSummary:
    score: int
    status: str
    bullets: Tuple[ModelHealthBullet, ...] = tuple()


@dataclass(frozen=True)
class AiWorkflowStep:
    id: str
    number: int
    title: str
    status: str  # active | done
    description: str
    action_id: str
    action_label: str
    action_enabled: bool
    disabled_reason: str = ""


@dataclass(frozen=True)
class AiWorkflowBanner:
    text: str
    action_id: str
    action_enabled: bool
    disabled_reason: str = ""


@dataclass(frozen=True)
class AiViewsWorkflowState:
    next_step: str
    current_step: int = 1
    completed_steps: Tuple[int, ...] = tuple()
    is_complete: bool = False
    complete_message: str = "Quick start complete"
    complete_action_id: str = "quickStartRestart"
    complete_action_label: str = "Run again"
    steps: Tuple[AiWorkflowStep, ...] = tuple()
    banner: Optional[AiWorkflowBanner] = None
    disabled_reasons: Tuple[Tuple[str, str], ...] = tuple()


@dataclass(frozen=True)
class AiViewsModel:
    empty_message: str
    health: Optional[ModelHealthSummary]
    workflow: Optional[AiViewsWorkflowState] = None
    cards: Tuple[AiViewCard, ...] = tuple()


_FRIENDLY_IFC_LABELS: Dict[str, str] = {
    "ifcflowsegment": "MEP segment",
    "ifcpipesegment": "Pipe",
    "ifcductsegment": "Duct",
    "ifccablecarriersegment": "Cable tray",
    "ifcflowfitting": "Fitting",
    "ifcvalve": "Valve",
    "ifcpump": "Equipment",
    "ifcfan": "Equipment",
    "ifcwall": "Wall",
    "ifcslab": "Slab",
}


_UNCLASSIFIED_BUCKET_LABELS: Dict[str, str] = {
    "ifcpipesegment": "Pipes",
    "ifcflowsegment": "Pipes",
    "ifcductsegment": "Ducts",
    "ifccablecarriersegment": "Cable trays",
    "ifcflowfitting": "Fittings",
    "ifcvalve": "Equipment",
    "ifcpump": "Equipment",
    "ifcfan": "Equipment",
}


_CARD_PRIORITY: Dict[str, int] = {
    "clashing": 0,
    "unclassified": 1,
    "high_risk": 2,
    "recent": 3,
}


_GUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)

_QUICK_START_SPECS: Tuple[Tuple[str, str, str, str], ...] = (
    ("classify", "Fix classification", "Fix missing system/type/classification fields first.", "classify"),
    ("runClash", "Run clash test", "Run clash detection when classification is ready.", "runClash"),
    ("reviewClashes", "Review clashes", "Open results and resolve active clashes.", "reviewClashes"),
    ("highRisk", "Focus high-risk systems", "Prioritize the highest-risk systems and buckets.", "highRisk"),
)


def build_ai_views_model(
    model_state: Mapping[str, object],
    clash_state: Mapping[str, object],
    selection_state: Mapping[str, object],
    quick_start_state: Optional[Mapping[str, object]] = None,
) -> AiViewsModel:
    cards = build_ai_view_cards(model_state, clash_state, selection_state)
    elements = dict(model_state.get("elements") or {})
    if not elements:
        return AiViewsModel(
            empty_message="Load a model to use AI Views",
            health=None,
            workflow=None,
            cards=tuple(),
        )

    has_run = bool(clash_state.get("has_run") or False)
    if not has_run:
        has_run = bool(clash_state.get("issues"))

    clashing_count = int(next((card.count for card in cards if card.id == "clashing"), 0))
    unclassified_count = int(next((card.count for card in cards if card.id == "unclassified"), 0))
    high_risk_count = int(next((card.count for card in cards if card.id == "high_risk"), 0))

    high_risk_card = next((card for card in cards if card.id == "high_risk"), None)
    top_risk_label = "-"
    if high_risk_count > 0 and high_risk_card and high_risk_card.rows:
        top_risk_label = str(high_risk_card.rows[0].label or "-")

    health = compute_model_health(
        total_elements=len(elements),
        clashing_elements=clashing_count,
        unclassified_elements=unclassified_count,
        high_risk_buckets=high_risk_count,
        top_risk_label=top_risk_label,
    )
    workflow = derive_ai_views_workflow_state(
        total_elements=len(elements),
        has_run=has_run,
        clashing_count=clashing_count,
        unclassified_count=unclassified_count,
        high_risk_count=high_risk_count,
        quick_start_state=quick_start_state,
    )
    return AiViewsModel(empty_message="", health=health, workflow=workflow, cards=tuple(cards))


def build_ai_view_cards(
    model_state: Mapping[str, object],
    clash_state: Mapping[str, object],
    selection_state: Mapping[str, object],
) -> List[AiViewCard]:
    elements = dict(model_state.get("elements") or {})
    issues = list(clash_state.get("issues") or [])
    has_run = bool(clash_state.get("has_run") or False)
    if not has_run:
        has_run = bool(issues)
    active_test_name = str(clash_state.get("active_test_name") or "active test")
    class_labels = dict(model_state.get("class_labels") or {})
    recent_selected = list(selection_state.get("recent_selected") or [])

    if not elements:
        return []

    cards: List[AiViewCard] = []
    display_name_cache: Dict[str, str] = {}
    for guid, elem in elements.items():
        display_name_cache[str(guid)] = get_display_name(elem)

    involvement = _clash_involvement_counts(issues)
    clashing_ids = sorted(
        involvement.keys(),
        key=lambda guid: (-int(involvement.get(guid, 0)), display_name_cache.get(guid, guid).lower()),
    )

    clashing_rows: List[AiCardRow] = []
    for guid in clashing_ids[:10]:
        clashing_rows.append(
            AiCardRow(
                id=f"clashing:{guid}",
                label=display_name_cache.get(guid, "Element"),
                count=int(involvement.get(guid, 0)),
                subtitle="active clashes",
                element_ids=(guid,),
            )
        )
    if not clashing_rows:
        clashing_rows.append(
            AiCardRow(
                id="clashing:ok",
                label="No clashes detected",
                subtitle="Run a clash test to populate this view.",
            )
        )

    clashing_primary_reason = ""
    clashing_secondary_reason = ""
    if len(clashing_ids) <= 0:
        clashing_primary_reason = _open_clashes_disabled_reason(has_run=has_run, clashing_count=len(clashing_ids))
        clashing_secondary_reason = "No clashing elements to select."

    cards.append(
        AiViewCard(
            id="clashing",
            priority=_CARD_PRIORITY["clashing"],
            icon="!",
            title="Clashing elements",
            count=len(clashing_ids),
            description=(
                f"Elements involved in active clashes ({active_test_name}). Review and resolve these first."
                if len(clashing_ids) > 0
                else "No clashes detected. Run a clash test to populate this view."
            ),
            primary_label="Open clashes",
            secondary_label="Select all",
            primary_enabled=len(clashing_ids) > 0,
            secondary_enabled=len(clashing_ids) > 0,
            primary_disabled_reason=clashing_primary_reason,
            secondary_disabled_reason=clashing_secondary_reason,
            rows=tuple(clashing_rows),
            element_ids=tuple(clashing_ids),
        )
    )

    unclassified_ids = [
        str(guid)
        for guid, elem in elements.items()
        if _is_unclassified_element(elem, str(class_labels.get(str(guid), "") or ""))
    ]
    unclassified_ids = _dedupe(unclassified_ids)
    unclassified_elements = {guid: elements[guid] for guid in unclassified_ids if guid in elements}
    unclassified_buckets = bucketize_elements(unclassified_elements)
    unclassified_rows: List[AiCardRow] = []
    for label, guids in sorted(unclassified_buckets.items(), key=lambda item: (-len(item[1]), item[0].lower())):
        unclassified_rows.append(
            AiCardRow(
                id=f"unclassified:{label}",
                label=label,
                count=len(guids),
                subtitle="elements",
                element_ids=tuple(guids),
            )
        )
    if not unclassified_rows:
        unclassified_rows.append(
            AiCardRow(
                id="unclassified:ok",
                label="All elements classified ✅",
            )
        )

    cards.append(
        AiViewCard(
            id="unclassified",
            priority=_CARD_PRIORITY["unclassified"],
            icon="?",
            title="Unclassified elements",
            count=len(unclassified_ids),
            description="Missing system/type/classification reduces filtering and auto-fix. Classify these first.",
            primary_label="Classify now",
            secondary_label="Select all",
            primary_enabled=len(unclassified_ids) > 0,
            secondary_enabled=len(unclassified_ids) > 0,
            primary_disabled_reason="All elements are classified.",
            secondary_disabled_reason="No unclassified elements to select.",
            rows=tuple(unclassified_rows),
            element_ids=tuple(unclassified_ids),
        )
    )

    high_risk_rows, high_risk_ids = _build_high_risk_rows(elements, issues)
    high_risk_count = len(high_risk_rows)
    if high_risk_count <= 0:
        high_risk_rows = [
            AiCardRow(
                id="high-risk:ok",
                label="No high-risk systems detected",
            )
        ]
    cards.append(
        AiViewCard(
            id="high_risk",
            priority=_CARD_PRIORITY["high_risk"],
            icon="^",
            title="High-risk systems",
            count=high_risk_count,
            description="Systems with the most clashes / lowest clearance. Resolve these early.",
            primary_label="Review high-risk",
            secondary_label="See ranking",
            primary_enabled=high_risk_count > 0,
            secondary_enabled=high_risk_count > 0,
            primary_disabled_reason="No high-risk systems found.",
            secondary_disabled_reason="No ranking available without clashes.",
            rows=tuple(high_risk_rows),
            element_ids=tuple(high_risk_ids),
        )
    )

    recent_ids = [guid for guid in _dedupe(recent_selected) if guid in elements][:10]
    if recent_ids:
        recent_rows = [
            AiCardRow(
                id=f"recent:{guid}",
                label=display_name_cache.get(guid, "Element"),
                count=0,
                subtitle="",
                element_ids=(guid,),
            )
            for guid in recent_ids
        ]
        cards.append(
            AiViewCard(
                id="recent",
                priority=_CARD_PRIORITY["recent"],
                icon="*",
                title="Recently selected",
                count=len(recent_rows),
                description="Quick access to your recent picks.",
                primary_label="Show list",
                secondary_label="Clear",
                primary_enabled=True,
                secondary_enabled=True,
                rows=tuple(recent_rows),
                element_ids=tuple(recent_ids),
            )
        )

    cards.sort(key=lambda card: int(card.priority))
    return cards


def get_display_name(elem: Element) -> str:
    if elem is None:
        return "Element"

    raw_name = str(getattr(elem, "name", "") or "").strip()
    cleaned_name = _clean_display_name(raw_name)
    if _is_meaningful_name(cleaned_name, elem):
        return _truncate_text(cleaned_name, 40)

    ifc_type = str(getattr(elem, "type", "") or "").strip()
    lower = ifc_type.lower()
    friendly = _friendly_ifc_label(ifc_type)

    if lower in ("ifcpipesegment", "ifcflowsegment"):
        diameter = _extract_diameter_mm(elem)
        return f"Pipe {diameter}" if diameter else "Pipe"
    if lower == "ifcductsegment":
        duct_size = _extract_rect_size_mm(elem)
        return f"Duct {duct_size}" if duct_size else "Duct"
    if lower == "ifccablecarriersegment":
        tray_size = _extract_rect_size_mm(elem)
        return f"Cable tray {tray_size}" if tray_size else "Cable tray"
    if lower == "ifcflowfitting":
        return "Fitting"
    if lower == "ifcvalve":
        return "Valve"
    if lower in ("ifcpump", "ifcfan"):
        return "Equipment"

    return friendly


def bucketize_elements(elements: Mapping[str, Element]) -> Dict[str, List[str]]:
    buckets: Dict[str, List[str]] = {
        "Pipes": [],
        "Ducts": [],
        "Cable trays": [],
        "Fittings": [],
        "Equipment": [],
        "Other": [],
    }
    for guid, elem in elements.items():
        lower = str(getattr(elem, "type", "") or "").strip().lower()
        bucket = _UNCLASSIFIED_BUCKET_LABELS.get(lower, "Other")
        buckets.setdefault(bucket, []).append(str(guid))
    return {label: guids for label, guids in buckets.items() if guids}


def compute_risk_score(clash_count: int, element_count: int, *, avg_involvement: float = 0.0) -> float:
    base = float(clash_count) * 10.0
    spread = float(element_count) * 1.2
    involvement_term = float(avg_involvement) * 2.0
    return round(base + spread + involvement_term, 2)


def compute_model_health(
    *,
    total_elements: int,
    clashing_elements: int,
    unclassified_elements: int,
    high_risk_buckets: int,
    top_risk_label: str,
) -> ModelHealthSummary:
    score = 100.0

    clash_penalty = 0.0
    if clashing_elements > 0:
        clash_penalty = min(40.0, 10.0 + (8.0 * math.log2(1.0 + float(clashing_elements))))

    unclassified_penalty = 0.0
    if unclassified_elements > 0:
        unclassified_penalty = min(30.0, 8.0 + (6.0 * math.log2(1.0 + float(unclassified_elements))))

    risk_penalty = 10.0 if high_risk_buckets > 0 else 0.0

    score -= clash_penalty
    score -= unclassified_penalty
    score -= risk_penalty
    score_int = max(0, min(100, int(round(score))))

    if score_int >= 80:
        status = "Good"
    elif score_int >= 50:
        status = "Needs attention"
    else:
        status = "Critical"

    bullets = [
        ModelHealthBullet(
            id="health:unclassified",
            text=f"{int(unclassified_elements)} unclassified elements",
            target_card_id="unclassified",
        ),
        ModelHealthBullet(
            id="health:clashing",
            text=f"{int(clashing_elements)} clashing elements",
            target_card_id="clashing",
        ),
    ]

    if top_risk_label and top_risk_label != "-":
        bullets.append(
            ModelHealthBullet(
                id="health:top-risk",
                text=f"Top risk: {top_risk_label}",
                target_card_id="high_risk",
            )
        )

    return ModelHealthSummary(score=score_int, status=status, bullets=tuple(bullets))


def derive_ai_views_workflow_state(
    *,
    total_elements: int,
    has_run: bool,
    clashing_count: int,
    unclassified_count: int,
    high_risk_count: int,
    quick_start_state: Optional[Mapping[str, object]] = None,
) -> AiViewsWorkflowState:
    del unclassified_count
    del high_risk_count
    if int(total_elements) <= 0:
        return AiViewsWorkflowState(next_step="done", steps=tuple(), banner=None, disabled_reasons=tuple())

    max_steps = len(_QUICK_START_SPECS)
    current_step, completed_steps = _normalize_quick_start_state(
        quick_start_state=quick_start_state,
        max_steps=max_steps,
    )
    is_complete = current_step > max_steps
    disabled: Dict[str, str] = {}

    steps: List[AiWorkflowStep] = []
    next_step = "done"
    if not is_complete:
        active_idx = max(0, int(current_step) - 1)
        step_id, title, description, action_id = _QUICK_START_SPECS[active_idx]
        next_step = str(step_id)
        steps.append(
            AiWorkflowStep(
                id=step_id,
                number=int(active_idx + 1),
                title=title,
                status="active",
                description=description,
                action_id=action_id,
                action_label="Go",
                action_enabled=True,
                disabled_reason="",
            )
        )

    open_clash_reason = _open_clashes_disabled_reason(has_run=bool(has_run), clashing_count=int(clashing_count))
    if open_clash_reason:
        disabled["openClashes"] = open_clash_reason

    return AiViewsWorkflowState(
        next_step=next_step,
        current_step=int(current_step),
        completed_steps=tuple(completed_steps),
        is_complete=bool(is_complete),
        complete_message="Quick start complete",
        complete_action_id="quickStartRestart",
        complete_action_label="Run again",
        steps=tuple(steps),
        banner=None,
        disabled_reasons=tuple(sorted(disabled.items(), key=lambda item: item[0])),
    )


def _normalize_quick_start_state(
    *,
    quick_start_state: Optional[Mapping[str, object]],
    max_steps: int,
) -> Tuple[int, Tuple[int, ...]]:
    completed_steps: List[int] = []
    raw_completed = quick_start_state.get("completedSteps") if isinstance(quick_start_state, Mapping) else []
    for raw in list(raw_completed or []):
        try:
            step_number = int(raw)
        except Exception:
            continue
        if 1 <= step_number <= int(max_steps) and step_number not in completed_steps:
            completed_steps.append(step_number)
    completed_steps.sort()

    raw_current = quick_start_state.get("currentStep") if isinstance(quick_start_state, Mapping) else 1
    try:
        current_step = int(raw_current)
    except Exception:
        current_step = 1
    if current_step < 1:
        current_step = 1
    if current_step > int(max_steps) + 1:
        current_step = int(max_steps) + 1

    for step_number in range(1, int(max_steps) + 1):
        if step_number not in completed_steps:
            break
    else:
        return int(max_steps) + 1, tuple(completed_steps)

    while current_step in completed_steps and current_step <= int(max_steps):
        current_step += 1
    if current_step > int(max_steps):
        for step_number in range(1, int(max_steps) + 1):
            if step_number not in completed_steps:
                current_step = step_number
                break

    return int(current_step), tuple(completed_steps)


def _build_next_banner(
    *,
    next_step: str,
    unclassified_count: int,
    clashing_count: int,
    high_risk_count: int,
) -> Optional[AiWorkflowBanner]:
    if next_step == "classify":
        return AiWorkflowBanner(
            text=f"Next: Classify {int(unclassified_count)} elements",
            action_id="classify",
            action_enabled=True,
        )
    if next_step == "runClash":
        return AiWorkflowBanner(
            text="Next: Run a clash test",
            action_id="runClash",
            action_enabled=True,
        )
    if next_step == "reviewClashes":
        return AiWorkflowBanner(
            text=f"Next: Review {int(clashing_count)} clashing elements",
            action_id="reviewClashes",
            action_enabled=True,
        )
    if next_step == "highRisk":
        return AiWorkflowBanner(
            text=f"Next: Focus top {int(high_risk_count)} high-risk systems",
            action_id="highRisk",
            action_enabled=True,
        )
    return AiWorkflowBanner(
        text="Workflow complete: no urgent AI actions right now.",
        action_id="done",
        action_enabled=False,
        disabled_reason="All workflow steps are done.",
    )


def _open_clashes_disabled_reason(*, has_run: bool, clashing_count: int) -> str:
    if int(clashing_count) > 0:
        return ""
    if not bool(has_run):
        return "No clashes yet. Run a clash test first."
    return "No clashes in latest run."


def _build_high_risk_rows(elements: Mapping[str, Element], issues: Sequence[Issue]) -> Tuple[List[AiCardRow], List[str]]:
    if not issues:
        return [], []

    involvement = _clash_involvement_counts(issues)
    buckets: Dict[str, Dict[str, object]] = {}
    for issue in issues:
        issue_guids = _issue_guids(issue)
        issue_bucket_labels: set[str] = set()
        for guid in issue_guids:
            elem = elements.get(guid)
            for label in _risk_bucket_labels(elem):
                issue_bucket_labels.add(label)
                entry = buckets.setdefault(label, {"issue_count": 0, "guids": []})
                guids = entry.get("guids") or []
                if isinstance(guids, list):
                    guids.append(guid)
        for label in issue_bucket_labels:
            entry = buckets.setdefault(label, {"issue_count": 0, "guids": []})
            entry["issue_count"] = int(entry.get("issue_count", 0)) + 1

    rows: List[AiCardRow] = []
    merged_guids: List[str] = []
    for label, payload in buckets.items():
        guids = _dedupe(payload.get("guids") or []) if isinstance(payload, dict) else []
        merged_guids.extend(guids)
        issue_count = int(payload.get("issue_count", 0)) if isinstance(payload, dict) else 0
        avg_involvement = (
            sum(float(involvement.get(guid, 0)) for guid in guids) / float(len(guids)) if guids else 0.0
        )
        risk_score = compute_risk_score(issue_count, len(guids), avg_involvement=avg_involvement)
        rows.append(
            AiCardRow(
                id=f"high-risk:{label}",
                label=label,
                count=issue_count,
                subtitle="risk score",
                element_ids=tuple(guids),
                risk_score=risk_score,
            )
        )

    rows.sort(key=lambda row: (-float(row.risk_score), -int(row.count), row.label.lower()))
    return rows[:10], _dedupe(merged_guids)


def _risk_bucket_labels(elem: Optional[Element]) -> List[str]:
    if elem is None:
        return ["Type: Other"]

    systems = _element_system_names(elem)
    if systems:
        return [f"System: {systems[0]}"]

    discipline = str(getattr(elem, "discipline", "") or "").strip()
    if discipline and discipline.lower() != "unknown":
        return [f"Discipline: {discipline}"]

    lower = str(getattr(elem, "type", "") or "").strip().lower()
    bucket = _UNCLASSIFIED_BUCKET_LABELS.get(lower, "Other")
    return [f"Type: {bucket}"]


def _clash_involvement_counts(issues: Sequence[Issue]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for issue in issues:
        for guid in _issue_guids(issue):
            counts[guid] = int(counts.get(guid, 0)) + 1
    return counts


def _issue_guids(issue: Issue) -> List[str]:
    guids: List[str] = []
    guid_a = str(getattr(issue, "guid_a", "") or "").strip()
    guid_b = str(getattr(issue, "guid_b", "") or "").strip()
    if guid_a:
        guids.append(guid_a)
    if guid_b:
        guids.append(guid_b)
    return guids


def _is_unclassified_element(elem: Element, class_label: str) -> bool:
    normalized = str(class_label or "").strip().lower()
    missing_class = (not normalized) or normalized in {
        "unknown",
        "classification_unknown",
        "unclassified",
        "none",
    }
    missing_type = not bool(str(getattr(elem, "type", "") or "").strip())
    missing_system = len(_element_system_names(elem)) == 0
    return bool(missing_class or missing_type or missing_system)


def _element_system_names(elem: Element) -> List[str]:
    names: List[str] = []
    systems = getattr(elem, "systems", None)
    if isinstance(systems, list):
        names.extend(str(value).strip() for value in systems if str(value).strip())
    system_groups = getattr(elem, "system_group_names", None)
    if isinstance(system_groups, list):
        names.extend(str(value).strip() for value in system_groups if str(value).strip())
    system_name = str(getattr(elem, "system", "") or "").strip()
    if system_name:
        names.append(system_name)
    meta = getattr(elem, "ifc_meta", {}) or {}
    if isinstance(meta, dict):
        meta_systems = meta.get("system_groups") or meta.get("systems") or []
        if isinstance(meta_systems, list):
            names.extend(str(value).strip() for value in meta_systems if str(value).strip())
    return _dedupe(names)


def _friendly_ifc_label(ifc_type: str) -> str:
    lower = str(ifc_type or "").strip().lower()
    if not lower:
        return "Element"
    alias = _FRIENDLY_IFC_LABELS.get(lower)
    if alias:
        return alias

    text = str(ifc_type or "").strip()
    if text.startswith("Ifc") and len(text) > 3:
        text = text[3:]
    words = re.sub(r"([a-z])([A-Z])", r"\1 \2", text).strip()
    return words or "Element"


def _clean_display_name(name: str) -> str:
    text = str(name or "").strip()
    if not text:
        return ""
    text = text.replace("\\", "/")
    if "/" in text:
        text = text.split("/")[-1]

    if ":" in text:
        parts = [part.strip() for part in text.split(":") if part.strip()]
        if len(parts) >= 2:
            text = parts[-1]

    text = re.sub(r"\s+", " ", text).strip()
    return text


def _is_meaningful_name(name: str, elem: Element) -> bool:
    if not name:
        return False
    lower = name.lower()
    if re.fullmatch(r"\d+", name):
        return False
    if _GUID_RE.match(name):
        return False
    if len(name) >= 22 and re.fullmatch(r"[A-Za-z0-9_$]+", name):
        return False
    if lower in {"default", "none", "unnamed", "type"}:
        return False
    if lower.startswith("port_"):
        return False
    if "default" in lower:
        return False

    guid = str(getattr(elem, "guid", "") or "").strip().lower()
    if guid and lower == guid:
        return False

    ifc_type = str(getattr(elem, "type", "") or "").strip().lower()
    if ifc_type and lower == ifc_type:
        return False
    return True


def _truncate_text(text: str, limit: int) -> str:
    value = str(text or "").strip()
    if len(value) <= int(limit):
        return value
    return value[: max(1, int(limit) - 1)].rstrip() + "..."


def _extract_diameter_mm(elem: Element) -> str:
    for value in _iter_numeric_meta_values(elem, {
        "diameter",
        "nominaldiameter",
        "nominal_diameter",
        "dn",
        "outsidediameter",
    }):
        mm = _to_mm(value)
        if mm is not None and mm > 0.0:
            return f"Ø{int(round(mm))}"
    return ""


def _extract_rect_size_mm(elem: Element) -> str:
    width = None
    height = None
    for key, value in _iter_key_values(elem):
        norm = key.lower().replace(" ", "").replace("_", "")
        if norm in {"width", "nominalwidth", "overallwidth"}:
            width = _to_mm(value)
        elif norm in {"height", "nominalheight", "overallheight"}:
            height = _to_mm(value)
    if width and height and width > 0.0 and height > 0.0:
        return f"{int(round(width))}x{int(round(height))}"
    return ""


def _iter_numeric_meta_values(elem: Element, keys: set[str]) -> Iterable[float]:
    for key, value in _iter_key_values(elem):
        normalized = key.lower().replace(" ", "").replace("_", "")
        if normalized in keys:
            try:
                yield float(value)
            except Exception:
                continue


def _iter_key_values(elem: Element) -> Iterable[Tuple[str, object]]:
    meta = getattr(elem, "ifc_meta", {}) or {}
    if isinstance(meta, dict):
        for group_key in ("item", "type"):
            group = meta.get(group_key) or {}
            if isinstance(group, dict):
                for key, value in group.items():
                    yield str(key), value
        for bucket_key in ("psets", "qtos", "type_psets", "type_qtos"):
            bucket = meta.get(bucket_key) or {}
            if not isinstance(bucket, dict):
                continue
            for _, payload in bucket.items():
                if not isinstance(payload, dict):
                    continue
                for key, value in payload.items():
                    yield str(key), value


def _to_mm(value: object) -> Optional[float]:
    try:
        numeric = float(value)
    except Exception:
        return None
    abs_value = abs(numeric)
    if abs_value <= 0.0:
        return None

    # Most IFC values here are in meters. Treat large values as already mm.
    if abs_value > 20.0:
        return abs_value
    return abs_value * 1000.0


def _dedupe(values: Iterable[str]) -> List[str]:
    ordered: List[str] = []
    for value in values:
        current = str(value or "").strip()
        if current and current not in ordered:
            ordered.append(current)
    return ordered
