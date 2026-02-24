from pathlib import Path


def test_ai_details_uses_structured_candidate_and_rule_rows():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "def _build_ai_candidate_rows(self, elem: Element) -> List[Dict[str, object]]:" in source
    assert "self._detail_row(\"Rule\", rule_summary" in source
    assert "self._detail_row(\"Evidence\", evidence_summary" in source
    assert "def _build_active_rule_rows(self, elem: Element) -> List[Dict[str, object]]:" in source
    assert "def _parse_active_rule_row(self, line: str, *, index: int) -> Dict[str, object]:" in source
    assert "ai_rows.extend(self._build_ai_candidate_rows(elem))" in source
    assert "constraint_rows.extend(self._build_active_rule_rows(elem))" in source


def test_property_row_supports_collapsible_detail_subrows():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "detailsToggled = QtCore.Signal(bool)" in source
    assert "def has_detail_rows(self) -> bool:" in source
    assert "def set_details_expanded(self, expanded: bool) -> None:" in source
    assert "if self.has_detail_rows():" in source
    assert "self.detailsToggled.emit(bool(self._details_expanded))" in source
    assert "QFrame[inspectRow=\"true\"][inspectSubRow=\"true\"] {" in source
