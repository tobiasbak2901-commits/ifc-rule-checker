from __future__ import annotations

from typing import Dict, Optional

from PySide6 import QtCore, QtGui, QtWidgets

from .panel_manager import PanelManager


class WorkspaceDockTabBar(QtWidgets.QTabBar):
    _MIME_TYPE = "application/x-workspace-panel-id"
    panelDropRequested = QtCore.Signal(str, str)

    def __init__(self, owner: "WorkspaceLayout", dock_target: str, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self._owner = owner
        self._dock_target = str(dock_target or "left")
        self._drag_start_pos: Optional[QtCore.QPoint] = None
        self._drag_panel_id = ""
        self.setMovable(True)
        self.setUsesScrollButtons(True)
        self.setAcceptDrops(True)
        self.setElideMode(QtCore.Qt.ElideRight)
        self.setToolTip("Drag tabs to move panels between left, bottom-left and right.")

    def _panel_id_for_pos(self, pos: QtCore.QPoint) -> str:
        idx = int(self.tabAt(pos))
        if idx < 0:
            return ""
        tabs = self.parentWidget()
        if not isinstance(tabs, QtWidgets.QTabWidget):
            return ""
        panel = tabs.widget(idx)
        if panel is None:
            return ""
        return str(self._owner._panel_id_for_widget(panel))

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.LeftButton:
            self._drag_start_pos = event.position().toPoint()
            self._drag_panel_id = self._panel_id_for_pos(self._drag_start_pos)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        if not (event.buttons() & QtCore.Qt.LeftButton):
            super().mouseMoveEvent(event)
            return
        if self._drag_start_pos is None or not self._drag_panel_id:
            super().mouseMoveEvent(event)
            return
        move_delta = event.position().toPoint() - self._drag_start_pos
        if move_delta.manhattanLength() < QtWidgets.QApplication.startDragDistance():
            super().mouseMoveEvent(event)
            return

        drag = QtGui.QDrag(self)
        mime = QtCore.QMimeData()
        mime.setData(self._MIME_TYPE, self._drag_panel_id.encode("utf-8"))
        drag.setMimeData(mime)

        idx = int(self.currentIndex())
        if idx >= 0:
            rect = self.tabRect(idx)
            if rect.isValid():
                drag.setPixmap(self.grab(rect))
                drag.setHotSpot(rect.center() - rect.topLeft())
        drag.exec(QtCore.Qt.MoveAction)
        fallback_target = self._owner._dock_target_for_global_pos(QtGui.QCursor.pos())
        if fallback_target:
            self.panelDropRequested.emit(self._drag_panel_id, fallback_target)
        self._drag_start_pos = None
        self._drag_panel_id = ""

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        self._drag_start_pos = None
        self._drag_panel_id = ""
        super().mouseReleaseEvent(event)

    def dragEnterEvent(self, event: QtGui.QDragEnterEvent) -> None:
        mime = event.mimeData()
        if mime is not None and mime.hasFormat(self._MIME_TYPE):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QtGui.QDragMoveEvent) -> None:
        mime = event.mimeData()
        if mime is not None and mime.hasFormat(self._MIME_TYPE):
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event: QtGui.QDropEvent) -> None:
        mime = event.mimeData()
        if mime is None or not mime.hasFormat(self._MIME_TYPE):
            super().dropEvent(event)
            return
        panel_id = bytes(mime.data(self._MIME_TYPE)).decode("utf-8", errors="ignore").strip()
        if panel_id:
            self.panelDropRequested.emit(panel_id, self._dock_target)
            event.acceptProposedAction()
            return
        super().dropEvent(event)


