from pathlib import Path


def test_workspace_layout_uses_panel_manager_and_layout_state():
    source = Path("ui/workspace_layout.py").read_text(encoding="utf-8")
    assert "from .panel_manager import PanelManager" in source
    assert "self.panel_manager = PanelManager(self)" in source
    assert "def apply_layout_state(self, state_map: Dict[str, object]) -> None:" in source
    assert "def layout_state(self) -> Dict[str, object]:" in source
    assert 'menu.addAction("Dock left (bottom)")' in source
    assert '"left_bottom"' in source


def test_base_panel_exists_with_tabs():
    source = Path("ui/panels/base_panel.py").read_text(encoding="utf-8")
    assert "class BasePanel(QtWidgets.QWidget):" in source
    assert "self.tabs = QtWidgets.QTabWidget(self)" in source
    assert "def add_tab(self, tab_id: str, label: str, widget: QtWidgets.QWidget) -> None:" in source


def test_side_panels_use_base_panel():
    object_tree = Path("ui/panels/object_tree_panel.py").read_text(encoding="utf-8")
    ai_views = Path("ui/panels/ai_views_panel.py").read_text(encoding="utf-8")
    search_sets = Path("ui/panels/search_sets_panel.py").read_text(encoding="utf-8")
    find_objects = Path("ui/panels/find_objects_panel.py").read_text(encoding="utf-8")
    clash = Path("ui/panels/clash_detection_panel.py").read_text(encoding="utf-8")
    issues = Path("ui/panels/issues_panel.py").read_text(encoding="utf-8")
    properties = Path("ui/panels/properties_panel.py").read_text(encoding="utf-8")
    ai_panel = Path("ui/panels/ponker_ai_panel.py").read_text(encoding="utf-8")
    assert "class ObjectTreePanel(BasePanel):" in object_tree
    assert "class AiViewsPanel(BasePanel):" in ai_views
    assert "class SearchSetsPanel(BasePanel):" in search_sets
    assert "class FindObjectsPanel(BasePanel):" in find_objects
    assert "class ClashDetectionPanel(BasePanel):" in clash
    assert "class IssuesPanel(BasePanel):" in issues
    assert "class PropertiesPanel(BasePanel):" in properties
    assert "class PonkerAIPanel(BasePanel):" in ai_panel


def test_main_window_persists_workspace_panel_layout_in_ui_state():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert 'return "workspace/panels_v2"' in source
    assert "self.workspace_layout.apply_layout_state(self._load_workspace_panel_state())" in source
    assert "self.state.ui_panel_layout_state = dict(payload)" in source
    assert '"objectTree": {"open": True, "dock": "left"}' in source
    assert '"properties": {"open": False, "dock": "right"}' in source
    assert '"ai": {"open": True, "dock": "right"}' in source


def test_main_window_registers_right_properties_panel():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert 'self.workspace_layout.register_panel(\n            "properties",' in source
    assert "self.properties_panel = PropertiesPanel(" in source


def test_object_tree_panel_no_longer_renders_left_properties_tab():
    source = Path("ui/panels/object_tree_panel.py").read_text(encoding="utf-8")
    assert 'self.inner_tabs.addTab(tree_tab, "Tree")' in source
    assert 'self.inner_tabs.addTab(properties_tab, "Properties")' not in source
    assert "properties_splitter = QtWidgets.QSplitter(" not in source


def test_only_one_properties_panel_is_mounted():
    main_window = Path("ui/main_window.py").read_text(encoding="utf-8")
    object_tree = Path("ui/panels/object_tree_panel.py").read_text(encoding="utf-8")
    assert main_window.count("self.properties_panel = PropertiesPanel(") == 1
    assert main_window.count('self.workspace_layout.register_panel(\n            "properties",') == 1
    assert 'self.inner_tabs.addTab(properties_tab, "Properties")' not in object_tree
    assert "def show_properties_tab(self) -> None:" not in object_tree
