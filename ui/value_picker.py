from __future__ import annotations

from typing import Dict, List, Optional, Sequence

from PySide6 import QtCore, QtGui, QtWidgets


class DistinctValuesListModel(QtCore.QAbstractListModel):
    selectionChanged = QtCore.Signal()
    pagingChanged = QtCore.Signal(int, int, int, bool)

    def __init__(self, parent: Optional[QtCore.QObject] = None, *, page_size: int = 200) -> None:
        super().__init__(parent)
        self._all_values: List[str] = []
        self._filtered_indices: List[int] = []
        self._selected_values: Dict[str, bool] = {}
        self._page_size = max(25, int(page_size))
        self._visible_count = 0

    def set_values(self, values: Sequence[str]) -> None:
        unique: List[str] = []
        seen: set[str] = set()
        for raw in list(values or []):
            value = str(raw or "").strip()
            if not value:
                continue
            normalized = value.casefold()
            if normalized in seen:
                continue
            seen.add(normalized)
            unique.append(value)

        selected = {key: True for key in self.selected_values()}
        self.beginResetModel()
        self._all_values = unique
        self._selected_values = {value: True for value in self._all_values if value in selected}
        self._filtered_indices = list(range(len(self._all_values)))
        self._visible_count = min(len(self._filtered_indices), self._page_size)
        self.endResetModel()
        self._emit_paging_changed()

    def set_search_text(self, text: str) -> None:
        needle = str(text or "").strip().casefold()
        self.beginResetModel()
        if not needle:
            self._filtered_indices = list(range(len(self._all_values)))
        else:
            self._filtered_indices = [
                idx
                for idx, value in enumerate(self._all_values)
                if needle in str(value or "").casefold()
            ]
        self._visible_count = min(len(self._filtered_indices), self._page_size)
        self.endResetModel()
        self._emit_paging_changed()

    def set_selected_values(self, values: Sequence[str]) -> None:
        wanted = {str(value or "").strip() for value in list(values or []) if str(value or "").strip()}
        old = set(self.selected_values())
        self._selected_values = {value: True for value in self._all_values if value in wanted}
        if old != set(self.selected_values()):
            self.layoutChanged.emit()
            self.selectionChanged.emit()

    def selected_values(self) -> List[str]:
        return [value for value in self._all_values if self._selected_values.get(value)]

    def load_more(self) -> None:
        total = len(self._filtered_indices)
        if self._visible_count >= total:
            self._emit_paging_changed()
            return
        start = int(self._visible_count)
        end = min(total, start + self._page_size)
        self.beginInsertRows(QtCore.QModelIndex(), start, end - 1)
        self._visible_count = end
        self.endInsertRows()
        self._emit_paging_changed()

    def toggle_index(self, index: QtCore.QModelIndex) -> None:
        if not index.isValid():
            return
        row = int(index.row())
        if row < 0 or row >= self.rowCount():
            return
        value = self._value_for_row(row)
        if not value:
            return
        if self._selected_values.get(value):
            self._selected_values.pop(value, None)
        else:
            self._selected_values[value] = True
        self.dataChanged.emit(index, index, [QtCore.Qt.CheckStateRole])
        self.selectionChanged.emit()

    def rowCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return min(len(self._filtered_indices), int(self._visible_count))

    def data(self, index: QtCore.QModelIndex, role: int = QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None
        value = self._value_for_row(int(index.row()))
        if role == QtCore.Qt.DisplayRole:
            return value
        if role == QtCore.Qt.CheckStateRole:
            return QtCore.Qt.Checked if self._selected_values.get(value) else QtCore.Qt.Unchecked
        return None

    def flags(self, index: QtCore.QModelIndex) -> QtCore.Qt.ItemFlags:
        if not index.isValid():
            return QtCore.Qt.NoItemFlags
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsUserCheckable

    def setData(self, index: QtCore.QModelIndex, value, role: int = QtCore.Qt.EditRole) -> bool:
        if role != QtCore.Qt.CheckStateRole or not index.isValid():
            return False
        checked = int(value) == int(QtCore.Qt.Checked)
        token = self._value_for_row(int(index.row()))
        if not token:
            return False
        if checked:
            self._selected_values[token] = True
        else:
            self._selected_values.pop(token, None)
        self.dataChanged.emit(index, index, [QtCore.Qt.CheckStateRole])
        self.selectionChanged.emit()
        return True

    def visible_range(self) -> tuple[int, int, int, bool]:
        total = int(len(self._filtered_indices))
        if total <= 0 or self.rowCount() <= 0:
            return 0, 0, total, False
        end = int(self.rowCount())
        has_more = bool(end < total)
        return 1, end, total, has_more

    def _value_for_row(self, row: int) -> str:
        if row < 0 or row >= len(self._filtered_indices):
            return ""
        idx = int(self._filtered_indices[row])
        if idx < 0 or idx >= len(self._all_values):
            return ""
        return str(self._all_values[idx] or "")

    def _emit_paging_changed(self) -> None:
        start, end, total, has_more = self.visible_range()
        self.pagingChanged.emit(int(start), int(end), int(total), bool(has_more))


class DistinctValuePickerPopup(QtWidgets.QFrame):
    valuesChanged = QtCore.Signal()

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(None)
        self._anchor: Optional[QtWidgets.QWidget] = parent
        self.setWindowFlag(QtCore.Qt.Popup, True)
        self.setWindowFlag(QtCore.Qt.FramelessWindowHint, True)
        self.setObjectName("FindObjectsValuePickerPopup")
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self.search_edit = QtWidgets.QLineEdit(self)
        self.search_edit.setObjectName("FindObjectsValuePickerSearch")
        self.search_edit.setPlaceholderText("Search values")
        self.search_edit.setClearButtonEnabled(True)
        layout.addWidget(self.search_edit, 0)

        self.list_view = QtWidgets.QListView(self)
        self.list_view.setObjectName("FindObjectsValuePickerList")
        self.list_view.setUniformItemSizes(True)
        self.list_view.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self.list_view.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.list_view.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.list_view.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.list_view, 1)

        footer = QtWidgets.QHBoxLayout()
        footer.setContentsMargins(0, 0, 0, 0)
        footer.setSpacing(6)
        self.range_label = QtWidgets.QLabel("0-0 of 0", self)
        self.range_label.setObjectName("FindObjectsValuePickerRange")
        self.load_more_btn = QtWidgets.QPushButton("Load more", self)
        self.load_more_btn.setObjectName("FindObjectsValuePickerLoadMore")
        self.load_more_btn.setMinimumHeight(24)
        footer.addWidget(self.range_label, 0)
        footer.addStretch(1)
        footer.addWidget(self.load_more_btn, 0)
        layout.addLayout(footer, 0)

        self.model = DistinctValuesListModel(self, page_size=250)
        self.list_view.setModel(self.model)

        self.search_edit.textChanged.connect(self.model.set_search_text)
        self.list_view.clicked.connect(self.model.toggle_index)
        self.load_more_btn.clicked.connect(self.model.load_more)
        self.model.selectionChanged.connect(self.valuesChanged.emit)
        self.model.pagingChanged.connect(self._on_paging_changed)

        for widget in (self, self.search_edit, self.list_view):
            widget.installEventFilter(self)

        self.setStyleSheet(
            """
            QFrame#FindObjectsValuePickerPopup {
                background: rgba(10, 16, 30, 0.985);
                border: 1px solid rgba(148, 163, 184, 0.30);
                border-radius: 9px;
            }
            QLineEdit#FindObjectsValuePickerSearch {
                background: rgba(15, 23, 42, 0.95);
                color: #E2E8F0;
                border: 1px solid rgba(148, 163, 184, 0.34);
                border-radius: 6px;
                padding: 5px 8px;
                selection-background-color: rgba(255, 46, 136, 0.30);
                selection-color: #F8FAFC;
            }
            QLineEdit#FindObjectsValuePickerSearch:focus {
                border-color: rgba(255, 46, 136, 0.66);
            }
            QListView#FindObjectsValuePickerList {
                background: transparent;
                color: #E2E8F0;
                border: 1px solid rgba(148, 163, 184, 0.18);
                border-radius: 6px;
                outline: none;
                padding: 2px;
                selection-background-color: rgba(255, 46, 136, 0.20);
                selection-color: #F8FAFC;
            }
            QListView#FindObjectsValuePickerList::item {
                min-height: 24px;
                padding: 4px 8px;
                border-radius: 5px;
            }
            QListView#FindObjectsValuePickerList::item:hover {
                background: rgba(30, 41, 59, 0.72);
            }
            QLabel#FindObjectsValuePickerRange {
                color: #94A3B8;
                font-size: 10px;
            }
            QPushButton#FindObjectsValuePickerLoadMore {
                background: transparent;
                color: #CBD5E1;
                border: 1px solid rgba(148, 163, 184, 0.30);
                border-radius: 6px;
                padding: 0px 9px;
                font-size: 10px;
                font-weight: 600;
            }
            QPushButton#FindObjectsValuePickerLoadMore:hover {
                border-color: rgba(255, 46, 136, 0.55);
                color: #F8FAFC;
            }
            """
        )

    def set_values(self, values: Sequence[str]) -> None:
        self.model.set_values(values)

    def set_selected_values(self, values: Sequence[str]) -> None:
        self.model.set_selected_values(values)

    def selected_values(self) -> List[str]:
        return self.model.selected_values()

    def show_for(self, anchor: QtWidgets.QWidget) -> None:
        self._anchor = anchor
        self.search_edit.blockSignals(True)
        self.search_edit.setText("")
        self.search_edit.blockSignals(False)
        self.model.set_search_text("")

        screen = QtWidgets.QApplication.primaryScreen().availableGeometry()
        width = max(360, int(anchor.width()) + 180)
        height = 440
        origin = anchor.mapToGlobal(QtCore.QPoint(0, anchor.height()))
        x = int(origin.x())
        y = int(origin.y())
        if y + height > int(screen.bottom()):
            above = int(anchor.mapToGlobal(QtCore.QPoint(0, 0)).y() - height)
            if above >= int(screen.top()):
                y = above
        x = max(int(screen.left()), min(x, int(screen.right() - width)))
        self.setGeometry(x, y, width, height)

        self.show()
        self.raise_()
        self.search_edit.setFocus(QtCore.Qt.PopupFocusReason)

    def eventFilter(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if watched is self.list_view and isinstance(event, QtGui.QKeyEvent) and event.type() == QtCore.QEvent.KeyPress:
            key = int(event.key())
            if key in {int(QtCore.Qt.Key_Space), int(QtCore.Qt.Key_Return), int(QtCore.Qt.Key_Enter)}:
                self.model.toggle_index(self.list_view.currentIndex())
                return True
            if key == int(QtCore.Qt.Key_Escape):
                self.hide()
                return True
        if watched is self.search_edit and isinstance(event, QtGui.QKeyEvent) and event.type() == QtCore.QEvent.KeyPress:
            key = int(event.key())
            if key in {int(QtCore.Qt.Key_Down), int(QtCore.Qt.Key_Up)}:
                self.list_view.setFocus(QtCore.Qt.PopupFocusReason)
                return False
            if key == int(QtCore.Qt.Key_Escape):
                self.hide()
                return True
        return super().eventFilter(watched, event)

    def _on_paging_changed(self, start: int, end: int, total: int, has_more: bool) -> None:
        self.range_label.setText(f"{int(start)}-{int(end)} of {int(total)}")
        self.load_more_btn.setVisible(bool(has_more))


class MultiValuePickerEditor(QtWidgets.QWidget):
    valueChanged = QtCore.Signal()

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("FindObjectsMultiValuePicker")

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.trigger_btn = QtWidgets.QToolButton(self)
        self.trigger_btn.setObjectName("FindObjectsValuePickerTrigger")
        self.trigger_btn.setText("Select values")
        self.trigger_btn.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)
        self.trigger_btn.setAutoRaise(False)
        self.trigger_btn.setMinimumHeight(32)
        self.trigger_btn.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.trigger_btn.setStyleSheet("")
        layout.addWidget(self.trigger_btn, 1)

        self.popup = DistinctValuePickerPopup(self)

        self.trigger_btn.clicked.connect(self._open_popup)
        self.popup.valuesChanged.connect(self._on_popup_values_changed)

    def set_values(self, values: Sequence[str], *, selected_csv: str = "") -> None:
        self.popup.set_values(values)
        if selected_csv:
            self.set_csv_text(selected_csv)
        else:
            selected = self.popup.selected_values()
            self.popup.set_selected_values(selected)
        self._refresh_summary()

    def set_csv_text(self, text: str) -> None:
        tokens = [str(token or "").strip() for token in str(text or "").split(",") if str(token or "").strip()]
        self.popup.set_selected_values(tokens)
        self._refresh_summary()

    def csv_text(self) -> str:
        return ", ".join(self.popup.selected_values())

    def selected_count(self) -> int:
        return len(self.popup.selected_values())

    def set_invalid(self, invalid: bool) -> None:
        self.trigger_btn.setProperty("invalid", bool(invalid))
        style = self.trigger_btn.style()
        if style is not None:
            style.unpolish(self.trigger_btn)
            style.polish(self.trigger_btn)
        self.trigger_btn.update()

    def _open_popup(self) -> None:
        self.popup.show_for(self.trigger_btn)

    def _on_popup_values_changed(self) -> None:
        self._refresh_summary()
        self.valueChanged.emit()

    def _refresh_summary(self) -> None:
        selected = self.popup.selected_values()
        if not selected:
            self.trigger_btn.setText("Select values")
            self.trigger_btn.setToolTip("Select one or more values")
            return
        if len(selected) == 1:
            text = str(selected[0])
            self.trigger_btn.setText(text)
            self.trigger_btn.setToolTip(text)
            return
        first = str(selected[0])
        text = f"{first} +{len(selected) - 1}"
        self.trigger_btn.setText(text)
        self.trigger_btn.setToolTip(", ".join(selected))
