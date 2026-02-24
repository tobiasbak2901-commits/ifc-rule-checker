from pathlib import Path


def test_search_sets_panel_has_icon_toolbar_filter_and_sort_controls():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "self.search_set_new_btn = QtWidgets.QToolButton()" in source
    assert "self.search_set_duplicate_btn = QtWidgets.QToolButton()" in source
    assert "self.search_set_delete_btn = QtWidgets.QToolButton()" in source
    assert 'self.search_set_new_btn.setObjectName("SearchSetsToolbarBtn")' in source
    assert 'self.search_set_new_btn.setToolTip("New search set")' in source
    assert 'self.search_set_search_edit = QtWidgets.QLineEdit(self.search_sets_group)' in source
    assert 'self.search_set_search_edit.setObjectName("SearchSetsFilterInput")' in source
    assert 'self.search_set_sort_combo = QtWidgets.QComboBox(self.search_sets_group)' in source
    assert 'self.search_set_sort_combo.setObjectName("SearchSetsSortCombo")' in source
    assert 'self.search_set_sort_combo.addItem("A->Z", "az")' in source
    assert 'self.search_set_sort_combo.addItem("Recent", "recent")' in source
    assert 'self.search_sets_list.setObjectName("SearchSetsList")' in source
    assert "self.search_sets_list.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)" in source


def test_search_sets_panel_supports_folders_badges_and_context_actions():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "def _split_search_set_name(name: str) -> Tuple[str, str]:" in source
    assert "def _compose_search_set_name(folder: str, label: str) -> str:" in source
    assert "def _build_search_set_folder_row_widget(self, folder: str) -> QtWidgets.QWidget:" in source
    assert "def _build_search_set_item_row_widget(" in source
    assert 'count_badge.setObjectName("SearchSetCountBadge")' in source
    assert 'menu_btn.setObjectName("SearchSetItemMenuBtn")' in source
    assert "def _show_search_set_context_menu(self, item: QtWidgets.QListWidgetItem, global_pos: QtCore.QPoint) -> None:" in source
    assert 'rename_action = menu.addAction("Rename")' in source
    assert 'move_action = menu.addAction("Move to folder...")' in source
    assert 'export_action = menu.addAction("Export...")' in source
    assert 'delete_action = menu.addAction("Delete")' in source
    assert "def _rename_search_set_from_context(self, search_set: SearchSet) -> None:" in source
    assert "def _move_search_set_from_context(self, search_set: SearchSet) -> None:" in source
    assert "def _export_search_set_from_context(self, search_set: SearchSet) -> None:" in source
    assert "def _delete_search_set_from_context(self, search_set: SearchSet) -> None:" in source


def test_search_sets_panel_applies_selection_and_enabled_toggle_to_viewer():
    source = Path("ui/main_window.py").read_text(encoding="utf-8")
    assert "def _apply_search_set_selection_to_viewer(self, search_set: Optional[SearchSet], *, focus: bool = False) -> None:" in source
    assert "def _apply_enabled_search_set_visibility(self) -> None:" in source
    assert "self._apply_search_set_selection_to_viewer(selected, focus=False)" in source
    assert "self._apply_enabled_search_set_visibility()" in source
    assert "self._context_isolate_selection(list(guids), transparent=False)" in source
    assert "self._context_show_all()" in source
    assert "def _on_search_set_filter_text_changed(self, _text: str) -> None:" in source
    assert "def _on_search_set_sort_changed(self, _index: int) -> None:" in source
    assert 'QToolButton#SearchSetsToolbarBtn {' in source
    assert 'QLineEdit#SearchSetsFilterInput,' in source
    assert 'QComboBox#SearchSetsSortCombo {' in source
    assert 'QListWidget#SearchSetsList {' in source
    assert 'QFrame#SearchSetItemRow[selected="true"] {' in source
