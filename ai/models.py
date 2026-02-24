from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Tuple


AIIntent = Literal[
    "EXPLAIN_CLASH",
    "SUGGEST_ACTIONS",
    "PROPOSE_FIXES",
    "CLASSIFY_HELP",
    "PROJECT_QA",
]

CitationKind = Literal["RULE", "STANDARD", "MEASURE", "GEOMETRY"]


@dataclass(frozen=True)
class ViewerState:
    active_mode: str
    camera_position: Optional[Tuple[float, float, float]] = None
    camera_target: Optional[Tuple[float, float, float]] = None
    camera_zoom: Optional[float] = None
    search_set_a: Optional[str] = None
    search_set_b: Optional[str] = None


@dataclass(frozen=True)
class SelectionItem:
    element_id: str
    ifc_type: Optional[str] = None
    discipline: Optional[str] = None
    system: Optional[str] = None
    diameter_mm: Optional[float] = None
    length_m: Optional[float] = None
    class_name: Optional[str] = None
    class_confidence: Optional[float] = None


@dataclass(frozen=True)
class ActiveIssueContext:
    issue_id: Optional[str] = None
    guid_a: Optional[str] = None
    guid_b: Optional[str] = None
    rule_id: Optional[str] = None
    clash_verdict: Optional[str] = None
    clash_type: Optional[str] = None
    method: Optional[str] = None
    min_distance_m: Optional[float] = None
    required_clearance_m: Optional[float] = None
    tolerance_m: Optional[float] = None
    search_scope_left: List[str] = field(default_factory=list)
    search_scope_right: List[str] = field(default_factory=list)
    search_count_left: Optional[int] = None
    search_count_right: Optional[int] = None


@dataclass(frozen=True)
class MeasurementState:
    enabled: bool = False
    measurement_id: Optional[str] = None
    kind: Optional[str] = None
    value_mm: Optional[float] = None
    method: Optional[str] = None


@dataclass(frozen=True)
class SectionBoxState:
    enabled: bool = False
    bounds: Optional[Tuple[float, float, float, float, float, float]] = None


@dataclass(frozen=True)
class ClassificationSummary:
    element_id: str
    discipline: Optional[str] = None
    system: Optional[str] = None
    ai_class: Optional[str] = None
    confidence: float = 0.0
    top_candidates: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class RuleTraceEntry:
    rule_id: str
    status: str
    reason: str
    trace_steps: List[str] = field(default_factory=list)
    standard_refs: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class StandardRef:
    id: str
    title: str
    doc_file: str
    page_range: Optional[str] = None
    excerpt: str = ""
    tags: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class ProjectMemoryNote:
    id: str
    created_at: str
    scope: str
    text: str
    tags: List[str] = field(default_factory=list)
    source_issue_id: Optional[str] = None


@dataclass(frozen=True)
class FixAvailability:
    status: str = "UNKNOWN"
    reasons: List[Dict[str, str]] = field(default_factory=list)


@dataclass(frozen=True)
class AIContext:
    project_id: str
    project_root: str
    viewer_state: ViewerState
    selection: List[SelectionItem] = field(default_factory=list)
    active_issue: Optional[ActiveIssueContext] = None
    measurement: Optional[MeasurementState] = None
    section_box: Optional[SectionBoxState] = None
    classification_summary: List[ClassificationSummary] = field(default_factory=list)
    rules_fired: List[RuleTraceEntry] = field(default_factory=list)
    standard_refs: List[StandardRef] = field(default_factory=list)
    project_memory: List[ProjectMemoryNote] = field(default_factory=list)
    fix_availability: Optional[FixAvailability] = None
    question: Optional[str] = None


@dataclass(frozen=True)
class AICardRequest:
    intent: AIIntent
    question: Optional[str] = None


@dataclass(frozen=True)
class Citation:
    kind: CitationKind
    id: str
    label: str
    excerpt: Optional[str] = None
    confidence: float = 1.0


@dataclass(frozen=True)
class NextAction:
    id: str
    label: str
    icon: str
    enabled: bool
    reason: str
    payload: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AICardResponse:
    title: str
    summary: str
    bullets: List[str]
    citations: List[Citation]
    assumptions: List[str]
    next_actions: List[NextAction]
    debug_trace_id: str


AICardModel = AICardResponse
