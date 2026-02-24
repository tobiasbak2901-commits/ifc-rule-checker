from pathlib import Path


def test_find_objects_panel_renders_scope_search_and_results_skeleton():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert 'self.find_objects_group = QtWidgets.QGroupBox("Find Objects")' in source
    assert 'self.find_objects_header_frame = QtWidgets.QFrame(self.find_objects_group)' in source
    assert 'self.find_objects_scope_section_title = QtWidgets.QLabel("Search scope")' in source
    assert 'self.find_objects_scope_section_title.setObjectName("FindObjectsZoneTitle")' in source
    assert 'self.find_objects_scope_combo.addItem("Everywhere", "everywhere")' in source
    assert 'self.find_objects_scope_combo.addItem("Within current selection", "currentSelection")' in source
    assert 'self.find_objects_scope_combo.addItem("Search below current selection", "belowCurrentSelection")' in source
    assert 'self.find_objects_scope_combo.addItem("Within search set", "active_search_set")' in source
    assert 'self.find_objects_scope_selection_chip = QtWidgets.QLabel("", self.find_objects_header_frame)' in source
    assert 'self.find_objects_scope_warning = QtWidgets.QLabel("No selection in Object Tree", self.find_objects_header_frame)' in source
    assert 'self.find_objects_scope_combo.view().setObjectName("FindObjectsComboPopup")' in source
    assert 'self.find_objects_scope_combo.view().setProperty("themeScope", "app")' in source
    assert 'self.find_objects_indexed_count = QtWidgets.QLabel("Indexed: 0")' in source
    assert 'self.find_objects_scope_elements_count = QtWidgets.QLabel("Scope elements: 0")' in source
    assert 'self.find_objects_search_edit = QtWidgets.QLineEdit()' in source
    assert 'self.find_objects_search_edit.setObjectName("FindObjectsSearchInput")' in source
    assert 'self.find_objects_search_edit.setPlaceholderText("Quick search (name, system, type...)")' in source
    assert "self.find_objects_search_edit.setClearButtonEnabled(True)" in source
    assert "self.find_objects_suggest_btn = QtWidgets.QToolButton()" in source
    assert 'self.find_objects_suggest_btn.setObjectName("FindObjectsSuggestBtn")' in source
    assert 'self.find_objects_suggest_btn.setText("Suggest")' in source
    assert 'self.find_objects_advanced_toggle_btn = QtWidgets.QToolButton(self.find_objects_group)' in source
    assert 'self.find_objects_advanced_toggle_btn.setText("Advanced filters")' in source
    assert "self.find_objects_advanced_toggle_btn.setCheckable(True)" in source
    assert "self.find_objects_advanced_frame = QtWidgets.QFrame(self.find_objects_group)" in source
    assert "self.find_objects_advanced_frame.setVisible(True)" in source
    assert 'self.find_objects_scope_condition_row = QtWidgets.QFrame(self.find_objects_advanced_frame)' in source
    assert 'self.find_objects_scope_condition_label = QtWidgets.QLabel("Search set", self.find_objects_scope_condition_row)' in source
    assert 'self.find_objects_scope_condition_value = QtWidgets.QLabel("", self.find_objects_scope_condition_row)' in source
    assert 'self.find_objects_scope_condition_remove_btn = QtWidgets.QToolButton(self.find_objects_scope_condition_row)' in source
    assert "self.find_objects_scope_condition_row.setVisible(False)" in source
    assert 'self.find_objects_add_condition_btn = QtWidgets.QPushButton("Add condition")' in source
    assert 'self.find_objects_add_group_btn = QtWidgets.QPushButton("Add group")' in source
    assert 'self.find_objects_add_condition_btn.setObjectName("FindObjectsInlineAction")' in source
    assert 'self.find_objects_add_group_btn.setObjectName("FindObjectsInlineAction")' in source
    assert "self.find_objects_add_condition_btn.setFlat(True)" in source
    assert "self.find_objects_add_group_btn.setFlat(True)" in source
    assert 'self.find_objects_add_condition_btn.setToolTip("Add condition")' in source
    assert 'self.find_objects_add_group_btn.setToolTip("Add nested group")' in source
    assert "frame.setObjectName(\"FindObjectsGroupBlock\")" in source
    assert "connector.setObjectName(\"FindObjectsGroupConnector\")" in source
    assert "header.setObjectName(\"FindObjectsGroupToolbar\")" in source
    assert 'logic_and_btn = QtWidgets.QToolButton(frame)' in source
    assert 'logic_or_btn = QtWidgets.QToolButton(frame)' in source
    assert 'self.find_objects_results_title = QtWidgets.QLabel("Results (0)")' in source
    assert 'self.find_objects_matches_label = QtWidgets.QLabel("Matches: 0")' in source
    assert 'self.find_objects_matches_label.setObjectName("FindObjectsMatchesCount")' in source
    assert 'self.find_objects_results_count_large = QtWidgets.QLabel("0 objects found")' in source
    assert "self.find_objects_results_table = QtWidgets.QTableView()" in source
    assert "self.find_objects_results_model = FindObjectsResultsTableModel(self.find_objects_group)" in source
    assert 'self.find_objects_empty_message = QtWidgets.QLabel("No objects match current filters", self.find_objects_empty_state)' in source
    assert 'self.find_objects_results_frame.setProperty("hasResults", False)' in source
    assert 'self.find_objects_find_disabled_hint = QtWidgets.QLabel(' in source
    assert 'self.find_objects_find_disabled_hint.setObjectName("FindObjectsFooterHint")' in source
    assert 'self.find_objects_filter_chip_wrap = QtWidgets.QWidget(self.find_objects_group)' in source
    assert "self.find_objects_filter_chip_layout = QtWidgets.QGridLayout(self.find_objects_filter_chip_wrap)" in source
    assert 'self.find_objects_find_btn = QtWidgets.QPushButton("Find all")' in source
    assert 'self.find_objects_find_btn.setObjectName("FindObjectsFindPrimary")' in source
    assert 'self.find_objects_action_footer = QtWidgets.QFrame(self.find_objects_group)' in source
    assert 'self.find_objects_action_footer.setObjectName("FindObjectsActionFooter")' in source
    assert 'self.find_objects_clear_btn = QtWidgets.QPushButton("Clear")' in source
    assert "self.find_objects_clear_btn.setVisible(True)" in source
    assert 'self.find_objects_prune_below_checkbox = QtWidgets.QCheckBox("Prune below result")' in source
    assert 'self.find_objects_elements_only_checkbox = QtWidgets.QCheckBox("Elements only")' in source
    assert 'self.find_objects_more_btn = QtWidgets.QToolButton(self.find_objects_action_footer)' in source
    assert 'self.find_objects_more_btn.setText("...")' in source
    assert 'self.find_objects_more_menu.setObjectName("FindObjectsMoreMenu")' in source
    assert 'self.find_objects_more_menu.setProperty("themeScope", "app")' in source
    assert 'self.find_objects_more_action_select_all = self.find_objects_more_menu.addAction("Select all results")' in source
    assert 'self.find_objects_select_all_btn = QtWidgets.QPushButton("Select all")' in source
    assert 'self.find_objects_isolate_btn = QtWidgets.QPushButton("Isolate")' in source
    assert 'self.find_objects_focus_btn = QtWidgets.QPushButton("Focus")' in source
    assert "self.find_objects_select_all_btn.setVisible(True)" in source
    assert "self.find_objects_isolate_btn.setVisible(True)" in source
    assert "self.find_objects_focus_btn.setVisible(True)" in source
    assert "footer_actions.addWidget(self.find_objects_select_all_btn, 0)" in source
    assert "footer_actions.addWidget(self.find_objects_isolate_btn, 0)" in source
    assert "footer_actions.addWidget(self.find_objects_focus_btn, 0)" in source
    assert 'self.find_objects_save_set_btn = QtWidgets.QPushButton("Save as Search Set...")' in source
    assert 'self.find_objects_save_set_btn.setObjectName("FindObjectsSavePrimary")' in source
    assert 'self.find_objects_save_set_btn.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DialogSaveButton))' in source
    assert 'self.find_objects_footer_frame = QtWidgets.QFrame(self.find_objects_group)' in source
    assert 'self.find_objects_footer_frame.setObjectName("FindObjectsFooter")' in source
    assert "self.find_objects_footer_frame.setVisible(True)" in source
    assert 'self.find_objects_update_set_btn = QtWidgets.QPushButton("Update selected Search Set")' in source
    assert 'self.find_objects_update_set_btn.setObjectName("FindObjectsUpdateSecondary")' in source
    assert "QPushButton#FindObjectsInlineAction {" in source
    assert "QFrame#FindObjectsGroupBlock {" in source
    assert "QLabel#FindObjectsGroupConnector {" in source


