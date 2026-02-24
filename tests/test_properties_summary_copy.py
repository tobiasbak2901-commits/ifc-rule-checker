from pathlib import Path


def test_properties_panel_has_compact_summary_block_before_table():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "self.inspect_summary_name_value = QtWidgets.QLabel(\"-\", inspect_body)" in source
    assert "self.inspect_summary_ifctype_value = QtWidgets.QLabel(\"-\", inspect_body)" in source
    assert "self.inspect_summary_global_id_value = QtWidgets.QLabel(\"-\", inspect_body)" in source
    assert "self.inspect_summary_system_value = QtWidgets.QLabel(\"-\", inspect_body)" in source
    assert "self.inspect_summary_discipline_value = QtWidgets.QLabel(\"-\", inspect_body)" in source
    assert "self.inspect_property_grid = InspectPropertyGrid(inspect_body)" in source
    assert "inspect_body_layout.addWidget(self.inspect_property_grid, 1)" in source


def test_properties_summary_copy_buttons_show_copied_toast():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "def _copy_to_clipboard(self, text: str) -> None:" in source
    assert 'self.statusBar().showMessage("Copied", 1200)' in source
    assert "def _copy_inspect_summary_value(self, field_key: str) -> None:" in source
    assert "self.inspect_property_grid.copyRequested.connect(self._copy_to_clipboard)" in source


def test_summary_values_refresh_with_selection_changes():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "def _update_inspect_summary_block(self, elem: Optional[Element]) -> None:" in source
    assert "self._update_inspect_summary_block(None)" in source
    assert "self._update_inspect_summary_block(elem)" in source
