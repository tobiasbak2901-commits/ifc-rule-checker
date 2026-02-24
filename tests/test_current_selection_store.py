from pathlib import Path


def test_current_selection_store_contract_methods_exist():
    source = Path("ui/current_selection_store.py").read_text(encoding="utf-8")
    assert "class CurrentSelectionStore(QtCore.QObject):" in source
    assert "self.selectedIds: Set[str] = set()" in source
    assert "self.selectedMeta: Dict[str, Dict[str, str]] = {}" in source
    assert "self.selectedObjectTreeNodeIds: Set[str] = set()" in source
    assert "self.selectedObjectTreeNodeMeta: Dict[str, Dict[str, str]] = {}" in source
    assert "self.selected3dElementIds: Set[str] = set()" in source
    assert "def setSelection(" in source
    assert "def setObjectTreeSelection(self, nodes: Sequence[Mapping[str, object]]) -> bool:" in source
    assert "def set3dSelection(self, ids: Sequence[str]) -> bool:" in source
    assert "def toggle(" in source
    assert "def clear(self) -> bool:" in source
    assert "def getSelectionArray(self) -> List[str]:" in source
    assert "def getObjectTreeSelectionArray(self) -> List[str]:" in source
    assert "def get3dSelectionArray(self) -> List[str]:" in source
    assert "changed = QtCore.Signal(object)" in source