class WorkspaceLayout(QtWidgets.QWidget):
    panelStateChanged = QtCore.Signal(dict)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self.setObjectName("WorkspaceLayout")
        self._panel_widgets: Dict[str, QtWidgets.QWidget] = {}
        self._panel_titles: Dict[str, str] = {}
        self._panel_buttons: Dict[str, QtWidgets.QToolButton] = {}
        self._left_side_by_side_enabled = False
        self._left_side_by_side_slots: Dict[str, str] = {}
        self._left_vertical_sizes: list[int] = []
        self._left_side_by_side_sizes: list[int] = []
        self.panel_manager = PanelManager(self)
        self._panel_parking = QtWidgets.QWidget(self)
        self._panel_parking.hide()

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal, self)
        self.splitter.setObjectName("WorkspaceSplitter")
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(11)
        self.splitter.splitterMoved.connect(self._on_splitter_moved)

        self.left_dock_wrap = QtWidgets.QWidget(self.splitter)
        left_layout = QtWidgets.QVBoxLayout(self.left_dock_wrap)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        self.left_vertical_splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical, self.left_dock_wrap)
        self.left_vertical_splitter.setObjectName("WorkspaceLeftVerticalSplitter")
        self.left_vertical_splitter.setChildrenCollapsible(False)
        self.left_vertical_splitter.setHandleWidth(9)
        self.left_vertical_splitter.splitterMoved.connect(self._on_left_vertical_splitter_moved)

        self.left_top_stack = QtWidgets.QStackedWidget(self.left_vertical_splitter)
        self.left_dock = QtWidgets.QTabWidget(self.left_top_stack)
        self.left_dock.setObjectName("WorkspaceLeftDock")
        self.left_top_stack.addWidget(self.left_dock)

        self.left_side_by_side = QtWidgets.QWidget(self.left_top_stack)
        self.left_side_by_side.setObjectName("WorkspaceLeftSideBySide")
        left_side_by_side_layout = QtWidgets.QHBoxLayout(self.left_side_by_side)
        left_side_by_side_layout.setContentsMargins(0, 0, 0, 0)
        left_side_by_side_layout.setSpacing(8)
        self.left_side_by_side_splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal, self.left_side_by_side)
        self.left_side_by_side_splitter.setObjectName("WorkspaceLeftSideBySideSplitter")
        self.left_side_by_side_splitter.setChildrenCollapsible(False)
        self.left_side_by_side_splitter.setHandleWidth(9)
        self.left_side_by_side_splitter.splitterMoved.connect(self._on_left_side_by_side_splitter_moved)
        self.left_tree_dock = QtWidgets.QTabWidget(self.left_side_by_side_splitter)
        self.left_tree_dock.setObjectName("WorkspaceLeftTreeDock")
        self.left_search_dock = QtWidgets.QTabWidget(self.left_side_by_side_splitter)
        self.left_search_dock.setObjectName("WorkspaceLeftSearchDock")
        self.left_find_dock = QtWidgets.QTabWidget(self.left_side_by_side_splitter)
        self.left_find_dock.setObjectName("WorkspaceLeftFindDock")
        self._configure_dock_tabs(self.left_tree_dock, "left_tree")
        self._configure_dock_tabs(self.left_search_dock, "left_search")
        self._configure_dock_tabs(self.left_find_dock, "left_find")
        for dock in (self.left_tree_dock, self.left_search_dock, self.left_find_dock):
            dock.setVisible(False)
            dock.setMinimumWidth(150)
        self.left_side_by_side_splitter.setStretchFactor(0, 1)
        self.left_side_by_side_splitter.setStretchFactor(1, 1)
        self.left_side_by_side_splitter.setStretchFactor(2, 1)
        left_side_by_side_layout.addWidget(self.left_side_by_side_splitter, 1)
        self.left_top_stack.addWidget(self.left_side_by_side)

        self.left_bottom_dock = QtWidgets.QTabWidget(self.left_vertical_splitter)
        self.left_bottom_dock.setObjectName("WorkspaceLeftBottomDock")
        self._configure_dock_tabs(self.left_bottom_dock, "left_bottom")
        self.left_bottom_dock.setVisible(False)

        left_layout.addWidget(self.left_vertical_splitter, 1)

        self.center_wrap = QtWidgets.QWidget(self.splitter)
        center_layout = QtWidgets.QVBoxLayout(self.center_wrap)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)
        self._center_layout = center_layout

        self.right_dock_wrap = QtWidgets.QWidget(self.splitter)
        right_layout = QtWidgets.QVBoxLayout(self.right_dock_wrap)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        self.right_dock = QtWidgets.QTabWidget(self.right_dock_wrap)
        self.right_dock.setObjectName("WorkspaceRightDock")
        self._configure_dock_tabs(self.right_dock, "right")
        right_layout.addWidget(self.right_dock, 1)

        self.left_dock_wrap.setMinimumWidth(220)
        self.right_dock_wrap.setMinimumWidth(240)
        self.center_wrap.setMinimumWidth(420)
        self._configure_dock_tabs(self.left_dock, "left")

        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setStretchFactor(2, 0)
        root.addWidget(self.splitter, 1)

        self.panel_bar = QtWidgets.QWidget(self)
        self.panel_bar.setObjectName("WorkspacePanelBar")
        panel_bar_layout = QtWidgets.QHBoxLayout(self.panel_bar)
        panel_bar_layout.setContentsMargins(6, 6, 6, 6)
        panel_bar_layout.setSpacing(6)
        panel_bar_layout.addStretch(1)
        self._panel_bar_layout = panel_bar_layout
        root.addWidget(self.panel_bar, 0)

        self._apply_dock_visibility()

    def _configure_dock_tabs(self, tabs: QtWidgets.QTabWidget, dock_target: str) -> None:
        tabs.setMovable(True)
        tabs.setTabBarAutoHide(False)
        tabs.setDocumentMode(True)
        bar = WorkspaceDockTabBar(self, dock_target, tabs)
        tabs.setTabBar(bar)
        bar.panelDropRequested.connect(self._on_tab_drop_requested)
        bar = tabs.tabBar()
        if bar is None:
            return
        bar.setMovable(True)
        bar.setUsesScrollButtons(True)
        bar.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        bar.customContextMenuRequested.connect(
            lambda pos, t=tabs: self._show_tab_context_menu(t, pos)
        )

    def _panel_id_for_widget(self, panel: QtWidgets.QWidget) -> str:
        for panel_id, widget in self._panel_widgets.items():
            if widget is panel:
                return str(panel_id)
        return ""

    def _on_tab_drop_requested(self, panel_id: str, dock_target: str) -> None:
        pid = str(panel_id or "").strip()
        if not pid or not self.panel_manager.has_panel(pid):
            return
        target = str(dock_target or "").strip().lower()
        if target == "right":
            self.set_panel_dock(pid, "right")
        elif target == "left_bottom":
            self.set_panel_dock(pid, "left_bottom")
        else:
            if self.left_side_by_side_enabled():
                slot = self._slot_for_dock_target(target)
                if slot:
                    self._left_side_by_side_slots[pid] = slot
            self.set_panel_dock(pid, "left")
        self.show_panel(pid)

    @staticmethod
    def _slot_for_dock_target(target: str) -> str:
        value = str(target or "").strip().lower()
        if value in {"left_search", "search"}:
            return "search"
        if value in {"left_find", "find"}:
            return "find"
        return "tree"

    def _dock_target_for_global_pos(self, global_pos: QtCore.QPoint) -> str:
        right_rect = self._global_rect_for_widget(self.right_dock_wrap)
        if right_rect.contains(global_pos):
            return "right"

        left_rect = self._global_rect_for_widget(self.left_dock_wrap)
        if left_rect.contains(global_pos):
            local_left = self.left_dock_wrap.mapFromGlobal(global_pos)
            if self._should_drop_to_left_bottom(local_left):
                return "left_bottom"
            if self.left_side_by_side_enabled():
                side_target = self._side_by_side_target_for_global_pos(global_pos)
                if side_target:
                    return side_target
            return "left"

        workspace_rect = self._global_rect_for_widget(self)
        if not workspace_rect.contains(global_pos):
            return ""
        workspace_local = self.mapFromGlobal(global_pos)
        mid_x = self.width() // 2
        if workspace_local.x() >= mid_x + 120:
            return "right"
        if workspace_local.x() <= mid_x - 120:
            if self._should_drop_to_left_bottom(self.left_dock_wrap.mapFromGlobal(global_pos)):
                return "left_bottom"
            if self.left_side_by_side_enabled():
                side_target = self._side_by_side_target_for_global_pos(global_pos)
                if side_target:
                    return side_target
            return "left"
        return ""

    def _side_by_side_target_for_global_pos(self, global_pos: QtCore.QPoint) -> str:
        dock_targets = (
            (self.left_tree_dock, "left_tree"),
            (self.left_search_dock, "left_search"),
            (self.left_find_dock, "left_find"),
        )
        visible_targets = []
        for dock_widget, target in dock_targets:
            if not dock_widget.isVisible():
                continue
            rect = self._global_rect_for_widget(dock_widget)
            if rect.contains(global_pos):
                return target
            visible_targets.append((dock_widget, target, rect))
        if not visible_targets:
            return "left_tree"
        point_x = int(global_pos.x())
        best_target = "left_tree"
        best_distance = None
        for _dock_widget, target, rect in visible_targets:
            center_x = int(rect.center().x())
            distance = abs(point_x - center_x)
            if best_distance is None or distance < best_distance:
                best_distance = distance
                best_target = target
        return best_target

    def _should_drop_to_left_bottom(self, local_pos: QtCore.QPoint) -> bool:
        if self.left_dock_wrap.height() <= 0:
            return False
        splitter_sizes = self.left_vertical_splitter.sizes()
        bottom_height = int(splitter_sizes[1]) if len(splitter_sizes) >= 2 else 0
        if bottom_height <= 4:
            threshold = int(self.left_dock_wrap.height() * 0.62)
        else:
            top_height = int(splitter_sizes[0]) if len(splitter_sizes) >= 1 else int(self.left_dock_wrap.height() * 0.55)
            threshold = min(self.left_dock_wrap.height() - 1, top_height + 24)
        return int(local_pos.y()) >= max(0, threshold)

    @staticmethod
    def _global_rect_for_widget(widget: Optional[QtWidgets.QWidget]) -> QtCore.QRect:
        if widget is None or not widget.isVisible():
            return QtCore.QRect()
        top_left = widget.mapToGlobal(QtCore.QPoint(0, 0))
        return QtCore.QRect(top_left, widget.size())

    def _show_tab_context_menu(self, tabs: QtWidgets.QTabWidget, pos: QtCore.QPoint) -> None:
        bar = tabs.tabBar()
        if bar is None:
            return
        idx = int(bar.tabAt(pos))
        if idx < 0:
            return
        panel = tabs.widget(idx)
        if panel is None:
            return
        panel_id = self._panel_id_for_widget(panel)
        if not panel_id:
            return
        state = self.panel_manager.get_panel_state(panel_id)
        if state is None:
            return

        menu = QtWidgets.QMenu(self)
        action_left_top = menu.addAction("Dock left (top)")
        action_left_bottom = menu.addAction("Dock left (bottom)")
        action_right = menu.addAction("Dock right")
        action_close = menu.addAction("Close panel")

        action_left_top.setEnabled(state.dock != "left")
        action_left_bottom.setEnabled(state.dock != "left_bottom")
        action_right.setEnabled(state.dock != "right")
        action_close.setEnabled(bool(state.open))

        chosen = menu.exec(bar.mapToGlobal(pos))
        if chosen is action_left_top:
            self.set_panel_dock(panel_id, "left")
        elif chosen is action_left_bottom:
            self.set_panel_dock(panel_id, "left_bottom")
        elif chosen is action_right:
            self.set_panel_dock(panel_id, "right")
        elif chosen is action_close:
            self.set_panel_open(panel_id, False)

    def set_center_widget(self, widget: QtWidgets.QWidget) -> None:
        while self._center_layout.count():
            item = self._center_layout.takeAt(0)
            existing = item.widget()
            if existing is not None:
                existing.setParent(None)
        self._center_layout.addWidget(widget, 1)

    def set_left_side_by_side(self, enabled: bool, panel_slots: Optional[Dict[str, str]] = None) -> None:
        self._left_side_by_side_enabled = bool(enabled)
        if panel_slots is not None:
            self._left_side_by_side_slots = {
                str(panel_id): self._normalize_left_slot(slot)
                for panel_id, slot in dict(panel_slots or {}).items()
                if str(panel_id).strip()
            }
        elif not self._left_side_by_side_enabled:
            self._left_side_by_side_slots = {}
        for pid in list(self._panel_widgets.keys()):
            self._attach_or_detach_panel(pid)
        self._emit_panel_state_changed()

    def left_side_by_side_enabled(self) -> bool:
        return bool(self._left_side_by_side_enabled and self._left_side_by_side_slots)

    def register_panel(
        self,
        panel_id: str,
        title: str,
        widget: QtWidgets.QWidget,
        *,
        dock: str = "left",
        open: bool = True,
        button_text: str = "",
        pin_bottom: bool = False,
    ) -> None:
        pid = str(panel_id)
        self._panel_widgets[pid] = widget
        self._panel_titles[pid] = str(title)
        self.panel_manager.register_panel(pid, dock=self._normalize_dock(dock), open=bool(open))

        button = QtWidgets.QToolButton(self.panel_bar)
        button.setObjectName("WorkspacePanelButton")
        button.setCheckable(True)
        button.setText(str(button_text or title[:2]).upper())
        button.setToolTip(f"{title}\nVenstreklik: toggle\nHojreklik: dock side")
        button.setChecked(bool(open))
        button.clicked.connect(lambda checked, p=pid: self.set_panel_open(p, bool(checked)))
        button.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        button.customContextMenuRequested.connect(
            lambda pos, p=pid, b=button: self._show_panel_button_menu(p, b.mapToGlobal(pos))
        )
        self._panel_buttons[pid] = button
        if pin_bottom:
            self._panel_bar_layout.addWidget(button, 0)
        else:
            self._panel_bar_layout.insertWidget(max(0, self._panel_bar_layout.count() - 1), button, 0)

        self._attach_or_detach_panel(pid)
        self._emit_panel_state_changed()

    def set_panel_open(self, panel_id: str, is_open: bool) -> None:
        pid = str(panel_id)
        if not self.panel_manager.has_panel(pid):
            return
        self.panel_manager.set_panel_open(pid, bool(is_open))
        btn = self._panel_buttons.get(pid)
        if btn is not None and btn.isChecked() != bool(is_open):
            btn.blockSignals(True)
            btn.setChecked(bool(is_open))
            btn.blockSignals(False)
        self._attach_or_detach_panel(pid)
        self._emit_panel_state_changed()

    def set_panel_dock(self, panel_id: str, dock: str) -> None:
        pid = str(panel_id)
        if not self.panel_manager.has_panel(pid):
            return
        self.panel_manager.set_panel_dock(pid, self._normalize_dock(dock))
        self._attach_or_detach_panel(pid)
        self._emit_panel_state_changed()

    def toggle_panel(self, panel_id: str) -> None:
        pid = str(panel_id)
        if not self.panel_manager.has_panel(pid):
            return
        state = self.panel_manager.get_panel_state(pid)
        if state is None:
            return
        self.set_panel_open(pid, not bool(state.open))

    def show_panel(self, panel_id: str) -> None:
        pid = str(panel_id)
        if not self.panel_manager.has_panel(pid):
            return
        self.set_panel_open(pid, True)
        state = self.panel_manager.get_panel_state(pid)
        if state is None:
            return
        dock_widget = self._dock_widget_for_panel(pid, state.dock)
        panel = self._panel_widgets.get(pid)
        if panel is None:
            return
        idx = dock_widget.indexOf(panel)
        if idx >= 0:
            dock_widget.setCurrentIndex(idx)

    def panel_state(self) -> Dict[str, Dict[str, object]]:
        return self.panel_manager.panel_state()

    def layout_state(self) -> Dict[str, object]:
        return self.panel_manager.layout_state()

    def apply_panel_state(self, state_map: Dict[str, Dict[str, object]]) -> None:
        self.apply_layout_state({"panels": dict(state_map or {})})

    def apply_layout_state(self, state_map: Dict[str, object]) -> None:
        self.panel_manager.apply_layout_state(dict(state_map or {}))
        for pid in list(self._panel_widgets.keys()):
            state = self.panel_manager.get_panel_state(pid)
            is_open = bool(state.open) if state is not None else False
            btn = self._panel_buttons.get(pid)
            if btn is not None:
                btn.blockSignals(True)
                btn.setChecked(is_open)
                btn.blockSignals(False)
            self._attach_or_detach_panel(pid)
        splitter_sizes = self.panel_manager.splitter_sizes()
        if len(splitter_sizes) == 3:
            self.splitter.setSizes([int(v) for v in splitter_sizes])
        self._emit_panel_state_changed()

    def _show_panel_button_menu(self, panel_id: str, global_pos: QtCore.QPoint) -> None:
        pid = str(panel_id)
        state = self.panel_manager.get_panel_state(pid)
        if state is None:
            return
        menu = QtWidgets.QMenu(self)
        action_open = menu.addAction("Open")
        action_close = menu.addAction("Close")
        menu.addSeparator()
        action_left_top = menu.addAction("Dock left (top)")
        action_left_bottom = menu.addAction("Dock left (bottom)")
        action_right = menu.addAction("Dock right")

        action_open.setEnabled(not state.open)
        action_close.setEnabled(state.open)
        action_left_top.setEnabled(state.dock != "left")
        action_left_bottom.setEnabled(state.dock != "left_bottom")
        action_right.setEnabled(state.dock != "right")

        chosen = menu.exec(global_pos)
        if chosen is action_open:
            self.set_panel_open(pid, True)
        elif chosen is action_close:
            self.set_panel_open(pid, False)
        elif chosen is action_left_top:
            self.set_panel_dock(pid, "left")
        elif chosen is action_left_bottom:
            self.set_panel_dock(pid, "left_bottom")
        elif chosen is action_right:
            self.set_panel_dock(pid, "right")

    def _attach_or_detach_panel(self, panel_id: str) -> None:
        pid = str(panel_id)
        panel = self._panel_widgets.get(pid)
        if panel is None:
            return
        self._remove_from_tabs(panel)
        state = self.panel_manager.get_panel_state(pid)
        if state is None or not state.open:
            panel.hide()
            panel.setParent(self._panel_parking)
            self._apply_dock_visibility()
            return
        dock_widget = self._dock_widget_for_panel(pid, state.dock)
        dock_widget.addTab(panel, self._panel_titles.get(pid, pid))
        panel.show()
        self._apply_dock_visibility()

    def _remove_from_tabs(self, panel: QtWidgets.QWidget) -> None:
        for tabs in (
            self.left_dock,
            self.left_bottom_dock,
            self.right_dock,
            self.left_tree_dock,
            self.left_search_dock,
            self.left_find_dock,
        ):
            idx = tabs.indexOf(panel)
            while idx >= 0:
                tabs.removeTab(idx)
                idx = tabs.indexOf(panel)

    def _dock_widget_for_panel(self, panel_id: str, dock: str) -> QtWidgets.QTabWidget:
        normalized = self._normalize_dock(dock)
        if normalized == "right":
            return self.right_dock
        if normalized == "left_bottom":
            return self.left_bottom_dock
        if self.left_side_by_side_enabled():
            slot = self._left_side_by_side_slots.get(str(panel_id))
            if slot == "tree":
                return self.left_tree_dock
            if slot == "search":
                return self.left_search_dock
            if slot == "find":
                return self.left_find_dock
            return self.left_tree_dock
        return self.left_dock

    @staticmethod
    def _normalize_dock(dock: str) -> str:
        value = str(dock or "").lower().strip()
        if value == "right":
            return "right"
        if value in {"left_bottom", "left-bottom", "bottom_left", "leftbottom", "bottom"}:
            return "left_bottom"
        return "left"

    @staticmethod
    def _normalize_left_slot(slot: str) -> str:
        value = str(slot or "").strip().lower()
        if value in {"tree", "search", "find"}:
            return value
        return "tree"

    def _restore_left_vertical_sizes(self) -> None:
        if len(self._left_vertical_sizes) == 2 and sum(self._left_vertical_sizes) > 0:
            self.left_vertical_splitter.setSizes([int(v) for v in self._left_vertical_sizes[:2]])
            return
        sizes = self.left_vertical_splitter.sizes()
        if len(sizes) != 2:
            return
        normalized = [max(0, int(v)) for v in sizes]
        if sum(normalized) <= 0 or min(normalized) <= 0:
            self.left_vertical_splitter.setSizes([1, 1])

    def _restore_left_side_by_side_sizes(self) -> None:
        if len(self._left_side_by_side_sizes) == 3 and sum(self._left_side_by_side_sizes) > 0:
            self.left_side_by_side_splitter.setSizes([int(v) for v in self._left_side_by_side_sizes[:3]])
            return
        sizes = self.left_side_by_side_splitter.sizes()
        if len(sizes) == 3 and sum(max(0, int(v)) for v in sizes) <= 0:
            self.left_side_by_side_splitter.setSizes([1, 1, 1])

    def _apply_dock_visibility(self) -> None:
        use_side_by_side = self.left_side_by_side_enabled()
        if use_side_by_side:
            self.left_top_stack.setCurrentWidget(self.left_side_by_side)
            slot_docks = (self.left_tree_dock, self.left_search_dock, self.left_find_dock)
            top_has_tabs = False
            for dock_widget in slot_docks:
                has_tabs = dock_widget.count() > 0
                dock_widget.setVisible(has_tabs)
                top_has_tabs = top_has_tabs or has_tabs
            self.left_dock.setVisible(False)
            if top_has_tabs:
                self._restore_left_side_by_side_sizes()
        else:
            self.left_top_stack.setCurrentWidget(self.left_dock)
            top_has_tabs = self.left_dock.count() > 0
            self.left_dock.setVisible(top_has_tabs)
            self.left_tree_dock.setVisible(False)
            self.left_search_dock.setVisible(False)
            self.left_find_dock.setVisible(False)

        bottom_has_tabs = self.left_bottom_dock.count() > 0
        self.left_bottom_dock.setVisible(bottom_has_tabs)
        if top_has_tabs and bottom_has_tabs:
            self._restore_left_vertical_sizes()
        elif top_has_tabs:
            self.left_vertical_splitter.setSizes([1, 0])
        elif bottom_has_tabs:
            self.left_vertical_splitter.setSizes([0, 1])

        left_visible = bool(top_has_tabs or bottom_has_tabs)
        right_visible = self.right_dock.count() > 0
        self.panel_bar.setVisible(bool(self._panel_buttons))
        self.left_dock_wrap.setVisible(left_visible)
        self.right_dock_wrap.setVisible(right_visible)

        wide_left = bool(use_side_by_side and top_has_tabs)
        if left_visible:
            left_min = 420 if wide_left else 220
        else:
            left_min = 0
        self.left_dock_wrap.setMinimumWidth(left_min)

        sizes = self.splitter.sizes()
        if len(sizes) == 3:
            current_left = max(0, int(sizes[0]))
            current_center = max(0, int(sizes[1]))
            current_right = max(0, int(sizes[2]))

            if left_visible:
                left = max(460 if wide_left else 240, current_left)
            else:
                left = 0
            center = max(420, current_center)
            right = max(240, current_right) if right_visible else 0
            if [left, center, right] != [current_left, current_center, current_right]:
                self.splitter.setSizes([left, center, right])
        self._enforce_center_visibility()

    def _emit_panel_state_changed(self) -> None:
        self.panel_manager.set_splitter_sizes(self.splitter.sizes())
        self.panelStateChanged.emit(self.layout_state())

    def _on_splitter_moved(self, _pos: int, _index: int) -> None:
        self._enforce_center_visibility()
        self.panel_manager.set_splitter_sizes(self.splitter.sizes())
        self.panelStateChanged.emit(self.layout_state())

    def _on_left_vertical_splitter_moved(self, _pos: int, _index: int) -> None:
        self._left_vertical_sizes = [max(0, int(v)) for v in self.left_vertical_splitter.sizes()[:2]]

    def _on_left_side_by_side_splitter_moved(self, _pos: int, _index: int) -> None:
        self._left_side_by_side_sizes = [max(0, int(v)) for v in self.left_side_by_side_splitter.sizes()[:3]]

    def _enforce_center_visibility(self) -> None:
        sizes = self.splitter.sizes()
        if len(sizes) != 3:
            return
        left_visible = self.left_dock_wrap.isVisible()
        right_visible = self.right_dock_wrap.isVisible()
        total = sum(max(0, int(v)) for v in sizes)
        if total <= 0:
            return
        center_min = max(300, int(self.center_wrap.minimumWidth() or 0))
        left = max(0, int(sizes[0])) if left_visible else 0
        center = max(0, int(sizes[1]))
        right = max(0, int(sizes[2])) if right_visible else 0
        if center >= center_min:
            return
        missing = center_min - center
        if right_visible and right > 0:
            cut = min(missing, right)
            right -= cut
            center += cut
            missing -= cut
        if missing > 0 and left_visible and left > 0:
            cut = min(missing, left)
            left -= cut
            center += cut
            missing -= cut
        if missing > 0:
            center = min(total, center + missing)
        self.splitter.blockSignals(True)
        self.splitter.setSizes([left, center, right])
        self.splitter.blockSignals(False)
