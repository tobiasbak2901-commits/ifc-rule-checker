from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class Element:
    guid: str
    type: str
    discipline: str
    geom_ref: str
    name: str = ""
    system: Optional[str] = None
    psets: Dict[str, Dict[str, object]] = field(default_factory=dict)
    qtos: Dict[str, Dict[str, object]] = field(default_factory=dict)
    type_name: Optional[str] = None
    type_psets: Dict[str, Dict[str, object]] = field(default_factory=dict)
    type_qtos: Dict[str, Dict[str, object]] = field(default_factory=dict)
    systems: List[str] = field(default_factory=list)
    system_group_names: List[str] = field(default_factory=list)
    ifc_meta: Dict[str, object] = field(default_factory=dict)
    utility_type: Optional[str] = None
    class_name: Optional[str] = None
    class_confidence: float = 0.0
    class_reasons: List[str] = field(default_factory=list)
    layers: List[str] = field(default_factory=list)


@dataclass
class SearchSet:
    id: str
    name: str
    enabled: bool = True
    query: List[Dict[str, Any]] = field(default_factory=list)
    manual_guids: List[str] = field(default_factory=list)
    find_definition: Optional[Dict[str, Any]] = None
    cached_matches: List[str] = field(default_factory=list)
    cache_ifc_token: Optional[str] = None
    cache_query_key: Optional[str] = None


@dataclass
class FavoritePreset:
    id: str
    name: str
    keys: List[str] = field(default_factory=list)


@dataclass
class Issue:
    guid_a: str
    guid_b: str
    rule_id: str
    severity: str
    clearance: float
    p_a: Optional[Tuple[float, float, float]]
    p_b: Optional[Tuple[float, float, float]]
    direction: Optional[Tuple[float, float, float]] = None
    viewpoint: Optional[Dict] = None
    clash_center: Optional[Tuple[float, float, float]] = None
    issue_id: Optional[str] = None
    title: Optional[str] = None
    movable_guid: Optional[str] = None
    movable_discipline: Optional[str] = None
    movable_type: Optional[str] = None
    movable_reason: Optional[str] = None
    movable_reason_codes: Optional[List[str]] = None
    fix_status: Optional[str] = None
    bcf_description: Optional[str] = None
    bcf_comments: Optional[List[str]] = None
    snapshot_bytes: Optional[bytes] = None
    snapshot_mime: Optional[str] = None
    element_a: Optional[Element] = None
    element_b: Optional[Element] = None
    utility_a: Optional[str] = None
    utility_b: Optional[str] = None
    relation: Optional[str] = None
    is_bound: Optional[bool] = None
    bbox_overlap: Optional[Tuple[float, float, float]] = None
    approx_distance: Optional[float] = None
    approx_clearance: Optional[float] = None
    search_set_names_a: List[str] = field(default_factory=list)
    search_set_names_b: List[str] = field(default_factory=list)
    group_id: Optional[str] = None
    min_distance_world: Optional[float] = None
    required_clearance_world: Optional[float] = None
    detection_method: Optional[str] = None
    clash_diagnostics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SourceCitation:
    standard: str
    rule_id: str
    section: Optional[str] = None
    clause: Optional[str] = None
    excerpt: Optional[str] = None
    page: Optional[int] = None
    url: Optional[str] = None
    note: Optional[str] = None
    yaml_path: Optional[str] = None


@dataclass
class RuleTraceItem:
    rule_id: str
    status: str
    reason: str
    source: Optional[SourceCitation] = None


@dataclass
class RuleTrace:
    matched: List[RuleTraceItem] = field(default_factory=list)
    failed: List[RuleTraceItem] = field(default_factory=list)


@dataclass
class MeasurementEntry:
    id: str
    kind: str
    p0: Tuple[float, float, float]
    p1: Tuple[float, float, float]
    value_mm: float
    units: str = "mm"
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    issue_id: Optional[str] = None
    guid_a: Optional[str] = None
    guid_b: Optional[str] = None
    label: Optional[str] = None
    method: Optional[str] = None
    status: Optional[str] = None


@dataclass
class CandidateFix:
    action: str
    params: Dict
    cost: float
    solves: int = 0
    creates: int = 0
    violations: int = 0
    score: float = 0.0
    min_clearance: Optional[float] = None
    solves_current: bool = False
    id: str = ""
    issue_id: Optional[str] = None
    transforms: List[Dict[str, Any]] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    citations: List[SourceCitation] = field(default_factory=list)
    explanation: Dict[str, Any] = field(default_factory=dict)
    trace: RuleTrace = field(default_factory=RuleTrace)


@dataclass
class SimResult:
    solves: int
    creates: int
    violations: int
    score: float


@dataclass
class Recommendation:
    top_fix: CandidateFix
    alternatives: List[CandidateFix]
    explanation: str
