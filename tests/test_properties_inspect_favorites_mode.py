from pathlib import Path


def test_inspect_favorites_only_renders_only_favorites_group():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "if favorites_only and str(group_id or \"\").strip() != \"favorites\":" in source
    assert "for group_id, group_label in list(self._inspect_properties_group_order):" in source


def test_inspect_property_checkboxes_use_high_contrast_checked_state():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "QCheckBox#InspectPropertySelectAll::indicator:checked," in source
    assert "background: {theme_rgba(DARK_THEME.colors.accent_hover, 0.90)};" in source
    assert "QCheckBox#InspectPropertySelectAll::indicator:checked:hover," in source