def test_find_objects_scope_changes_candidate_provider():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "self.object_index = ObjectIndex()" in source
    assert "from ui.theme import DARK_THEME, dropdown_menu_overrides, hex_to_rgb, normalize_stylesheet, rgba as theme_rgba" in source
    assert "self._find_objects_candidate_provider: Callable[[], List[str]] = lambda: []" in source
    assert "self.findObjectsStore = FindObjectsStore()" in source
    assert 'self._find_objects_debounce_mode = "search"' in source
    assert "self._find_objects_debounce_timer.setInterval(200)" in source
    assert "self._find_objects_debounce_timer.timeout.connect(self._on_find_objects_debounce_timeout)" in source
    assert "self.find_objects_advanced_toggle_btn.toggled.connect(self._on_find_objects_advanced_toggled)" in source
    assert "self.find_objects_search_edit.textChanged.connect(self._on_find_objects_search_text_changed)" in source
    assert "self.find_objects_search_edit.returnPressed.connect(self._on_find_objects_find_clicked)" in source
    assert "self.find_objects_suggest_btn.clicked.connect(self._on_find_objects_suggest_filters_clicked)" in source
    assert "self.find_objects_scope_condition_remove_btn.clicked.connect(self._on_find_objects_scope_condition_removed)" in source
    assert "self.find_objects_add_condition_btn.clicked.connect(self._on_find_objects_add_condition_clicked)" in source
    assert "self.find_objects_more_action_select_all.triggered.connect(self._on_find_objects_select_all_clicked)" in source
    assert "from ui.condition_row import ConditionRow" in source
    assert "row = ConditionRow(" in source
    assert "distinct_values_provider=self._find_objects_distinct_values_for_property" in source
    assert "def _rebuild_object_index(self) -> None:" in source
    assert 'self.find_objects_indexed_count.setText(f"Indexed: {count}")' in source
    assert "def _set_find_objects_candidate_provider(self, scope_key: str) -> None:" in source
    assert "def _build_find_objects_filter_suggestions(self) -> List[Dict[str, str]]:" in source
    assert "def _on_find_objects_suggest_filters_clicked(self) -> None:" in source
    assert 'menu.setProperty("themeScope", "app")' in source
    assert "def _apply_find_objects_suggestion(self, suggestion: Mapping[str, str]) -> None:" in source
    assert "def _remember_find_objects_condition_descriptors(self, descriptors: Sequence[Mapping[str, str]]) -> None:" in source
    assert "source=\"From selection\"" in source
    assert "source=\"Last used\"" in source
    assert '"currentselection": self._find_objects_candidates_selection' in source
    assert '"belowcurrentselection": self._find_objects_candidates_selection_below' in source
    assert '"active_search_set": self._find_objects_candidates_active_search_set' in source
    assert "self.findObjectsStore.scope = str(key)" in source
    assert "def _find_objects_scope_uses_current_selection(self) -> bool:" in source
    assert "def _find_objects_scope_uses_search_set(self) -> bool:" in source
    assert "def _find_objects_scope_has_selection(self) -> bool:" in source
    assert "def _find_objects_scope_selection_summary(self, selection_ids: Sequence[str]) -> Tuple[str, str]:" in source
    assert "def resolveScopeCandidates(self, scope: str, selectionIds: Sequence[str]) -> Set[str]:" in source
    assert "def setFindObjectsScopeSelectionNodes(self, nodes: Sequence[Mapping[str, object]], *, source: str = \"tree\") -> None:" in source
    assert "def _update_find_objects_scope_condition_row(self) -> None:" in source
    assert "def _update_find_objects_scope_selection_ui(self) -> None:" in source
    assert "def _on_find_objects_scope_changed(self, _index: int) -> None:" in source
    assert "def _on_find_objects_scope_condition_removed(self) -> None:" in source
    assert "scope_key = str(self.find_objects_scope_combo.currentData() or \"everywhere\")" in source
    assert "def _run_find_objects_live_search(self) -> None:" in source
    assert "def _schedule_find_objects_live_search(self, *, immediate: bool = False) -> None:" in source
    assert "def _schedule_find_objects_quick_preview(self) -> None:" in source
    assert "def _on_find_objects_debounce_timeout(self) -> None:" in source
    assert "def _run_find_objects_quick_preview(self) -> None:" in source
    assert "def _update_find_objects_matches_preview(self, count: Optional[int], *, invalid: bool = False) -> None:" in source
    assert "def _find_objects_active_filter_chip_texts(self) -> List[str]:" in source
    assert 'return "Add a condition or use Quick search."' in source
    assert 'return "No matches. Try changing operator, value, or scope."' in source
    assert 'more_chip = QtWidgets.QLabel(f"+{remaining} more")' in source
    assert "def _update_find_objects_find_all_state(self) -> None:" in source
    assert "def _find_objects_has_query_or_valid_filters(self) -> bool:" in source
    assert "self.find_objects_find_btn.setEnabled(enabled)" in source
    assert "scope_ready = (not self._find_objects_scope_uses_current_selection()) or self._find_objects_scope_has_selection()" in source
    assert "self.find_objects_find_disabled_hint.setVisible(False)" in source
    assert 'self.find_objects_matches_label.setText("Matches: —")' in source
    assert "def _set_find_objects_advanced_visible(self, visible: bool) -> None:" in source
    assert "def _on_find_objects_advanced_toggled(self, checked: bool) -> None:" in source
    assert "def _on_find_objects_group_logic_toggled(self, group_id: int, logic: str, checked: bool) -> None:" in source
    assert "def _find_objects_query_matches_guid(self, guid: str, query_tokens: Sequence[str], query_text: str) -> bool:" in source
    assert 'haystack = str(getattr(item, "searchableText", "") or "").strip().lower()' in source
    assert "def _find_objects_distinct_values_for_property(self, property_key: str) -> List[str]:" in source
    assert "def _update_find_objects_scope_count(self) -> None:" in source
    assert 'self.find_objects_scope_elements_count.setText(f"Scope elements: {count}")' in source
    assert 'self._refresh_find_objects_for_active_scope("belowCurrentSelection")' in source
    assert "self.find_objects_results_model.checkedGuidsChanged.connect(self._on_find_objects_results_checked_changed)" in source
    assert "def _on_find_objects_result_row_clicked(self, index: QtCore.QModelIndex) -> None:" in source
    assert "def _on_find_objects_result_row_double_clicked(self, index: QtCore.QModelIndex) -> None:" in source


