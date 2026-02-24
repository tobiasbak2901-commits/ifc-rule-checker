from pathlib import Path


def test_find_objects_scope_labels_match_minimal_copy():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert 'self.find_objects_scope_combo.addItem("Everywhere", "everywhere")' in source
    assert 'self.find_objects_scope_combo.addItem("Within current selection", "currentSelection")' in source
    assert 'self.find_objects_scope_combo.addItem("Search below current selection", "belowCurrentSelection")' in source
    assert 'self.find_objects_scope_combo.addItem("Within search set", "active_search_set")' in source
    assert 'self.find_objects_scope_warning = QtWidgets.QLabel("No selection in Object Tree", self.find_objects_header_frame)' in source
    assert 'self.find_objects_scope_selection_chip = QtWidgets.QLabel("", self.find_objects_header_frame)' in source
    assert 'self.find_objects_selected_count = QtWidgets.QLabel("Selected: 0")' in source
    assert 'return "Within current selection"' in source
    assert 'return "Search below current selection"' in source
    assert 'return "Within search set"' in source


def test_find_objects_group_ui_is_flat_and_footer_actions_are_minimal():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert 'self.find_objects_scope_condition_label = QtWidgets.QLabel("Search set", self.find_objects_scope_condition_row)' in source
    assert 'self.find_objects_scope_condition_remove_btn.setToolTip("Switch scope to Everywhere")' in source
    assert 'self.find_objects_add_condition_btn = QtWidgets.QPushButton("Add condition")' in source
    assert 'self.find_objects_add_group_btn = QtWidgets.QPushButton("Add group")' in source
    assert "self.find_objects_add_condition_btn.setFlat(True)" in source
    assert "self.find_objects_add_group_btn.setFlat(True)" in source
    assert 'self.find_objects_more_btn.setVisible(False)' in source
    assert "QFrame#FindObjectsScopeConditionRow {" in source
    assert "QFrame#FindObjectsGroupBlock {" in source
    assert "QLabel#FindObjectsGroupConnector {" in source
    assert "QPushButton#FindObjectsInlineAction {" in source
    assert "QPushButton#FindObjectsClearSecondary {" in source
    assert "QFrame#FindObjectsGroupCard {" not in source
    assert "QLabel#FindObjectsGroupBadge {" not in source
    assert "QFrame#FindObjectsGroupDivider {" not in source
    assert "QPushButton#FindObjectsGroupAddFilter {" not in source


def test_find_objects_find_all_requires_query_or_valid_condition():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "def _find_objects_has_query_or_valid_filters(self) -> bool:" in source
    assert "if not row.is_active():" in source
    assert "if row.has_missing_required_value():" in source
    assert "return False" in source
