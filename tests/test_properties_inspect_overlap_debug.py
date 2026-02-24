from pathlib import Path


def _source() -> str:
    return Path("ui/main_window.py").read_text(encoding="utf-8")


def test_inspect_overlap_debug_toggle_can_be_enabled_from_env_and_menu() -> None:
    source = _source()
    assert 'os.getenv("PONKER_INSPECT_OVERLAP_DEBUG"' in source
    assert 'debug_action = menu.addAction("Debug overlap overlay")' in source
    assert "debug_action.setCheckable(True)" in source
    assert "debug_action.toggled.connect(self._on_toggle_inspect_overlap_debug)" in source


def test_inspect_overlap_debug_adds_data_attributes_for_rows_and_layers() -> None:
    source = _source()
    assert 'setProperty("data-row-id"' in source
    assert 'setProperty("data-row-type"' in source
    assert 'setProperty("data-layer", "main")' in source
    assert 'setProperty("data-layer", "sticky")' in source


def test_collapse_all_debug_logging_reports_flattened_and_virtualizer_measurements() -> None:
    source = _source()
    assert "def _log_inspect_collapse_all_debug(self) -> None:" in source
    assert "expandedGroupIds=" in source
    assert "flattenedRows=" in source
    assert "firstTypes=" in source
    assert "virtualizer " in source
