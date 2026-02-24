from pathlib import Path


def _source() -> str:
    return Path("ui/main_window.py").read_text(encoding="utf-8")


def test_collapse_all_applies_atomic_state_then_recomputes_sections_once() -> None:
    source = _source()
    assert "def _collapse_all_inspect_property_groups(self) -> None:" in source
    assert "next_expanded_state = {key: False for key in target_group_ids}" in source
    assert "self._inspect_properties_group_expanded = dict(next_expanded_state)" in source
    assert "pause_widgets = self._inspect_collapse_pause_widgets()" in source
    assert "widget.setUpdatesEnabled(False)" in source
    assert "self._ensure_inspect_hidden_backing_store()" in source
    assert "self._render_inspect_property_sections()" in source
    assert "QtWidgets.QApplication.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)" in source
    assert "self._reset_inspect_property_layout_cache()" in source
    assert "widget.setUpdatesEnabled(True)" in source


def test_collapse_all_dev_guard_checks_only_headers_visible_when_all_collapsed() -> None:
    source = _source()
    assert "def _dev_validate_inspect_collapse_all_state(self) -> None:" in source
    assert "visiblePropertyRows=" in source
    assert "duplicateRowIds=" in source
    assert "flattenedPropertyRows=" in source
    assert "duplicateFlattenedIds=" in source
    assert "if __debug__:" in source
    assert "raise AssertionError(msg)" in source


def test_render_tracks_stable_flattened_row_ids_for_collapse_all_invariants() -> None:
    source = _source()
    assert "self._inspect_flattened_rows_snapshot = list(flattened_rows)" in source
    assert "Inspect flattened rows must use stable unique ids" in source


def test_collapsed_sections_do_not_keep_mounted_property_rows() -> None:
    source = _source()
    assert "rows_for_render = list(filtered_rows) if bool(expanded) else []" in source
    assert "Inspect collapsed groups must render zero property rows" in source


def test_group_toggle_rerenders_sections_to_mount_unmount_children() -> None:
    source = _source()
    assert "def _on_inspect_property_section_toggled(self, group_id: str, expanded: bool) -> None:" in source
    assert "self._render_inspect_property_sections()" in source
