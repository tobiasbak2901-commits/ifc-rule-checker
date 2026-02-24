from pathlib import Path


def test_issue_selection_and_selection_sync_are_wired_to_ai_card_refresh():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "self._ai_card_refresh_timer.setInterval(250)" in source
    assert 'self._schedule_ai_card_refresh("selection_sync")' in source
    assert 'self._update_clash_explanation_visuals(issue)' in source
    assert 'self._schedule_ai_card_refresh("legacy_update")' in source
