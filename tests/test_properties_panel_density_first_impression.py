from pathlib import Path


def _source() -> str:
    return Path("ui/main_window.py").read_text(encoding="utf-8")


def test_inspect_density_spacing_is_compact_for_first_impression() -> None:
    source = _source()
    assert "inspect_toolbar_layout.setContentsMargins(" in source
    assert "header_layout.setContentsMargins(PropertyRow.ROW_LEFT_MARGIN, 3, PropertyRow.ROW_RIGHT_MARGIN, 3)" in source
    assert "header_layout.setColumnMinimumWidth(0, PropertyRow.CHECKBOX_COLUMN_WIDTH)" in source
    assert "self.selection_actions.setVisible(state)" in source


def test_group_expansion_defaults_use_saved_state_then_context_rules() -> None:
    source = _source()
    assert "def _ensure_item_expanded_for_new_selection_context(self) -> None:" in source
    assert "expanded_state[\"item\"] = True" in source
    assert "self._ensure_item_expanded_for_new_selection_context()" in source
    assert "has_saved_state = gid in self._inspect_properties_group_expanded" in source
    assert "if has_saved_state:" in source
    assert "elif multi_selected:" in source
    assert "expanded = bool(first_visible_group_id is None)" in source


def test_no_helper_hint_row_is_rendered_in_inspect_list() -> None:
    source = _source()
    assert 'self.collapsed_hint = QtWidgets.QLabel("Click a group to expand", self)' not in source
    assert "def _refresh_collapsed_hint_visibility(self) -> None:" in source
    assert "def set_empty_state(self, visible: bool, message: str = \"No properties found for current filters.\") -> None:" in source


def test_property_header_and_rows_use_shared_three_column_alignment() -> None:
    source = _source()
    assert "CHECKBOX_COLUMN_WIDTH = 36" in source
    assert "layout.setColumnMinimumWidth(0, self.CHECKBOX_COLUMN_WIDTH)" in source
    assert "layout.setColumnMinimumWidth(1, self.PROPERTY_COLUMN_MIN_WIDTH)" in source
    assert "layout.setColumnMinimumWidth(2, self.VALUE_COLUMN_MIN_WIDTH)" in source
    assert "self.value_cell = QtWidgets.QWidget(self)" in source
    assert "layout.addWidget(self.value_cell, 0, 2, 1, 1)" in source


def test_group_rerender_detaches_old_widgets_to_prevent_ghost_overlap() -> None:
    source = _source()
    assert "widget.setParent(None)" in source
    assert "widget.setVisible(False)" in source
    assert "Root cause fix:" in source


def test_properties_groups_hide_empty_and_use_clean_empty_state_message() -> None:
    source = _source()
    assert "if self._is_empty_property_value(str(value_text or \"\")) and not cleaned_detail_rows:" in source
    assert "grid.set_empty_state(True, \"No properties found for current filters.\")" not in source
    assert "grid.add_group(\"empty\", \"Properties\", collapsed=False)" not in source
