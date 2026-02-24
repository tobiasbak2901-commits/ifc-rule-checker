from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from detection import SpatialIndex
from clash_detection import Bounds
from io_ifc import IfcRepository
from models import Element, Issue, MeasurementEntry, SearchSet
from rules import RulePack


@dataclass
class ProjectState:
    ifc_model: Optional[IfcRepository] = None
    ifc_index: Dict[str, Element] = field(default_factory=dict)
    spatial_index: Optional[SpatialIndex] = None
    aabbs: Dict[str, tuple] = field(default_factory=dict)
    bcf_issues: List[Issue] = field(default_factory=list)
    selected_issue: Optional[Issue] = None
    selected_elements: List[str] = field(default_factory=list)
    ifc_path: Optional[str] = None
    rulepack: RulePack = field(default_factory=RulePack)
    rulepack_id: str = "core-v1"
    rulepack_label: str = "Core v1.0"
    rule_overrides: Dict[str, float] = field(default_factory=dict)
    search_sets: List[SearchSet] = field(default_factory=list)
    search_set_ifc_token: int = 0
    measurements: List[MeasurementEntry] = field(default_factory=list)
    section_box_enabled: bool = False
    section_box_bounds: Optional[Tuple[float, float, float, float, float, float]] = None
    active_model: Optional[Any] = None
    viewer_model_loaded: bool = False
    viewer_warning: Optional[str] = None
    scene_offset: Optional[Tuple[float, float, float]] = None
    viewer_diagnostics: Dict[str, object] = field(default_factory=dict)
    clash_world_bounds: Dict[str, Bounds] = field(default_factory=dict)
    clash_units_scale: float = 1.0
    clash_invalid_geometry: Dict[str, str] = field(default_factory=dict)
    ui_panel_layout_state: Dict[str, object] = field(default_factory=dict)
    _primary_selected_id: Optional[str] = field(default=None, init=False, repr=False)

    @staticmethod
    def _normalize_selection(keys: List[str]) -> List[str]:
        normalized: List[str] = []
        for value in list(keys or []):
            guid = str(value or "").strip()
            if not guid or guid in normalized:
                continue
            normalized.append(guid)
        return normalized

    @property
    def selectedElementKeys(self) -> List[str]:
        """SelectionStore alias used by UI contracts (Tree <-> Viewer <-> Properties)."""
        return list(self.selected_elements or [])

    @selectedElementKeys.setter
    def selectedElementKeys(self, keys: List[str]) -> None:
        normalized = self._normalize_selection(keys)
        primary = str(self._primary_selected_id or "").strip()
        if not primary or primary not in normalized:
            primary = normalized[0] if normalized else ""
        if primary and normalized and normalized[0] != primary:
            normalized = [primary] + [guid for guid in normalized if guid != primary]
        self.selected_elements = list(normalized)
        self._primary_selected_id = primary or None

    @property
    def selectedIds(self) -> List[str]:
        return list(self.selected_elements or [])

    @selectedIds.setter
    def selectedIds(self, keys: List[str]) -> None:
        self.selectedElementKeys = list(keys or [])

    @property
    def primarySelectedId(self) -> Optional[str]:
        primary = str(self._primary_selected_id or "").strip()
        if primary and primary in self.selected_elements:
            return primary
        selected = list(self.selected_elements or [])
        return selected[0] if selected else None

    @primarySelectedId.setter
    def primarySelectedId(self, value: Optional[str]) -> None:
        primary = str(value or "").strip()
        if not primary:
            self._primary_selected_id = None
            return
        ordered = [primary] + [guid for guid in self.selected_elements if guid != primary]
        self.selected_elements = self._normalize_selection(ordered)
        self._primary_selected_id = primary

    def reset(self):
        self.ifc_model = None
        self.ifc_index.clear()
        self.spatial_index = None
        self.aabbs.clear()
        self.bcf_issues.clear()
        self.selected_issue = None
        self.selected_elements.clear()
        self.ifc_path = None
        self.rulepack = RulePack()
        self.rulepack_id = "core-v1"
        self.rulepack_label = "Core v1.0"
        self.rule_overrides.clear()
        self.search_sets.clear()
        self.search_set_ifc_token = 0
        self.measurements.clear()
        self.section_box_enabled = False
        self.section_box_bounds = None
        self.active_model = None
        self.viewer_model_loaded = False
        self.viewer_warning = None
        self.scene_offset = None
        self.viewer_diagnostics.clear()
        self.clash_world_bounds.clear()
        self.clash_units_scale = 1.0
        self.clash_invalid_geometry.clear()
        self.ui_panel_layout_state.clear()
        self._primary_selected_id = None


project_state = ProjectState()