def test_find_objects_suggestions_are_selection_driven_and_deterministic():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "def _find_objects_selected_keys(self, *, limit: int = 80) -> List[str]:" in source
    assert "def _update_find_objects_suggest_state(self) -> None:" in source
    assert "self.find_objects_suggest_btn.setEnabled(has_selection)" in source
    assert "self._update_find_objects_suggest_state()" in source
    assert "if not selected_keys:" in source
    assert "return []" in source
    assert "def score_by_support(selected_hits: int, global_hits: int) -> int:" in source
    assert "selected_ifc_type_counts" in source
    assert "selected_system_counts" in source
    assert "selected_name_token_counts" in source
    assert "global_ifc_type_counts" in source
    assert "global_system_counts" in source
    assert "top_ifc_type, top_ifc_hits = pick_top_value(selected_ifc_type_counts)" in source
    assert "top_system, top_system_hits = pick_top_value(selected_system_counts)" in source
    assert 'add("name", "contains"' in source
    assert '"diameter_mm",' in source
    assert '"greater_than",' in source
    assert "ordered[:6]" in source
    assert 'if not self._find_objects_selected_keys(limit=1):' in source


def test_find_objects_object_index_rebuilds_on_model_activation_and_project_reset():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "self.state.ifc_index = dict(modelPayload.elementRefs or {})" in source
    assert "self._rebuild_object_index()" in source
    assert "self.state.reset()" in source


