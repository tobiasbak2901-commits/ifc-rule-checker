from pathlib import Path


def test_section_headers_are_subtle_and_animated():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "self.header_btn.setIconSize(QtCore.QSize(10, 10))" in source
    assert "self._content_anim = QtCore.QPropertyAnimation(self.content, b\"maximumHeight\", self)" in source
    assert "self._content_anim.setDuration(150)" in source
    assert "self._content_anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)" in source
    assert "border-bottom: 1px solid" in source


def test_inspect_panel_forces_dark_menu_and_dropdown_surfaces():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "QGroupBox#InspectPropertiesGroup QMenu {" in source
    assert "QGroupBox#InspectPropertiesGroup QMenu::item:selected {" in source
    assert "QGroupBox#InspectPropertiesGroup QComboBox QAbstractItemView {" in source
    assert "self.inspect_favorite_preset_popup = QtWidgets.QListView(self.inspect_favorite_preset_combo)" in source
    assert 'self.inspect_favorite_preset_popup.setObjectName("InspectFavoritePresetPopup")' in source
    assert "self.inspect_favorite_preset_combo.setView(self.inspect_favorite_preset_popup)" in source
    assert "QListView#InspectFavoritePresetPopup {" in source
    assert "QListView#InspectFavoritePresetPopup::item:selected {" in source
    assert "QComboBox#InspectFavoritePresetCombo QComboBoxPrivateContainer {" in source
    assert "QComboBox#InspectFavoritePresetCombo QComboBoxPrivateContainer QFrame {" in source
    assert "QComboBox#InspectFavoritePresetCombo QComboBoxPrivateContainer QComboBoxPrivateScroller {" in source
    assert 'self.inspect_favorite_preset_popup.setProperty("data-ui", "favorites-dropdown")' in source
    assert "self.inspect_favorite_preset_popup.installEventFilter(self)" in source
    assert "def _inspect_favorite_popup_stylesheet(self) -> str:" in source
    assert 'QWidget#InspectFavoritePresetPopupRoot[data-ui="favorites-dropdown"] {' in source
    assert 'popup_root.setProperty("data-ui", "favorites-dropdown")' in source
    assert "self._inspect_favorite_preset_popup_root = popup_root" in source
    assert "popup_palette.setColor(QtGui.QPalette.Base, QColor(10, 16, 30, 252))" in source
    assert "popup_palette.setColor(QtGui.QPalette.Highlight, QColor(255, 46, 136, 61))" in source


def test_inspect_favorites_popup_wrapper_avoids_white_frame_values():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    anchor = "QComboBox#InspectFavoritePresetCombo QComboBoxPrivateContainer {"
    start = source.find(anchor)
    assert start >= 0
    end = source.find("QLineEdit#InspectPropertiesSearch {", start)
    assert end > start
    block = source[start:end]
    assert "#fff" not in block.lower()
    assert "rgba(255, 255, 255" not in block


def test_inspect_favorites_popup_root_style_has_white_killer_guard() -> None:
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    anchor = 'QWidget#InspectFavoritePresetPopupRoot[data-ui="favorites-dropdown"] {'
    start = source.find(anchor)
    assert start >= 0
    end = source.find("def _style_inspect_favorite_preset_popup(self) -> None:", start)
    assert end > start
    block = source[start:end]
    assert "#fff" not in block.lower()
    assert "rgba(255, 255, 255" not in block
    assert "outline: none;" in block


def test_header_secondary_line_uses_ifctype_and_system_or_discipline():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "self._set_sticky_secondary_line(" in source
    assert "if not system_group or system_group == \"-\":" in source
    assert "system_group = str(self._ifc_discipline_label(elem) or \"-\")" in source


def test_inspect_header_has_settings_menu_and_virtualized_row_batching_hooks():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "self.inspect_meta_controls_wrap = QtWidgets.QWidget(self.inspect_sticky_header)" in source
    assert "self.inspect_settings_menu_btn = QtWidgets.QToolButton(self.inspect_meta_controls_wrap)" in source
    assert "self.inspect_settings_menu = QtWidgets.QMenu(self.inspect_settings_menu_btn)" in source
    assert "def _populate_inspect_settings_menu(self) -> None:" in source
    assert "expand_action = menu.addAction(\"Expand all\")" in source
    assert "collapse_action = menu.addAction(\"Collapse all\")" in source
    assert "reset_layout_action = menu.addAction(\"Reset panel layout\")" in source
    assert "def _reset_inspect_panel_layout(self) -> None:" in source
    assert "inspect_table_zone_layout.addWidget(self.inspect_scroll, 1)" in source
    assert "self._virtualized_row_threshold = 220" in source
    assert "self._virtualized_row_batch_size = 72" in source
    assert "def _render_group_rows_virtualized(" in source
