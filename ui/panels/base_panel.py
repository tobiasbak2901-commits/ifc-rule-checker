from __future__ import annotations

from typing import Dict, Optional

from PySide6 import QtCore, QtWidgets


class BasePanel(QtWidgets.QWidget):
    tabChanged = QtCore.Signal(str)

    def __init__(self, title: str, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self.setObjectName("BasePanel")
        self._title = str(title or "")
        self._tab_ids: Dict[str, int] = {}
        self._tab_keys_by_index: Dict[int, str] = {}

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.tabs = QtWidgets.QTabWidget(self)
        self.tabs.setObjectName("BasePanelTabs")
        self.tabs.currentChanged.connect(self._on_tab_changed)
        root.addWidget(self.tabs, 1)

    @property
    def title(self) -> str:
        return self._title

    def add_tab(self, tab_id: str, label: str, widget: QtWidgets.QWidget) -> None:
        key = str(tab_id or f"tab_{self.tabs.count()}").strip()
        if not key:
            key = f"tab_{self.tabs.count()}"
        if key in self._tab_ids:
            idx = self._tab_ids[key]
            existing = self.tabs.widget(idx)
            if existing is not None and existing is not widget:
                existing.setParent(None)
            self.tabs.removeTab(idx)
            self._reindex_tabs()
        widget.setParent(self.tabs)
        index = self.tabs.addTab(widget, str(label or key))
        self._tab_ids[key] = int(index)
        self._tab_keys_by_index[int(index)] = key
        # Avoid duplicate headers when a panel only has a single tab.
        self.tabs.tabBar().setVisible(self.tabs.count() > 1)

    def set_active_tab(self, tab_id: str) -> None:
        key = str(tab_id or "").strip()
        idx = self._tab_ids.get(key)
        if idx is None:
            return
        if self.tabs.currentIndex() != int(idx):
            self.tabs.setCurrentIndex(int(idx))

    def active_tab(self) -> str:
        return str(self._tab_keys_by_index.get(int(self.tabs.currentIndex()), ""))

    def _on_tab_changed(self, index: int) -> None:
        self.tabChanged.emit(str(self._tab_keys_by_index.get(int(index), "")))

    def _reindex_tabs(self) -> None:
        self._tab_ids = {}
        self._tab_keys_by_index = {}
        for idx in range(self.tabs.count()):
            key = f"tab_{idx}"
            self._tab_ids[key] = idx
            self._tab_keys_by_index[idx] = key
        self.tabs.tabBar().setVisible(self.tabs.count() > 1)
