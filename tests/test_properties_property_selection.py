from pathlib import Path


def test_inspect_property_grid_has_selection_header_and_actions():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "self.selection_actions = QtWidgets.QFrame(self)" in source
    assert 'self.clear_selected_btn.setText("Clear selected")' in source
    assert 'self.copy_selected_btn.setText("Copy selected")' in source
    assert "self.table_header = QtWidgets.QFrame(self)" in source
    assert 'self.select_all_cb = QtWidgets.QCheckBox(self.table_header)' in source
    assert 'self.property_header_label = QtWidgets.QLabel("Property", self.table_header)' in source
    assert 'self.value_header_label = QtWidgets.QLabel("Value", self.table_header)' in source


def test_property_row_supports_checkbox_space_and_shift_range_selection():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "selectionClicked = QtCore.Signal(object, bool, bool)" in source
    assert "navigateRequested = QtCore.Signal(object, int)" in source
    assert 'self.select_cb = QtWidgets.QCheckBox(self)' in source
    assert 'self.select_cb.setObjectName("InspectPropertySelect")' in source
    assert 'self.select_cb.setProperty("data-no-row-toggle", True)' in source
    assert 'self.copy_btn.setProperty("data-no-row-toggle", True)' in source
    assert 'self.favorite_btn.setProperty("data-no-row-toggle", True)' in source
    assert 'self.setProperty("selected", bool(selected and selectable and selection_key))' in source
    assert 'self.setProperty("role", "row")' in source
    assert "self.select_cb.toggled.connect(self._on_checkbox_toggled)" in source
    assert 'QFrame[inspectRow="true"][selected="true"] {' in source
    assert 'QFrame[inspectRow="true"][selected="true"]:hover {' in source
    assert "def _is_no_row_toggle_widget(self, widget: Optional[QtWidgets.QWidget]) -> bool:" in source
    assert "def _toggle_row_selection_from_input(self, *, shift_pressed: bool) -> None:" in source
    assert "def _handle_row_primary_click(" in source
    assert "def _handle_row_double_click(self, *, row_pos: QtCore.QPoint) -> bool:" in source
    assert "def _is_detail_caret_hit(self, row_pos: QtCore.QPoint) -> bool:" in source
    assert "if self._is_no_row_toggle_widget(target):" in source
    assert "if self._handle_row_primary_click(row_pos=pos, modifiers=event.modifiers()):" in source
    assert "if self._handle_row_double_click(row_pos=pos):" in source
    assert "def eventFilter(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:" in source
    assert "if watched in (self.label_w, self.value_cell, self.value_w, self.actions_wrap):" in source
    assert "if self.is_selectable():" in source
    assert "cursor = QtCore.Qt.ArrowCursor" in source
    assert "self.setCursor(cursor)" in source
    assert "row_surface.setCursor(cursor)" in source
    assert "if event.key() in (QtCore.Qt.Key_Up, QtCore.Qt.Key_Down):" in source
    assert "self.navigateRequested.emit(self, int(delta))" in source
    assert "if self.is_selectable() and event.key() in (QtCore.Qt.Key_Space, QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):" in source
    assert "shift_pressed = bool(modifiers & QtCore.Qt.ShiftModifier)" in source
    assert "def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent) -> None:" in source


def test_main_window_stores_property_selection_per_selection_context_and_copy_rows():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "self._inspect_property_selected_keys_by_context: Dict[str, Set[str]] = {}" in source
    assert "def _current_inspect_selection_context_key(self) -> str:" in source
    assert 'return f"single:{normalized[0]}"' in source
    assert 'return f"multi:{\'|\'.join(unique_sorted)}"' in source
    assert "def _inspect_selected_property_keys_for_context(self, *, create: bool = True) -> Set[str]:" in source
    assert "def _clear_selected_inspect_properties(self) -> None:" in source
    assert "def _copy_selected_inspect_properties(self) -> None:" in source
    assert 'if multi_selected and copy_value == "Multiple values":' in source
    assert 'copy_value = "(varies)"' in source


def test_inspect_selection_signals_are_wired_between_grid_and_main_window():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "self.inspect_property_grid.propertySelectionChanged.connect(self._on_inspect_property_selection_changed)" in source
    assert "self.inspect_property_grid.clearSelectionRequested.connect(self._clear_selected_inspect_properties)" in source
    assert "self.inspect_property_grid.copySelectionRequested.connect(self._copy_selected_inspect_properties)" in source
    assert "row_widget.navigateRequested.connect(self._on_row_navigation_requested)" in source
    assert "detail_widget.navigateRequested.connect(self._on_row_navigation_requested)" in source
    assert "def _on_row_navigation_requested(self, row: object, delta: int) -> None:" in source
