from pathlib import Path


def test_sticky_header_uses_two_compact_rows_and_icon_copy_button():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "self._inspect_sticky_header_height = 60" in source
    assert "self._inspect_sticky_header_height_compact = 72" in source
    assert "sticky_root.addLayout(sticky_top, 0)" in source
    assert "self.inspect_controls_row = QtWidgets.QFrame(inspect_tab)" in source
    assert "self.inspect_controls_row.setObjectName(\"InspectControlsRow\")" in source
    assert "self.inspect_meta_controls_wrap.setParent(self.inspect_controls_row)" in source
    assert "inspect_layout.addWidget(self.inspect_sticky_header, 0)" not in source
    assert "self.inspect_sticky_header.setParent(self.inspect_table_zone)" in source
    assert "inspect_table_zone_layout.addWidget(self.inspect_sticky_header, 0)" in source
    assert "inspect_table_zone_layout.addWidget(self.inspect_controls_row, 0)" in source
    assert "inspect_layout.addWidget(self.inspect_props_toolbar, 0)" not in source
    assert "self.inspect_props_toolbar.setParent(self.inspect_table_zone)" in source
    assert "inspect_table_zone_layout.addWidget(self.inspect_props_toolbar, 0)" in source
    assert "sticky_root.addWidget(self.inspect_selection_summary, 0)" not in source
    assert "self.inspect_sticky_copy_btn.setText(\"\")" in source
    assert "self.inspect_sticky_copy_btn.setToolTip(\"Copy GlobalId\")" in source
    assert "self.inspect_sticky_secondary = QtWidgets.QLabel(\"IfcType · System/Group\", self.inspect_sticky_header)" in source


def test_sticky_header_chip_truncation_and_tooltips_are_supported():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "def _set_sticky_secondary_line(" in source
    assert "metrics.elidedText(full_text, QtCore.Qt.ElideRight" in source
    assert "label.setToolTip(full_text)" in source
    assert "def _set_sticky_global_id_label(" in source
    assert "QtCore.Qt.ElideMiddle" in source


def test_second_header_row_keeps_search_and_compact_favorites():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "inspect_toolbar_layout.addWidget(self.inspect_properties_search, 0)" in source
    assert "inspect_summary_row.addWidget(self.inspect_selection_summary, 0, QtCore.Qt.AlignRight)" in source
    assert "self.inspect_meta_controls_wrap = QtWidgets.QWidget(self.inspect_sticky_header)" in source
    assert "self.inspect_favorite_preset_combo = QtWidgets.QComboBox(self.inspect_meta_controls_wrap)" in source
    assert "self.inspect_settings_menu_btn = QtWidgets.QToolButton(self.inspect_meta_controls_wrap)" in source
    assert "self.inspect_properties_favorites_only = QtWidgets.QCheckBox(\"Favorites only\", self.inspect_meta_controls_wrap)" in source
    assert "def _layout_inspect_meta_controls(self, *, compact: bool) -> None:" in source
    assert "def _update_inspect_header_layout_mode(self) -> None:" in source
    assert "self.inspect_sticky_header.installEventFilter(self)" in source
    assert "self._refresh_inspect_sticky_header_for_selection()" in source
    assert "QLineEdit#InspectPropertiesSearch {" in source
    assert "min-height: 34px;" in source
    assert "QComboBox#InspectFavoritePresetCombo {" in source
    assert "QCheckBox#InspectPropertiesFavoritesOnly {" in source
