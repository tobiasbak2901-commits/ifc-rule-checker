from pathlib import Path


def _source() -> str:
    return Path("ui/main_window.py").read_text(encoding="utf-8")


def test_inspect_top_area_uses_meta_controls_and_sticky_search_header_zones() -> None:
    source = _source()
    assert "self.inspect_sticky_header = QtWidgets.QFrame(inspect_tab)" in source
    assert "self.inspect_controls_row = QtWidgets.QFrame(inspect_tab)" in source
    assert "self.inspect_props_toolbar = QtWidgets.QFrame(inspect_tab)" in source
    assert "self.inspect_props_toolbar.setProperty(\"inspectStickySearchZone\", True)" in source
    assert "inspect_table_zone_layout.addWidget(self.inspect_sticky_header, 0)" in source
    assert "inspect_table_zone_layout.addWidget(self.inspect_controls_row, 0)" in source
    assert "inspect_table_zone_layout.addWidget(self.inspect_props_toolbar, 0)" in source
    assert "inspect_table_zone_layout.addWidget(self.inspect_property_grid.table_header, 0)" in source
    assert "inspect_table_zone_layout.addWidget(self.inspect_scroll, 1)" in source


def test_search_row_full_width_and_header_columns_use_shared_min_widths() -> None:
    source = _source()
    assert "inspect_toolbar_layout.setContentsMargins(" in source
    assert "PropertyRow.ROW_RIGHT_MARGIN," in source
    assert "header_layout.setColumnMinimumWidth(0, PropertyRow.CHECKBOX_COLUMN_WIDTH)" in source
    assert "header_layout.setColumnMinimumWidth(1, PropertyRow.PROPERTY_COLUMN_MIN_WIDTH)" in source
    assert "header_layout.setColumnMinimumWidth(2, PropertyRow.VALUE_COLUMN_MIN_WIDTH)" in source
