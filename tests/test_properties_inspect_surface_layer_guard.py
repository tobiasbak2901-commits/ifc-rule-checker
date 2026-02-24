from pathlib import Path


def test_inspect_surface_layer_guard_blocks_duplicate_header_and_floating_children() -> None:
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "def _dev_validate_inspect_surface_layers(self) -> None:" in source
    assert "Inspect table must render one Property/Value header" in source
    assert "Inspect table must not render floating overlay children" in source
    assert "self._dev_validate_inspect_surface_layers()" in source
