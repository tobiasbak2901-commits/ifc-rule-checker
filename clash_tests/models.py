from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple


class ClashType(str, Enum):
    HARD = "hard"
    TOLERANCE = "tolerance"
    CLEARANCE = "clearance"


class ClashResultStatus(str, Enum):
    NEW = "new"
    TRIAGED = "triaged"
    CLOSED = "closed"


IGNORE_SAME_ELEMENT = "same_element"
IGNORE_SAME_SYSTEM = "same_system"
IGNORE_SAME_FILE = "same_file"
IGNORE_NAME_PATTERN = "name_pattern"
IGNORE_IFCTYPE_IN = "ifc_type_in"

GROUP_ELEMENT_A = "element_a"
GROUP_PROXIMITY = "proximity"
GROUP_LEVEL = "level"


@dataclass
class SearchSet:
    id: str
    name: str
    query: List[Dict[str, Any]] = field(default_factory=list)
    manual_guids: List[str] = field(default_factory=list)
    enabled: bool = True


@dataclass
class IgnoreRule:
    key: str
    enabled: bool = True
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ClashTest:
    id: str
    name: str
    search_set_ids_a: List[str] = field(default_factory=list)
    search_set_ids_b: List[str] = field(default_factory=list)
    clash_type: ClashType = ClashType.HARD
    threshold_mm: float = 0.0
    ignore_rules: List[IgnoreRule] = field(default_factory=list)
    grouping_order: List[str] = field(default_factory=list)
    proximity_meters: float = 6.0
    auto_viewpoint: bool = True
    auto_screenshot: bool = False
    created_ts: float = field(default_factory=time.time)
    updated_ts: float = field(default_factory=time.time)


@dataclass
class ClashResult:
    id: str
    test_id: str
    elementA_id: str
    elementB_id: str
    elementA_guid: Optional[str]
    elementB_guid: Optional[str]
    rule_triggered: str
    min_distance_m: float
    penetration_depth_m: float
    method: str
    timestamp: float
    level_id: str
    proximity_cell: str
    elementA_key: str
    clash_key: str = ""
    status: ClashResultStatus = ClashResultStatus.NEW
    assignee: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    group_id: Optional[str] = None
    group_name: Optional[str] = None
    clash_name: Optional[str] = None
    clash_midpoint: Optional[Tuple[float, float, float]] = None
    first_seen_at: Optional[float] = None
    last_seen_at: Optional[float] = None
    reopen_count: int = 0
    reopened: bool = False
    diagnostics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ClashGroup:
    id: str
    test_id: str
    name: str
    elementA_key: str
    proximity_cell: str
    level_id: str
    result_ids: List[str] = field(default_factory=list)
    created_ts: float = field(default_factory=time.time)


@dataclass
class Viewpoint:
    id: str
    test_id: str
    result_id: str
    camera_position: Tuple[float, float, float]
    camera_direction: Tuple[float, float, float]
    camera_up: Tuple[float, float, float]
    camera_type: str = "perspective"
    camera_scale: Optional[float] = None
    look_at: Optional[Tuple[float, float, float]] = None
    screenshot_path: Optional[str] = None
    screenshot_status: str = "not_requested"
    created_ts: float = field(default_factory=time.time)


def default_ignore_rules() -> List[IgnoreRule]:
    return [
        IgnoreRule(key=IGNORE_SAME_ELEMENT, enabled=True),
        IgnoreRule(key=IGNORE_SAME_SYSTEM, enabled=False),
        IgnoreRule(key=IGNORE_SAME_FILE, enabled=False),
        IgnoreRule(key=IGNORE_NAME_PATTERN, enabled=False, params={"patterns": []}),
        IgnoreRule(key=IGNORE_IFCTYPE_IN, enabled=False, params={"types": []}),
    ]


def default_grouping_order(level_available: bool) -> List[str]:
    order = [GROUP_ELEMENT_A, GROUP_PROXIMITY]
    if level_available:
        order.append(GROUP_LEVEL)
    return order


def ignore_rule_enabled(rules: Sequence[IgnoreRule], key: str) -> bool:
    wanted = str(key or "").strip().lower()
    for rule in list(rules or []):
        if str(rule.key or "").strip().lower() == wanted:
            return bool(rule.enabled)
    return False
