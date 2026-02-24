from pathlib import Path


def test_main_window_exposes_central_classification_api():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "def setElementClassification(self, elementId: Optional[str], payload: Mapping[str, object]) -> bool:" in source
    assert "def clearElementClassification(self, elementId: Optional[str]) -> bool:" in source
    assert "def _resolve_element_key(self, element_id: Optional[str]) -> str:" in source
    assert "def enableClassificationMode(self, *, source: str = \"aiViewsGo\", focusElementId: Optional[str] = None) -> None:" in source
    assert "def disableClassificationMode(self) -> None:" in source


def test_modal_accept_button_routes_through_accept_handler_and_api():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "_on_accept_classification_clicked(" in source
    assert "self.setElementClassification(" in source
    assert 'self.statusBar().showMessage(f"Classified as {label}.", 3000)' in source
    assert "dialog.accept()" in source


def test_modal_clear_button_routes_through_clear_handler_and_api():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "_on_clear_classification_clicked(" in source
    assert "self.clearElementClassification(" in source
    assert 'self.statusBar().showMessage("Classification cleared.", 3000)' in source


def test_classification_overrides_are_persisted_for_project():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "def _classification_overrides_settings_key(self) -> str:" in source
    assert 'return "classification/overrides_v1"' in source
    assert "def _persist_classification_overrides(self) -> None:" in source
    assert "def _load_classification_overrides_for_current_project(self) -> None:" in source
    assert "def classificationSuggestionsForElement(self, elementId: Optional[str]) -> List[Dict[str, object]]:" in source


def test_object_tree_has_manual_refresh_hook_for_immediate_ai_count_updates():
    source = Path("ui/panels/object_tree_panel.py").read_text(encoding="utf-8")
    assert "def refresh_now(self) -> None:" in source
    assert "self._last_ai_signature = None" in source
    assert "self._refresh_from_host()" in source