def test_find_objects_results_and_footer_actions_wired():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "def _on_find_objects_select_all_clicked(self) -> None:" in source
    assert "def _on_find_objects_isolate_clicked(self) -> None:" in source
    assert "def _on_find_objects_focus_clicked(self) -> None:" in source
    assert "def _on_find_objects_save_as_search_set_clicked(self) -> None:" in source
    assert "def _on_find_objects_update_search_set_clicked(self) -> None:" in source
    assert "def _find_objects_result_element_ids(self, guids: Optional[Sequence[str]] = None) -> List[str]:" in source
    assert "def _find_objects_guids_from_element_ids(self, element_ids: Sequence[str]) -> List[str]:" in source
    assert "def _prompt_find_objects_search_set_details(self, *, default_name: str) -> Optional[Tuple[str, str]]:" in source
    assert 'dialog.setWindowTitle("Save as Search Set")' in source
    assert 'form.addRow("Name", name_edit)' in source
    assert 'form.addRow("Folder/group", folder_edit)' in source
    assert 'create_btn = QtWidgets.QPushButton("Create", dialog)' in source
    assert 'default_name = f"New Set ({len(element_ids)} objects)"' in source
    assert "details = self._prompt_find_objects_search_set_details(default_name=default_name)" in source
    assert "label = f\"{folder_label} / {label}\"" in source
    assert "self.find_objects_update_set_btn.setEnabled(bool(editing and has_results))" in source
    assert 'self.find_objects_update_set_btn.setToolTip("Update selected Search Set" if editing else "Select a Search Set first")' in source
    assert "self.find_objects_more_action_update_set.setEnabled(bool(editing and has_results))" in source
    assert 'self.find_objects_save_set_btn.setEnabled(has_results)' in source
    assert "self.find_objects_more_action_select_all.setEnabled(has_results)" in source
    assert 'self.find_objects_results_count_large.setText(f"{len(rows)} objects found")' in source
    assert 'self.find_objects_results_frame.setProperty("hasResults", has_results)' in source
    assert 'self.statusBar().showMessage("Search set created from Find Objects", 2600)' in source
    assert "definition = self._build_find_objects_search_set_definition()" in source
    assert "find_definition=definition" in source
    assert "selected.find_definition = dict(definition)" in source


