from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from PySide6 import QtCore


@dataclass
class PanelState:
    open: bool = True
    dock: str = "left"


class PanelManager(QtCore.QObject):
    stateChanged = QtCore.Signal(dict)

    def __init__(self, parent: Optional[QtCore.QObject] = None):
        super().__init__(parent)
        self._panels: Dict[str, PanelState] = {}
        self._splitter_sizes: List[int] = []

    def register_panel(self, panel_id: str, *, dock: str = "left", open: bool = True) -> None:
        pid = str(panel_id or "").strip()
        if not pid:
            return
        self._panels[pid] = PanelState(open=bool(open), dock=self._normalize_dock(dock))
        self._emit_changed()

    def has_panel(self, panel_id: str) -> bool:
        return str(panel_id) in self._panels

    def panel_state(self) -> Dict[str, Dict[str, object]]:
        return {
            pid: {"open": bool(state.open), "dock": str(state.dock)}
            for pid, state in self._panels.items()
        }

    def layout_state(self) -> Dict[str, object]:
        return {
            "panels": self.panel_state(),
            "splitterSizes": list(self._splitter_sizes or []),
        }

    def set_splitter_sizes(self, sizes: List[int]) -> None:
        normalized = [max(0, int(v)) for v in list(sizes or [])]
        if normalized == self._splitter_sizes:
            return
        self._splitter_sizes = normalized
        self._emit_changed()

    def splitter_sizes(self) -> List[int]:
        return list(self._splitter_sizes or [])

    def set_panel_open(self, panel_id: str, is_open: bool) -> None:
        pid = str(panel_id)
        if pid not in self._panels:
            return
        state = self._panels[pid]
        open_flag = bool(is_open)
        if state.open == open_flag:
            return
        state.open = open_flag
        self._emit_changed()

    def toggle_panel(self, panel_id: str) -> None:
        pid = str(panel_id)
        if pid not in self._panels:
            return
        self.set_panel_open(pid, not bool(self._panels[pid].open))

    def set_panel_dock(self, panel_id: str, dock: str) -> None:
        pid = str(panel_id)
        if pid not in self._panels:
            return
        normalized = self._normalize_dock(dock)
        state = self._panels[pid]
        if state.dock == normalized:
            return
        state.dock = normalized
        self._emit_changed()

    def get_panel_state(self, panel_id: str) -> Optional[PanelState]:
        return self._panels.get(str(panel_id))

    def apply_layout_state(self, payload: Dict[str, object]) -> None:
        data = dict(payload or {})
        raw_panels = data.get("panels")
        if not isinstance(raw_panels, dict):
            raw_panels = data
        for pid, state in dict(raw_panels or {}).items():
            if pid not in self._panels or not isinstance(state, dict):
                continue
            self._panels[pid].open = bool(state.get("open", self._panels[pid].open))
            self._panels[pid].dock = self._normalize_dock(str(state.get("dock", self._panels[pid].dock)))
        raw_sizes = data.get("splitterSizes")
        if isinstance(raw_sizes, list):
            self._splitter_sizes = [max(0, int(v)) for v in raw_sizes]
        self._emit_changed()

    @staticmethod
    def _normalize_dock(dock: str) -> str:
        value = str(dock or "").lower().strip()
        if value == "right":
            return "right"
        if value in {"left_bottom", "left-bottom", "bottom_left", "leftbottom", "bottom"}:
            return "left_bottom"
        return "left"

    def _emit_changed(self) -> None:
        self.stateChanged.emit(self.layout_state())
