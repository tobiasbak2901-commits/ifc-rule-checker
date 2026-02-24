from pathlib import Path


def test_workspace_manager_exists_with_linear_tabs():
    source = Path("ui/workspace_manager.py").read_text(encoding="utf-8")
    assert "class WorkspaceManager:" in source
    assert "class WorkspaceConfig" in source
    assert 'self._ordered_keys: Tuple[str, ...] = ("Project", "Model", "Analyze", "Issues")' in source
    assert '"Model": WorkspaceConfig(' in source
    assert '"Analyze": WorkspaceConfig(' in source
    assert '"Issues": WorkspaceConfig(' in source


def test_main_window_uses_workspace_manager_for_top_navigation():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "from ui.workspace_manager import WorkspaceManager" in source
    assert "self.workspace_manager = WorkspaceManager()" in source
    assert "for mode, label in self.workspace_manager.ordered_tabs():" in source
    assert "config = self.workspace_manager.config_for(mode)" in source
    assert "self._apply_workspace_content(config)" in source