def test_find_objects_condition_row_has_professional_builder_controls():
    source = Path("ui/condition_row.py").read_text(encoding="utf-8")
    assert "class ConditionRow(QtWidgets.QFrame):" in source
    assert "from ui.searchable_dropdown import SearchableDropdown" in source
    assert 'self.setObjectName("FindObjectsConditionRow")' in source
    assert 'self.category_combo.setObjectName("FindObjectsCategoryCombo")' in source
    assert 'self.category_combo.view().setObjectName("FindObjectsComboPopup")' in source
    assert 'self.category_combo.set_popup_titles(recent="Recent", all_items="Categories")' in source
    assert 'self.category_combo.set_search_placeholder("Search categories")' in source
    assert 'self.category_combo.set_recent_settings_key("findObjects/recent/categories")' in source
    assert 'self.property_combo.setObjectName("FindObjectsPropertyCombo")' in source
    assert 'self.property_combo.view().setObjectName("FindObjectsComboPopup")' in source
    assert 'self.property_combo.view().setProperty("themeScope", "app")' in source
    assert 'self.property_combo.set_popup_titles(recent="Recent", all_items="Properties")' in source
    assert 'self.property_combo.set_search_placeholder("Search properties")' in source
    assert 'self.property_combo.set_recent_settings_key("findObjects/recent/properties")' in source
    assert 'self.operator_combo.view().setObjectName("FindObjectsComboPopup")' in source
    assert 'self.operator_combo.view().setProperty("themeScope", "app")' in source
    assert '("equals", "equals")' in source
    assert '("in list", "in_list")' in source
    assert '("contains", "contains")' in source
    assert '("starts with", "starts_with")' in source
    assert '("ends with", "ends_with")' in source
    assert '("exists", "exists")' in source
    assert '("greater than", "greater_than")' in source
    assert '("less than", "less_than")' in source
    assert '"diameter_mm": {"category": "constraints", "kind": "number", "unit": "mm"}' in source
    assert '"length_m": {"category": "constraints", "kind": "number", "unit": "m"}' in source
    assert '"is_classified": {"category": "ifc", "kind": "boolean"}' in source
    assert '"discipline": {' in source
    assert 'self.value_choice_combo.setObjectName("FindObjectsValueChoice")' in source
    assert 'self.value_choice_combo.view().setObjectName("FindObjectsComboPopup")' in source
    assert 'self.value_choice_combo.view().setProperty("themeScope", "app")' in source
    assert "self.value_stack = QtWidgets.QStackedWidget(self)" in source
    assert 'self.value_unit_label.setObjectName("FindObjectsValueUnit")' in source
    assert 'self.settings_btn.setObjectName("FindObjectsConditionSettingsBtn")' in source
    assert 'self.settings_btn.setText("...")' in source
    assert 'self.settings_btn.setToolTip("Condition settings")' in source
    assert 'self.settings_menu.setObjectName("FindObjectsConditionSettingsMenu")' in source
    assert 'self.settings_menu.setProperty("themeScope", "app")' in source
    assert "self.settings_menu.setToolTipsVisible(True)" in source
    assert 'self.settings_match_case_action = self.settings_menu.addAction("Match case")' in source
    assert "self.settings_match_case_action.setCheckable(True)" in source
    assert "self.settings_match_case_action.setEnabled(False)" in source
    assert 'self.settings_match_case_action.setToolTip("Coming soon")' in source
    assert 'self.settings_negate_action = self.settings_menu.addAction("Negate condition (NOT)")' in source
    assert "self.settings_negate_action.setCheckable(True)" in source
    assert "self.settings_negate_action.setEnabled(False)" in source
    assert 'self.settings_negate_action.setToolTip("Coming soon")' in source
    assert 'self.remove_btn.setObjectName("FindObjectsConditionRemoveBtn")' in source
    assert 'self.remove_btn.setText("X")' in source
    assert 'if op == "in_list":' in source
    assert "self.value_input.setToolTip(\"Use comma-separated values\")" in source
    assert 'if kind == "boolean":' in source
    assert 'if kind in {"enum", "list"}:' in source
    assert 'if kind == "number":' in source
    assert "self.value_input.setValidator(self._number_validator)" in source
    assert "def category_key(self) -> str:" in source
    assert "def set_value_invalid(self, invalid: bool) -> None:" in source
    assert "def has_missing_required_value(self) -> bool:" in source
    dropdown_source = Path("ui/searchable_dropdown.py").read_text(encoding="utf-8")
    assert "class SearchableDropdown(QtWidgets.QComboBox):" in dropdown_source
    assert "QListView#SearchableDropdownList" in dropdown_source
    assert "QLineEdit#SearchableDropdownSearch" in dropdown_source
    assert "popup.setWindowFlag(QtCore.Qt.Popup, True)" in dropdown_source
    assert "self._remember_recent(value)" in dropdown_source
    assert "QtCore.QSettings(\"Ponker\", \"Resolve\")" in dropdown_source
    assert "self._popup_delegate.set_filter_text(str(search_text or \"\"))" in dropdown_source
    source_main = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "{dropdown_menu_overrides(self.THEME)}" in source_main
    assert "QToolButton#FindObjectsSuggestBtn {" in source_main
    assert "QToolButton#FindObjectsSuggestApplyBtn {" in source_main
    assert "QFrame#FindObjectsConditionsHeader {" in source_main
    assert "QToolButton#FindObjectsGroupInlineAction {" in source_main
    assert "QLabel#FindObjectsFilterChipMore {" in source_main
    assert "QFrame#FindObjectsActionFooter {" in source_main
    assert "QPushButton#FindObjectsFindPrimary:disabled {" in source_main
    dropdowns = Path("ui/theme_overrides/dropdowns.qss").read_text(encoding="utf-8")
    assert "QAbstractItemView#FindObjectsComboPopup[themeScope=\"app\"]" in dropdowns
    assert "QComboBox#FindObjectsCategoryCombo QAbstractItemView[themeScope=\"app\"]" in dropdowns
    assert "QMenu#FindObjectsSuggestMenu[themeScope=\"app\"]" in dropdowns
    assert "QMenu#FindObjectsMoreMenu[themeScope=\"app\"]" in dropdowns
