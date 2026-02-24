from pathlib import Path


def test_overlay_theme_tokens_are_defined():
    source = Path("ui/theme.py").read_text(encoding="utf-8")
    assert "def overlay_surface_tokens(" in source
    assert '"--surface":' in source
    assert '"--surface-2":' in source
    assert '"--text":' in source
    assert '"--text-muted":' in source
    assert '"--border":' in source
    assert '"--hover":' in source
    assert '"--focus":' in source


def test_main_window_styles_all_overlay_surfaces_with_shared_tokens():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "overlay_tokens = {" in source
    assert 'QComboBox QAbstractItemView {' in source
    assert "QDialog, QMessageBox {" in source
    assert "QMenu {" in source
    assert 'background: {overlay_tokens["--surface-2"]};' in source
    assert 'color: {overlay_tokens["--text"]};' in source
    assert 'background: {overlay_tokens["--hover"]};' in source


def test_demo_script_exists_for_manual_dark_overlay_checks():
    source = Path("scripts/theme_overlay_demo.py").read_text(encoding="utf-8")
    assert "class OverlayThemeDemo(QtWidgets.QWidget):" in source
    assert "dropdown_menu_overrides(DARK_THEME)" in source
    assert "dialog = QtWidgets.QDialog(self)" in source
