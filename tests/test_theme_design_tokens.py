from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ui.theme import DARK_THEME, normalize_stylesheet


def test_theme_file_defines_design_tokens():
    source = Path("ui/theme.py").read_text(encoding="utf-8")
    assert "class ColorTokens" in source
    assert "class SpacingTokens" in source
    assert "class FontSizeTokens" in source
    assert "class RadiusTokens" in source
    assert "DARK_THEME = ThemeTokens(" in source
    assert "def normalize_stylesheet(" in source


def test_main_window_uses_unified_theme_tokens():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "from ui.theme import DARK_THEME, dropdown_menu_overrides, hex_to_rgb, normalize_stylesheet, rgba as theme_rgba" in source
    assert "THEME = DARK_THEME" in source
    assert "{dropdown_menu_overrides(self.THEME)}" in source
    assert "self.setStyleSheet(normalize_stylesheet(stylesheet, self.THEME))" in source


def test_checkbox_tokens_and_states_are_defined_for_dark_theme_contrast():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "\"--check-bg\":" in source
    assert "\"--check-border\":" in source
    assert "QCheckBox::indicator:checked {" in source
    assert "QCheckBox:focus::indicator {" in source
    assert "QCheckBox::indicator:disabled {" in source
    assert "QCheckBox#InspectPropertySelectAll::indicator:checked," in source


def test_dropdown_menu_overrides_live_in_central_theme_file():
    theme_source = Path("ui/theme.py").read_text(encoding="utf-8")
    dropdown_source = Path("ui/theme_overrides/dropdowns.qss").read_text(encoding="utf-8")
    assert "def dropdown_menu_overrides(" in theme_source
    assert "_read_override_template(\"dropdowns.qss\")" in theme_source
    assert "QAbstractItemView#FindObjectsComboPopup[themeScope=\"app\"]" in dropdown_source
    assert "QMenu#FindObjectsSuggestMenu[themeScope=\"app\"]" in dropdown_source


def test_panels_use_theme_tokens():
    ai_views = Path("ui/panels/ai_views_panel.py").read_text(encoding="utf-8")
    issue_card = Path("ui/panels/issue_card.py").read_text(encoding="utf-8")
    tooltip = Path("ui/tooltip_card.py").read_text(encoding="utf-8")
    assert "from ui.theme import DARK_THEME, normalize_stylesheet" in ai_views
    assert "self.setStyleSheet(normalize_stylesheet(stylesheet))" in ai_views
    assert "from ui.theme import DARK_THEME, normalize_stylesheet, rgba as theme_rgba" in issue_card
    assert "from ui.theme import DARK_THEME, normalize_stylesheet, rgba as theme_rgba" in tooltip


def test_normalize_stylesheet_replaces_legacy_colors():
    source = (
        "background:#14213A;color:#FFFFFF;border:1px solid #18263D;"
        "selection-color:#FBCFE8;box-shadow:0 0 0 rgba(255, 255, 255, 30);"
    )
    normalized = normalize_stylesheet(source, DARK_THEME)
    assert "#14213A" not in normalized
    assert "#18263D" not in normalized
    assert "#FFFFFF" not in normalized
    assert "#FBCFE8" not in normalized
    assert "255, 255, 255" not in normalized
    assert DARK_THEME.colors.panel_elevated in normalized
    assert DARK_THEME.colors.text_inverse in normalized
    assert DARK_THEME.colors.accent_hover in normalized
