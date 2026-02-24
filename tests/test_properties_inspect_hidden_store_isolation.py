from pathlib import Path


def _source() -> str:
    return Path("ui/main_window.py").read_text(encoding="utf-8")


def test_inspect_hidden_backing_widgets_are_detached_from_scroll_stacking_context() -> None:
    source = _source()
    assert "self.inspect_hidden_store = QtWidgets.QWidget(self)" in source
    assert "self.inspect_hidden_store.setGeometry(-20000, -20000, 1, 1)" in source
    assert "self.inspect_hidden_store.setAttribute(QtCore.Qt.WA_DontShowOnScreen, True)" in source
    assert "self._inspect_summary_hidden_labels = (" in source
    assert "for hidden_label in self._inspect_summary_hidden_labels:" in source
    assert "hidden_label.setParent(self.inspect_hidden_store)" in source
    assert "self.element_top_candidates = QtWidgets.QPlainTextEdit(self.inspect_hidden_store)" in source
    assert "self.element_rules = QtWidgets.QPlainTextEdit(self.inspect_hidden_store)" in source
    assert "self.rule_match_debug = QtWidgets.QPlainTextEdit(self.inspect_hidden_store)" in source
    assert "self.search_set_debug = QtWidgets.QPlainTextEdit(self.inspect_hidden_store)" in source
    assert "self.ai_trace_json = QtWidgets.QPlainTextEdit(self.inspect_hidden_store)" in source
    assert "def _ensure_inspect_hidden_backing_store(self) -> None:" in source
    assert "hidden_label.setGeometry(-20000, -20000, 1, 1)" in source
    assert "self._ensure_inspect_hidden_backing_store()" in source
