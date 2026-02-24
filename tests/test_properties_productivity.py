from pathlib import Path


def test_properties_favorites_are_project_scoped_in_local_settings():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert 'def _favorite_properties_settings_key(self) -> str:' in source
    assert 'return "properties/favorites_v1"' in source
    assert "settings = QtCore.QSettings(\"Ponker\", \"Resolve\")" in source
    assert '"schemaVersion": int(self._favorite_schema_version)' in source
    assert '"activePresetId": str(self._favorite_active_preset_id or "default")' in source
    assert '"presets": [self._favorite_preset_payload(preset) for preset in list(self._favorite_presets or [])]' in source
    assert "FavoritePreset(id=\"default\", name=\"Default\", keys=[])" in source
    assert "self._load_favorite_properties(force=True)" in source


def test_properties_hover_copy_button_exists_for_value_column():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "self._properties_copy_btn = QtWidgets.QToolButton(self.properties_table.viewport())" in source
    assert "self.properties_table.entered.connect(self._on_properties_table_hover_index)" in source
    assert "def _copy_hovered_property_value(self) -> None:" in source
    assert 'self.statusBar().showMessage("Copied", 1200)' in source


def test_properties_escape_clears_search_across_panel_children():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "self.properties_search_escape = QShortcut(QKeySequence(\"Escape\"), panel_body)" in source
    assert "self.properties_search_escape.setContext(QtCore.Qt.WidgetWithChildrenShortcut)" in source
