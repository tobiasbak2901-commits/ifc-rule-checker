from pathlib import Path

def test_favorite_preset_dataclass_shape():
    source = Path("models.py").read_text(encoding="utf-8")
    assert "class FavoritePreset:" in source
    assert "id: str" in source
    assert "name: str" in source
    assert "keys: List[str] = field(default_factory=list)" in source


def test_inspect_header_includes_favorites_preset_controls():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "self.inspect_meta_controls_wrap = QtWidgets.QWidget(self.inspect_sticky_header)" in source
    assert 'self.inspect_favorites_label = QtWidgets.QLabel("Favorites", self.inspect_meta_controls_wrap)' in source
    assert 'self.inspect_favorite_preset_combo = QtWidgets.QComboBox(self.inspect_meta_controls_wrap)' in source
    assert 'self.inspect_settings_menu_btn = QtWidgets.QToolButton(self.inspect_meta_controls_wrap)' in source
    assert "self.inspect_settings_menu = QtWidgets.QMenu(self.inspect_settings_menu_btn)" in source
    assert "self.inspect_favorite_preset_combo.currentIndexChanged.connect(self._on_inspect_favorite_preset_changed)" in source


def test_favorite_preset_management_methods_exist():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "def _populate_inspect_settings_menu(self) -> None:" in source
    assert "def _create_inspect_favorite_preset(self) -> None:" in source
    assert "def _rename_active_inspect_favorite_preset(self) -> None:" in source
    assert "def _delete_active_inspect_favorite_preset(self) -> None:" in source
    assert "reset_layout_action = menu.addAction(\"Reset panel layout\")" in source
    assert "def _reset_inspect_panel_layout(self) -> None:" in source
    assert "is_system_preset = str(active.id or \"\") in {\"default\", \"favorite\"}" in source
    assert "delete_action.setEnabled(not is_system_preset)" in source


def test_favorite_preset_persistence_is_schema_versioned():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "self._favorite_schema_version = 2" in source
    assert '"schemaVersion": int(self._favorite_schema_version)' in source
    assert '"activePresetId": str(self._favorite_active_preset_id or "default")' in source
    assert '"presets": [self._favorite_preset_payload(preset) for preset in list(self._favorite_presets or [])]' in source


def test_default_and_favorite_presets_are_always_available():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "def _favorite_preset_favorite() -> FavoritePreset:" in source
    assert "return FavoritePreset(id=\"favorite\", name=\"Favorite\", keys=[])" in source
    assert "if \"favorite\" not in {str(preset.id or \"\").strip() for preset in normalized}:" in source
