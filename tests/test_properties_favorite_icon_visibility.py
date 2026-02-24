from pathlib import Path


def test_favorite_icon_toggle_is_always_visible_for_property_rows():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "self._hovered = False" in source
    assert "self._focused = False" in source
    assert "def _sync_action_visibility(self) -> None:" in source
    assert "favorite_visible = bool(can_favorite)" in source
    assert "self.favorite_btn.setVisible(bool(favorite_visible))" in source
    assert "def focusInEvent(self, event: QtGui.QFocusEvent) -> None:" in source
    assert "def focusOutEvent(self, event: QtGui.QFocusEvent) -> None:" in source


def test_favorite_action_remains_keyboard_and_context_menu_accessible():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "def contextMenuEvent(self, event: QtGui.QContextMenuEvent) -> None:" in source
    assert "action_text = \"Remove favorite\" if bool(self._favorite) else \"Add to favorites\"" in source
    assert "def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:" in source
    assert "event.key() == QtCore.Qt.Key_F" in source
