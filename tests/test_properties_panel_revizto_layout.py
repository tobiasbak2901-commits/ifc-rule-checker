from pathlib import Path


def test_properties_panel_uses_sticky_toolbar_and_table_like_tree():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert 'self._inspect_sticky_header_height = 60' in source
    assert 'self.inspect_sticky_secondary = QtWidgets.QLabel("IfcType · System/Group", self.inspect_sticky_header)' in source
    assert 'self.inspect_sticky_secondary.setObjectName("InspectStickySecondary")' in source
    assert 'self.inspect_sticky_gid_chip = QtWidgets.QFrame(self.inspect_sticky_header)' in source
    assert 'sticky_gid_title = QtWidgets.QLabel("GlobalId", self.inspect_sticky_gid_chip)' in source
    assert 'self.inspect_sticky_copy_btn.setText("")' in source
    assert 'self.inspect_sticky_copy_btn.setToolTip("Copy GlobalId")' in source
    assert "self.inspect_sticky_copy_btn.clicked.connect(self._copy_inspect_sticky_global_id)" in source
    assert 'self.inspect_properties_search = QtWidgets.QLineEdit(self.inspect_props_toolbar)' in source
    assert 'self.inspect_favorite_preset_combo = QtWidgets.QComboBox(self.inspect_meta_controls_wrap)' in source
    assert 'self.inspect_settings_menu_btn = QtWidgets.QToolButton(self.inspect_meta_controls_wrap)' in source
    assert 'self.inspect_properties_favorites_only = QtWidgets.QCheckBox("Favorites only", self.inspect_meta_controls_wrap)' in source
    assert 'self.inspect_selection_summary = QtWidgets.QFrame(self.inspect_props_toolbar)' in source
    assert "inspect_summary_row.addWidget(self.inspect_selection_summary, 0, QtCore.Qt.AlignRight)" in source
    assert "sticky_top.addWidget(self.inspect_sticky_gid_chip, 0, QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)" in source
    assert "self.inspect_controls_row = QtWidgets.QFrame(inspect_tab)" in source
    assert "self.inspect_meta_controls_wrap.setParent(self.inspect_controls_row)" in source
    assert "self._layout_inspect_meta_controls(compact=False)" in source
    assert "self.inspect_property_grid = InspectPropertyGrid(inspect_body)" in source
    assert 'self.inspect_property_grid.setObjectName("InspectPropertyGrid")' in source
    assert "self.inspect_sticky_header.setVisible(False)" in source
    assert "self.inspect_props_toolbar.setParent(self.inspect_table_zone)" in source
    assert "self.inspect_controls_row.setParent(self.inspect_table_zone)" in source
    assert "inspect_table_zone_layout.addWidget(self.inspect_controls_row, 0)" in source
    assert "inspect_table_zone_layout.addWidget(self.inspect_props_toolbar, 0)" in source
    assert "inspect_table_zone_layout.addWidget(self.inspect_property_grid.table_header, 0)" in source
    assert "inspect_table_zone_layout.addWidget(self.inspect_scroll, 1)" in source
    assert "self.inspect_properties_tree = QtWidgets.QTreeWidget(inspect_body)" not in source


def test_properties_groups_include_revizto_style_item_other_constraints_ifc_ai():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "def _inspect_group_for_property(source_group: str, source_key: str, label: str) -> str:" in source
    assert "add_section(" in source
    assert 'add_section("favorites", "Favorites", favorites_rows, default_open=True)' in source
    assert 'add_section("item", "Item", target_group_rows.get("item", []), default_open=True)' in source
    assert 'add_section("other", "Other", target_group_rows.get("other", []), default_open=False)' in source
    assert 'add_section("constraints", "Constraints", target_group_rows.get("constraints", []), default_open=False)' in source
    assert 'add_section("ifc", "IFC", target_group_rows.get("ifc", []), default_open=False)' in source
    assert 'add_section("ai", "AI", target_group_rows.get("ai", []), default_open=False)' in source
    assert '"rule_match_debug",' in source
    assert '"search_set_debug",' in source


def test_properties_tree_supports_filtering_favorites_and_collapsible_state_memory():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "self._inspect_properties_group_expanded: Dict[str, bool] = {}" in source
    assert "self._inspect_properties_group_defaults: Dict[str, bool] = {}" in source
    assert "def _inspect_group_expanded_settings_key(self) -> str:" in source
    assert "return \"inspect/group_expanded_v1\"" in source
    assert "def _load_inspect_group_expanded_state(self) -> None:" in source
    assert "def _save_inspect_group_expanded_state(self) -> None:" in source
    assert "def _expand_all_inspect_property_groups(self) -> None:" in source
    assert "def _collapse_all_inspect_property_groups(self) -> None:" in source
    assert "def _on_inspect_properties_filter_changed(self, *_args) -> None:" in source
    assert "def _render_inspect_property_sections(self) -> None:" in source
    assert "favorites_only = bool(" in source
    assert "matches, matched_details = self._inspect_row_matches_needle(" in source
    assert "def _on_inspect_property_section_toggled(self, group_id: str, expanded: bool) -> None:" in source
    assert "title = f\"{str(group_label)} ({len(filtered_rows)})\"" in source


def test_properties_panel_has_multi_selection_summary_actions():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "self.inspect_selection_summary_label = QtWidgets.QLabel(\"0 selected\", self.inspect_selection_summary)" in source
    assert "self.inspect_selection_focus_btn = QtWidgets.QToolButton(self.inspect_selection_summary)" in source
    assert "self.inspect_selection_clear_btn = QtWidgets.QToolButton(self.inspect_selection_summary)" in source
    assert "def _on_inspect_selection_focus_clicked(self) -> None:" in source
    assert "def _on_inspect_selection_clear_clicked(self) -> None:" in source
    assert "def _update_inspect_selection_summary_panel(self) -> None:" in source
