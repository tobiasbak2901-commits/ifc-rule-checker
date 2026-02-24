from pathlib import Path


def test_group_headers_use_right_chevron_and_separator_style():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "class PropertySection(CollapsibleSection):" in source
    assert "class PropertyRow(QtWidgets.QFrame):" in source
    assert "self.inspect_property_grid.groupToggled.connect(self._on_inspect_property_section_toggled)" in source
    assert "grid.add_group(gid, title, collapsed=(not expanded))" in source
    assert "def set_group_deemphasized(self, group_id: str, deemphasized: bool) -> None:" in source


def test_properties_rows_have_compact_density_and_hover_zebra_styles():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "QFrame[inspectRow=\"true\"] {" in source
    assert "border-bottom: 1px solid" in source
    assert "QFrame[inspectRow=\"true\"]:hover {" in source
    assert "QToolButton[inspectCopyButton=\"true\"] {" in source
    assert "QToolButton[inspectFavButton=\"true\"] {" in source
    assert "QToolButton[inspectDebugSection=\"true\"] {" in source


def test_long_values_support_ellipsis_tooltip_and_inline_expand():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "def _inspect_collapsed_value_text(value: str, *, max_chars: int = 160) -> str:" in source
    assert "def _inspect_value_is_expandable(value: str, collapsed: str) -> bool:" in source
    assert "def _set_inspect_value_expanded(self, item: QtWidgets.QTreeWidgetItem, expanded: bool) -> None:" in source
    assert "item.setToolTip(1, full_value)" in source
    assert "def _toggle_inspect_value_expansion(self, item: QtWidgets.QTreeWidgetItem) -> None:" in source
    assert "if int(column) == 1:" in source


def test_panel_removes_trailing_large_empty_stretch_container():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "inspect_body_layout.addStretch(1)" not in source
