from pathlib import Path


def test_inspect_multi_selection_uses_compact_chip_and_mode_toggle():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "self.inspect_selection_summary_label.setObjectName(\"InspectSelectionChip\")" in source
    assert "self.inspect_selection_focus_btn.setObjectName(\"InspectSelectionAction\")" in source
    assert "self.inspect_selection_clear_btn.setObjectName(\"InspectSelectionAction\")" in source
    assert "self.inspect_multi_primary_btn = QtWidgets.QToolButton(self.inspect_selection_summary)" in source
    assert "self.inspect_multi_compare_btn = QtWidgets.QToolButton(self.inspect_selection_summary)" in source
    assert "self.inspect_multi_mode_group = QtWidgets.QButtonGroup(self.inspect_selection_summary)" in source


def test_multi_selection_compare_mode_uses_common_fields_and_multiple_values():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "self._inspect_multi_view_mode = \"compare\"" in source
    assert "def _set_multi_selection_info(self, elements: Sequence[Element]) -> None:" in source
    assert "self.element_global_id.setText(\"Multiple values\")" in source
    assert "def _refresh_inspect_property_grid_multi(self, elements: Sequence[Element]) -> None:" in source
    assert "(\"IfcType\", common_ifctype, \"inspect:multi\", \"IfcType\")" in source
    assert "(\"System/Group\", common_system, \"inspect:multi\", \"System/Group\")" in source


def test_multi_selection_summary_row_updates_chip_text_and_toggle_state():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "def _update_inspect_selection_summary_panel(self) -> None:" in source
    assert "label.setText(f\"{count} selected\")" in source
    assert "primary_btn.setChecked(mode == \"primary\")" in source
    assert "compare_btn.setChecked(mode != \"primary\")" in source
    assert "compare_multi = bool(selection_count > 1 and str(self._inspect_multi_view_mode) == \"compare\")" in source
    assert "elif multi_selected:" in source
    assert "expanded = False" in source
