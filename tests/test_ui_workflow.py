from pathlib import Path


def test_setup_step_has_run_clash_test_primary_cta():
    source = Path("ui/panels/clash_detection_panel.py").read_text(encoding="utf-8")
    assert 'self.primary_btn = QtWidgets.QPushButton("Run clash test")' in source


def test_results_step_is_disabled_before_run():
    source = Path("ui/panels/clash_detection_panel.py").read_text(encoding="utf-8")
    assert "self.workflow_tabs.setTabEnabled(1, has_run)" in source
    assert 'self.empty_label.setText("Run a test to see results")' in source


def test_results_summary_uses_run_count_after_run():
    source = Path("ui/panels/clash_detection_panel.py").read_text(encoding="utf-8")
    assert "clashes found" in source
    assert "Last run:" in source


def test_review_clashes_moves_workflow_to_fix_step():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "def _review_clashes_from_workflow(self) -> None:" in source
    assert 'self._clash_workflow_state.activeStep = "fix"' in source
    assert "self._move_issue_selection(1)" in source


def test_ai_views_run_clash_action_wires_to_clash_setup_panel():
    source = Path("ui/panels/object_tree_panel.py").read_text(encoding="utf-8")
    assert 'if action == "runClash":' in source
    assert "def _open_clash_setup(self, *, focus_run: bool = False) -> None:" in source
    assert 'host.workspace_layout.show_panel("clash")' in source
    assert 'host._clash_workflow_state.activeStep = "setup"' in source


def test_ai_views_go_classify_enters_guided_classification_mode():
    source = Path("ui/panels/object_tree_panel.py").read_text(encoding="utf-8")
    assert "def _run_classification_flow(self) -> None:" in source
    assert "self.show_tree_tab()" in source
    assert 'host.workspace_layout.show_panel("objectTree")' in source
    assert 'host.enableClassificationMode(source="aiViewsGo", focusElementId=target_guid)' in source
    assert "Classification mode enabled." in source


def test_guided_classification_banner_actions_exist():
    source = Path("ui/panels/object_tree_panel.py").read_text(encoding="utf-8")
    assert "Classification needed" in source
    assert "def _on_class_mode_apply(self) -> None:" in source
    assert "def _on_class_mode_next(self) -> None:" in source
    assert "def _on_class_mode_exit(self) -> None:" in source


def test_clash_fix_step_has_go_to_clash_button():
    source = Path("ui/panels/clash_detection_panel.py").read_text(encoding="utf-8")
    assert 'self.go_to_clash_btn = QtWidgets.QToolButton(self)' in source
    assert 'self.go_to_clash_btn.setText("Go to clash")' in source
    assert "goToClashRequested = QtCore.Signal()" in source


def test_main_window_wires_go_to_clash_action():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "self.clash_detection_panel.goToClashRequested.connect(self._go_to_selected_clash)" in source
    assert "def _go_to_selected_clash(self) -> None:" in source
    assert "def _go_to_clash(self, issue: Issue, *, apply_section_box: Optional[bool] = None) -> bool:" in source


def test_issue_tracker_controls_exist_in_issue_details():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert 'self.issue_go_to_btn = QtWidgets.QPushButton("Go to issue"' in source
    assert 'self.issue_mark_resolved_btn = QtWidgets.QPushButton("Mark resolved"' in source
    assert 'self.issue_mark_closed_btn = QtWidgets.QPushButton("Mark closed"' in source
    assert 'self.issue_comment_edit = QtWidgets.QLineEdit' in source
    assert "def _save_issue_comment(self) -> None:" in source


def test_clash_review_keyboard_shortcuts_exist():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert 'self.shortcut_next_clash = QShortcut(QKeySequence("N"), self)' in source
    assert 'self.shortcut_prev_clash = QShortcut(QKeySequence("P"), self)' in source
    assert 'self.shortcut_resolve_clash = QShortcut(QKeySequence("R"), self)' in source
    assert 'self.shortcut_ignore_clash = QShortcut(QKeySequence("A"), self)' in source
    assert 'self.shortcut_focus = QShortcut(QKeySequence("F"), self)' in source
    assert "def _next_clash_shortcut(self) -> None:" in source
    assert "def _previous_clash_shortcut(self) -> None:" in source
    assert "def _resolve_clash_shortcut(self) -> None:" in source
    assert "def _ignore_clash_shortcut(self) -> None:" in source
    assert "def _frame_selection_shortcut(self) -> None:" in source


def test_group_batch_actions_exist_for_clash_review():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert 'self.issue_mark_group_resolved_btn = QtWidgets.QPushButton("Resolve all in group"' in source
    assert 'self.issue_mark_group_closed_btn = QtWidgets.QPushButton("Ignore all in group"' in source
    assert "def _mark_current_group_resolved(self) -> None:" in source
    assert "def _mark_current_group_closed(self) -> None:" in source


def test_review_progress_indicator_is_rendered():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "reviewed_count" in source
    assert "reviewed ·" in source
