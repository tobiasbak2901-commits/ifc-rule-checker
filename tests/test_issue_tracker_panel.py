from pathlib import Path


def test_issue_card_component_exists():
    source = Path("ui/panels/issue_card.py").read_text(encoding="utf-8")
    assert "class IssueCard(QtWidgets.QFrame):" in source
    assert "clicked = QtCore.Signal(object)" in source
    assert 'self.status_label = QtWidgets.QLabel(f"Status:' in source
    assert 'self.priority_label = QtWidgets.QLabel(f"Priority:' in source
    assert 'self.assignee_label = QtWidgets.QLabel(f"Assigned:' in source


def test_issue_list_panel_has_required_filters():
    source = Path("ui/panels/issue_list_panel.py").read_text(encoding="utf-8")
    assert "class IssueListPanel(QtWidgets.QWidget):" in source
    assert "issueActivated = QtCore.Signal(object)" in source
    assert "self.status_combo = QtWidgets.QComboBox" in source
    assert "self.discipline_combo = QtWidgets.QComboBox" in source
    assert "self.assignee_combo = QtWidgets.QComboBox" in source
    assert "self.search_edit = QtWidgets.QLineEdit" in source


def test_main_window_wires_issue_panel_selection_to_viewer_navigation():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "self.issues_panel.issueActivated.connect(self._on_issue_panel_activated)" in source
    assert "def _on_issue_panel_activated(self, issue_obj: object) -> None:" in source
    assert "self.issues_list.setCurrentRow(row)" in source
    assert "self._apply_viewpoint(selected)" in source
    assert "self._sync_issue_tracker_panel()" in source
