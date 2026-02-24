from pathlib import Path


def _source() -> str:
    return Path("ui/main_window.py").read_text(encoding="utf-8")


def test_inspect_rows_use_table_like_grid_with_value_and_actions_cells() -> None:
    source = _source()
    assert "ACTIONS_COLUMN_WIDTH = 72" in source
    assert 'self.value_cell.setProperty("inspectValueCell", True)' in source
    assert 'self.actions_wrap.setProperty("inspectActionCell", True)' in source
    assert "actions_layout.setContentsMargins(6, 0, 10, 0)" in source
    assert "actions_layout.setSpacing(8)" in source
    assert "actions_layout.addStretch(1)" in source
    assert "layout.addWidget(self.value_cell, 0, 2, 1, 1)" in source
    assert "layout.addWidget(self.actions_wrap, 0, 3, 1, 1" in source
    assert "layout.setColumnMinimumWidth(3, self.ACTIONS_COLUMN_WIDTH)" in source


def test_inspect_header_has_matching_table_dividers() -> None:
    source = _source()
    assert 'self.value_header_label.setProperty("inspectHeaderValue", True)' in source
    assert 'self.header_actions_cell.setProperty("inspectHeaderActions", True)' in source
    assert "header_layout.addWidget(self.header_actions_cell, 0, 3, 1, 1" in source
    assert 'QLabel#InspectPropertyHeaderLabel[inspectHeaderValue="true"] {' in source
    assert 'QWidget[inspectValueCell="true"] {' in source
    assert 'QWidget[inspectActionCell="true"] {' in source
