from pathlib import Path


def _source() -> str:
    return Path("ui/main_window.py").read_text(encoding="utf-8")


def test_collapsible_section_uses_compact_header_height() -> None:
    source = _source()
    assert "self._header_min_height = 30" in source
    assert "self._header_max_height = 30" in source
    assert "self.header_btn.setMinimumHeight(self._header_min_height)" in source
    assert "self.header_btn.setMaximumHeight(self._header_max_height)" in source


def test_collapsed_content_does_not_reserve_space_when_animation_is_disabled() -> None:
    source = _source()
    assert "def _apply_content_visibility(self, expanded: bool) -> None:" in source
    assert "if int(self._content_anim.duration()) <= 0:" in source
    assert "content_policy.setRetainSizeWhenHidden(False)" in source
    assert "self.content.setAttribute(QtCore.Qt.WA_DontShowOnScreen, True)" in source
    assert "self.content.setMaximumHeight(0)" in source
    assert "self.content.setVisible(False)" in source
