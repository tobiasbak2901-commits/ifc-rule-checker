from pathlib import Path


def test_project_state_exposes_selection_store_alias():
    source = Path("project_state.py").read_text(encoding="utf-8")
    assert "def selectedElementKeys(self) -> List[str]:" in source
    assert "@selectedElementKeys.setter" in source
    assert "def selectedIds(self) -> List[str]:" in source
    assert "@selectedIds.setter" in source
    assert "def primarySelectedId(self) -> Optional[str]:" in source
    assert "@primarySelectedId.setter" in source


def test_main_window_selection_contract_writes_selection_store_alias():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "self.state.selectedIds = list(normalized)" in source
    assert "self.currentSelectionStore.setSelection(" in source
    assert "self.currentSelectionStore.set3dSelection(list(normalized))" in source
    assert "def _apply_selection_contract(" in source


def test_tree_selection_change_can_clear_selection_store():
    source = Path("ui/panels/object_tree_panel.py").read_text(encoding="utf-8")
    assert "def _on_by_file_selection_changed(self) -> None:" in source
    assert 'host.setFindObjectsScopeSelectionNodes(payload, source="tree")' in source
    assert 'store = getattr(host, "currentSelectionStore", None)' in source
    assert '"type": scope_type' in source
    assert '"descendantElementIds": list(descendant_element_ids)' in source
    assert "self._select_guids(guids)" in source
    assert "host._apply_selection_contract(" in source
    assert "source=\"tree\"" in source


def test_find_objects_scope_nodes_sync_into_global_selection_store():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "def setFindObjectsScopeSelectionNodes(self, nodes: Sequence[Mapping[str, object]], *, source: str = \"tree\") -> None:" in source
    assert "self.currentSelectionStore.setObjectTreeSelection(store_rows)" in source
