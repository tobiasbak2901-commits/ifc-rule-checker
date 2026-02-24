from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from PySide6 import QtCore, QtGui, QtWidgets


_ROLE_KIND = int(QtCore.Qt.UserRole + 301)
_ROLE_VALUE = int(QtCore.Qt.UserRole + 302)


@dataclass(frozen=True)
class _DropdownEntry:
    label: str
    value: str
    search_text: str


class _SearchHighlightDelegate(QtWidgets.QStyledItemDelegate):
    """Draw popup rows and highlight the matching substring."""

    def __init__(self, parent: Optional[QtCore.QObject] = None) -> None:
        super().__init__(parent)
        self._needle = ""

    def set_filter_text(self, text: str) -> None:
        self._needle = str(text or "").strip()

    def sizeHint(self, option: QtWidgets.QStyleOptionViewItem, index: QtCore.QModelIndex) -> QtCore.QSize:
        kind = str(index.data(_ROLE_KIND) or "item").strip().lower()
        base = super().sizeHint(option, index)
        if kind == "header":
            return QtCore.QSize(base.width(), max(20, int(base.height()) - 2))
        if kind == "empty":
            return QtCore.QSize(base.width(), max(24, int(base.height())))
        return QtCore.QSize(base.width(), max(26, int(base.height())))

    def paint(
        self,
        painter: QtGui.QPainter,
        option: QtWidgets.QStyleOptionViewItem,
        index: QtCore.QModelIndex,
    ) -> None:
        kind = str(index.data(_ROLE_KIND) or "item").strip().lower()
        if kind == "header":
            self._paint_header(painter, option, index)
            return
        if kind == "empty":
            self._paint_empty(painter, option, index)
            return

        needle = str(self._needle or "").strip()
        if not needle:
            super().paint(painter, option, index)
            return

        opt = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        text = str(opt.text or "")
        pos = text.casefold().find(needle.casefold())
        if pos < 0:
            super().paint(painter, option, index)
            return

        style = opt.widget.style() if opt.widget is not None else QtWidgets.QApplication.style()
        no_text_opt = QtWidgets.QStyleOptionViewItem(opt)
        no_text_opt.text = ""
        style.drawControl(QtWidgets.QStyle.CE_ItemViewItem, no_text_opt, painter, opt.widget)

        text_rect = style.subElementRect(QtWidgets.QStyle.SE_ItemViewItemText, opt, opt.widget).adjusted(1, 0, -2, 0)
        if not text_rect.isValid():
            return

        prefix = text[:pos]
        match = text[pos : pos + len(needle)]
        suffix = text[pos + len(needle) :]

        painter.save()
        normal_font = QtGui.QFont(opt.font)
        bold_font = QtGui.QFont(opt.font)
        bold_font.setBold(True)

        selected = bool(opt.state & QtWidgets.QStyle.State_Selected)
        text_color = opt.palette.color(QtGui.QPalette.HighlightedText if selected else QtGui.QPalette.Text)
        highlight_fill = QtGui.QColor(255, 46, 136, 96 if selected else 68)

        normal_metrics = QtGui.QFontMetrics(normal_font)
        bold_metrics = QtGui.QFontMetrics(bold_font)
        baseline = int(text_rect.y() + (text_rect.height() + normal_metrics.ascent() - normal_metrics.descent()) / 2)

        x = int(text_rect.x())
        painter.setPen(text_color)

        if prefix:
            painter.setFont(normal_font)
            painter.drawText(QtCore.QPoint(x, baseline), prefix)
            x += int(normal_metrics.horizontalAdvance(prefix))

        if match:
            match_width = int(max(1, bold_metrics.horizontalAdvance(match)))
            marker_rect = QtCore.QRect(x - 1, text_rect.y() + 3, match_width + 2, max(8, text_rect.height() - 6))
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(highlight_fill)
            painter.drawRoundedRect(marker_rect, 4, 4)
            painter.setPen(text_color)
            painter.setFont(bold_font)
            painter.drawText(QtCore.QPoint(x, baseline), match)
            x += match_width

        if suffix:
            painter.setFont(normal_font)
            painter.drawText(QtCore.QPoint(x, baseline), suffix)

        painter.restore()

    def _paint_header(
        self,
        painter: QtGui.QPainter,
        option: QtWidgets.QStyleOptionViewItem,
        index: QtCore.QModelIndex,
    ) -> None:
        opt = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        style = opt.widget.style() if opt.widget is not None else QtWidgets.QApplication.style()
        no_text_opt = QtWidgets.QStyleOptionViewItem(opt)
        no_text_opt.text = ""
        no_text_opt.state = no_text_opt.state & ~QtWidgets.QStyle.State_Selected
        style.drawControl(QtWidgets.QStyle.CE_ItemViewItem, no_text_opt, painter, opt.widget)

        text_rect = style.subElementRect(QtWidgets.QStyle.SE_ItemViewItemText, opt, opt.widget).adjusted(0, 0, 0, 0)
        painter.save()
        font = QtGui.QFont(opt.font)
        font.setBold(True)
        font.setPointSize(max(8, int(font.pointSize() - 1)))
        painter.setFont(font)
        painter.setPen(QtGui.QColor(148, 163, 184))
        painter.drawText(text_rect, int(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft), str(opt.text or "").upper())
        painter.restore()

    def _paint_empty(
        self,
        painter: QtGui.QPainter,
        option: QtWidgets.QStyleOptionViewItem,
        index: QtCore.QModelIndex,
    ) -> None:
        opt = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        style = opt.widget.style() if opt.widget is not None else QtWidgets.QApplication.style()
        no_text_opt = QtWidgets.QStyleOptionViewItem(opt)
        no_text_opt.text = ""
        no_text_opt.state = no_text_opt.state & ~QtWidgets.QStyle.State_Selected
        style.drawControl(QtWidgets.QStyle.CE_ItemViewItem, no_text_opt, painter, opt.widget)

        text_rect = style.subElementRect(QtWidgets.QStyle.SE_ItemViewItemText, opt, opt.widget)
        painter.save()
        painter.setFont(opt.font)
        painter.setPen(QtGui.QColor(148, 163, 184))
        painter.drawText(text_rect, int(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft), str(opt.text or ""))
        painter.restore()


class SearchableDropdown(QtWidgets.QComboBox):
    """Combo with a searchable dark popup and persisted recent selections."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self._entries: List[_DropdownEntry] = []
        self._entries_by_value: Dict[str, _DropdownEntry] = {}
        self._recent_settings_key = ""
        self._recent_limit = 8
        self._recent_enabled = True
        self._recent_title = "Recent"
        self._all_title = "All"
        self._search_placeholder = "Search"

        self._popup: Optional[QtWidgets.QFrame] = None
        self._popup_layout: Optional[QtWidgets.QVBoxLayout] = None
        self._popup_search: Optional[QtWidgets.QLineEdit] = None
        self._popup_list: Optional[QtWidgets.QListView] = None
        self._popup_model: Optional[QtGui.QStandardItemModel] = None
        self._popup_delegate: Optional[_SearchHighlightDelegate] = None

        self.setInsertPolicy(QtWidgets.QComboBox.NoInsert)
        self.setMaxVisibleItems(18)

    def set_recent_settings_key(self, key: str, *, limit: int = 8) -> None:
        self._recent_settings_key = str(key or "").strip()
        self._recent_limit = max(1, int(limit or 8))

    def set_recent_enabled(self, enabled: bool) -> None:
        self._recent_enabled = bool(enabled)

    def set_popup_titles(self, *, recent: str = "Recent", all_items: str = "All") -> None:
        self._recent_title = str(recent or "Recent").strip() or "Recent"
        self._all_title = str(all_items or "All").strip() or "All"

    def set_search_placeholder(self, text: str) -> None:
        self._search_placeholder = str(text or "Search").strip() or "Search"
        if isinstance(self._popup_search, QtWidgets.QLineEdit):
            self._popup_search.setPlaceholderText(self._search_placeholder)

    def set_options(self, options: Sequence[Tuple[str, str]], *, preserve_value: str = "") -> None:
        previous = str(preserve_value or self.currentData() or "").strip()
        cleaned: List[_DropdownEntry] = []
        dedupe: set[str] = set()
        for label_raw, value_raw in list(options or []):
            label = str(label_raw or "").strip()
            value = str(value_raw or "").strip()
            if not label or not value:
                continue
            if value in dedupe:
                continue
            dedupe.add(value)
            cleaned.append(_DropdownEntry(label=label, value=value, search_text=label.casefold()))

        self._entries = cleaned
        self._entries_by_value = {entry.value: entry for entry in self._entries}

        was_blocked = self.signalsBlocked()
        if not was_blocked:
            self.blockSignals(True)
        self.clear()
        for entry in self._entries:
            super().addItem(entry.label, entry.value)
        target = self.findData(previous)
        if target >= 0:
            self.setCurrentIndex(target)
        elif self.count() > 0:
            self.setCurrentIndex(0)
        if not was_blocked:
            self.blockSignals(False)

    def showPopup(self) -> None:
        if not self.isEnabled():
            return
        self._ensure_popup()
        if not isinstance(self._popup, QtWidgets.QFrame):
            return
        if isinstance(self._popup_search, QtWidgets.QLineEdit):
            self._popup_search.blockSignals(True)
            self._popup_search.setText("")
            self._popup_search.blockSignals(False)
        self._rebuild_popup_model("")
        self._position_popup()
        self._popup.show()
        self._popup.raise_()
        if isinstance(self._popup_search, QtWidgets.QLineEdit):
            self._popup_search.setFocus(QtCore.Qt.PopupFocusReason)
            self._popup_search.selectAll()

    def hidePopup(self) -> None:
        if isinstance(self._popup, QtWidgets.QFrame):
            self._popup.hide()

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        if event.key() in {
            int(QtCore.Qt.Key_Space),
            int(QtCore.Qt.Key_Return),
            int(QtCore.Qt.Key_Enter),
            int(QtCore.Qt.Key_Down),
        }:
            self.showPopup()
            event.accept()
            return
        super().keyPressEvent(event)

    def eventFilter(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if watched is self._popup_search and isinstance(event, QtGui.QKeyEvent) and event.type() == QtCore.QEvent.KeyPress:
            return self._handle_search_key(event)
        if watched is self._popup_list and isinstance(event, QtGui.QKeyEvent) and event.type() == QtCore.QEvent.KeyPress:
            return self._handle_list_key(event)
        if watched is self._popup and event.type() == QtCore.QEvent.Hide:
            self.setFocus(QtCore.Qt.PopupFocusReason)
        return super().eventFilter(watched, event)

    def _ensure_popup(self) -> None:
        if isinstance(self._popup, QtWidgets.QFrame):
            return

        popup = QtWidgets.QFrame(None)
        popup.setWindowFlag(QtCore.Qt.Popup, True)
        popup.setWindowFlag(QtCore.Qt.FramelessWindowHint, True)
        popup.setObjectName("SearchableDropdownPopup")
        popup.setProperty("themeScope", "app")
        popup.setAttribute(QtCore.Qt.WA_StyledBackground, True)

        layout = QtWidgets.QVBoxLayout(popup)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        search = QtWidgets.QLineEdit(popup)
        search.setObjectName("SearchableDropdownSearch")
        search.setPlaceholderText(self._search_placeholder)
        search.setClearButtonEnabled(True)

        list_view = QtWidgets.QListView(popup)
        list_view.setObjectName("SearchableDropdownList")
        list_view.setUniformItemSizes(True)
        list_view.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        list_view.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        list_view.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        list_view.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        list_view.setAlternatingRowColors(False)

        model = QtGui.QStandardItemModel(list_view)
        list_view.setModel(model)

        delegate = _SearchHighlightDelegate(list_view)
        list_view.setItemDelegate(delegate)

        layout.addWidget(search, 0)
        layout.addWidget(list_view, 1)

        # Keep the popup self-styled so it never falls back to white palette defaults.
        popup.setStyleSheet(
            """
            QFrame#SearchableDropdownPopup {
                background: rgba(10, 16, 30, 0.98);
                border: 1px solid rgba(148, 163, 184, 0.30);
                border-radius: 8px;
            }
            QLineEdit#SearchableDropdownSearch {
                background: rgba(15, 23, 42, 0.95);
                color: #e2e8f0;
                border: 1px solid rgba(148, 163, 184, 0.34);
                border-radius: 6px;
                padding: 5px 8px;
                selection-background-color: rgba(255, 46, 136, 0.30);
                selection-color: #f8fafc;
            }
            QLineEdit#SearchableDropdownSearch:focus {
                border-color: rgba(255, 46, 136, 0.66);
            }
            QListView#SearchableDropdownList {
                background: transparent;
                color: #e2e8f0;
                border: none;
                outline: none;
                padding: 0px;
                selection-background-color: rgba(255, 46, 136, 0.24);
                selection-color: #f8fafc;
            }
            QListView#SearchableDropdownList::item {
                min-height: 24px;
                padding: 4px 8px;
                border-radius: 6px;
            }
            QListView#SearchableDropdownList::item:hover {
                background: rgba(30, 41, 59, 0.72);
            }
            QListView#SearchableDropdownList::item:selected {
                background: rgba(255, 46, 136, 0.24);
            }
            """
        )

        search.textChanged.connect(self._on_popup_search_text_changed)
        list_view.clicked.connect(self._on_popup_index_clicked)
        list_view.doubleClicked.connect(self._on_popup_index_clicked)

        popup.installEventFilter(self)
        search.installEventFilter(self)
        list_view.installEventFilter(self)

        self._popup = popup
        self._popup_layout = layout
        self._popup_search = search
        self._popup_list = list_view
        self._popup_model = model
        self._popup_delegate = delegate

    def _position_popup(self) -> None:
        if not isinstance(self._popup, QtWidgets.QFrame):
            return
        if not isinstance(self._popup_list, QtWidgets.QListView):
            return

        available = QtWidgets.QApplication.primaryScreen().availableGeometry()
        width = max(int(self.width()), 280)

        row_height = self._popup_list.sizeHintForRow(0)
        if row_height <= 0:
            row_height = 26
        visible_rows = min(14, max(6, int((self._popup_model.rowCount() if isinstance(self._popup_model, QtGui.QStandardItemModel) else 0))))
        header_height = 40
        height = int(header_height + visible_rows * row_height + 14)

        origin = self.mapToGlobal(QtCore.QPoint(0, self.height()))
        x = int(origin.x())
        y = int(origin.y())
        if y + height > available.bottom() and (self.mapToGlobal(QtCore.QPoint(0, 0)).y() - height) > available.top():
            y = int(self.mapToGlobal(QtCore.QPoint(0, 0)).y() - height)
        x = max(int(available.left()), min(x, int(available.right() - width)))

        self._popup.setGeometry(x, y, width, height)

    def _on_popup_search_text_changed(self, text: str) -> None:
        self._rebuild_popup_model(str(text or ""))

    def _rebuild_popup_model(self, search_text: str) -> None:
        if not isinstance(self._popup_model, QtGui.QStandardItemModel):
            return

        needle = str(search_text or "").strip().casefold()
        filtered = [entry for entry in self._entries if (not needle) or (needle in entry.search_text)]

        recent_entries: List[_DropdownEntry] = []
        if self._recent_enabled:
            for recent_value in self._load_recent_values():
                entry = self._entries_by_value.get(str(recent_value or ""))
                if entry is None:
                    continue
                if needle and needle not in entry.search_text:
                    continue
                recent_entries.append(entry)

        self._popup_model.clear()

        if recent_entries:
            self._append_header(self._recent_title)
            for entry in recent_entries:
                self._append_item(entry)

        if filtered:
            self._append_header(self._all_title)
            for entry in filtered:
                self._append_item(entry)

        if self._popup_model.rowCount() <= 0:
            empty = QtGui.QStandardItem("No matches")
            empty.setData("empty", _ROLE_KIND)
            empty.setFlags(QtCore.Qt.ItemIsEnabled)
            self._popup_model.appendRow(empty)

        if isinstance(self._popup_delegate, _SearchHighlightDelegate):
            self._popup_delegate.set_filter_text(str(search_text or ""))

        self._select_first_popup_item(preferred_value=str(self.currentData() or "").strip())

    def _append_header(self, text: str) -> None:
        if not isinstance(self._popup_model, QtGui.QStandardItemModel):
            return
        header = QtGui.QStandardItem(str(text or "").strip())
        header.setData("header", _ROLE_KIND)
        header.setFlags(QtCore.Qt.ItemIsEnabled)
        self._popup_model.appendRow(header)

    def _append_item(self, entry: _DropdownEntry) -> None:
        if not isinstance(self._popup_model, QtGui.QStandardItemModel):
            return
        item = QtGui.QStandardItem(entry.label)
        item.setData("item", _ROLE_KIND)
        item.setData(entry.value, _ROLE_VALUE)
        item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
        self._popup_model.appendRow(item)

    def _select_first_popup_item(self, *, preferred_value: str = "") -> None:
        if not isinstance(self._popup_model, QtGui.QStandardItemModel):
            return
        if not isinstance(self._popup_list, QtWidgets.QListView):
            return

        preferred = str(preferred_value or "").strip()
        preferred_index: Optional[QtCore.QModelIndex] = None
        first_index: Optional[QtCore.QModelIndex] = None

        for row in range(self._popup_model.rowCount()):
            idx = self._popup_model.index(row, 0)
            if not self._popup_index_is_selectable(idx):
                continue
            if first_index is None:
                first_index = idx
            if preferred and str(idx.data(_ROLE_VALUE) or "").strip() == preferred:
                preferred_index = idx
                break

        target = preferred_index if preferred_index is not None else first_index
        if target is not None and target.isValid():
            self._popup_list.setCurrentIndex(target)
            self._popup_list.scrollTo(target, QtWidgets.QAbstractItemView.PositionAtCenter)

    def _popup_index_is_selectable(self, index: QtCore.QModelIndex) -> bool:
        if not index.isValid():
            return False
        kind = str(index.data(_ROLE_KIND) or "").strip().lower()
        return kind == "item"

    def _on_popup_index_clicked(self, index: QtCore.QModelIndex) -> None:
        self._commit_popup_index(index)

    def _commit_popup_index(self, index: QtCore.QModelIndex) -> bool:
        if not self._popup_index_is_selectable(index):
            return False
        value = str(index.data(_ROLE_VALUE) or "").strip()
        if not value:
            return False
        combo_index = self.findData(value)
        if combo_index < 0:
            return False
        self.setCurrentIndex(combo_index)
        self._remember_recent(value)
        self.hidePopup()
        return True

    def _handle_search_key(self, event: QtGui.QKeyEvent) -> bool:
        key = int(event.key())
        if key in {int(QtCore.Qt.Key_Down), int(QtCore.Qt.Key_Up)}:
            self._move_popup_selection(+1 if key == int(QtCore.Qt.Key_Down) else -1)
            return True
        if key in {int(QtCore.Qt.Key_PageDown), int(QtCore.Qt.Key_PageUp)}:
            self._move_popup_selection(+5 if key == int(QtCore.Qt.Key_PageDown) else -5)
            return True
        if key in {int(QtCore.Qt.Key_Return), int(QtCore.Qt.Key_Enter)}:
            if isinstance(self._popup_list, QtWidgets.QListView):
                return self._commit_popup_index(self._popup_list.currentIndex())
            return True
        if key == int(QtCore.Qt.Key_Escape):
            self.hidePopup()
            return True
        return False

    def _handle_list_key(self, event: QtGui.QKeyEvent) -> bool:
        key = int(event.key())
        if key in {int(QtCore.Qt.Key_Return), int(QtCore.Qt.Key_Enter)}:
            if isinstance(self._popup_list, QtWidgets.QListView):
                return self._commit_popup_index(self._popup_list.currentIndex())
            return True
        if key == int(QtCore.Qt.Key_Escape):
            self.hidePopup()
            return True
        if key in {int(QtCore.Qt.Key_Up), int(QtCore.Qt.Key_Down), int(QtCore.Qt.Key_PageUp), int(QtCore.Qt.Key_PageDown)}:
            return False
        text = str(event.text() or "")
        if text and isinstance(self._popup_search, QtWidgets.QLineEdit):
            self._popup_search.setFocus(QtCore.Qt.PopupFocusReason)
            self._popup_search.insert(text)
            return True
        return False

    def _move_popup_selection(self, step: int) -> None:
        if not isinstance(self._popup_list, QtWidgets.QListView):
            return
        if not isinstance(self._popup_model, QtGui.QStandardItemModel):
            return

        current = self._popup_list.currentIndex()
        row = int(current.row()) if current.isValid() else -1
        direction = 1 if step >= 0 else -1
        remaining = abs(int(step))

        while remaining > 0:
            candidate = row + direction
            while 0 <= candidate < self._popup_model.rowCount():
                idx = self._popup_model.index(candidate, 0)
                if self._popup_index_is_selectable(idx):
                    row = candidate
                    break
                candidate += direction
            else:
                break
            remaining -= 1

        if 0 <= row < self._popup_model.rowCount():
            target = self._popup_model.index(row, 0)
            if self._popup_index_is_selectable(target):
                self._popup_list.setCurrentIndex(target)
                self._popup_list.scrollTo(target, QtWidgets.QAbstractItemView.PositionAtCenter)

    def _load_recent_values(self) -> List[str]:
        history = self._load_recent_history()
        if not history:
            return []
        counts: Dict[str, int] = {}
        first_seen_index: Dict[str, int] = {}
        for idx, value in enumerate(history):
            token = str(value or "").strip()
            if not token:
                continue
            counts[token] = int(counts.get(token, 0) + 1)
            if token not in first_seen_index:
                first_seen_index[token] = int(idx)
        ranked = sorted(
            counts.keys(),
            key=lambda token: (-int(counts.get(token, 0)), int(first_seen_index.get(token, 10_000_000)), token.casefold()),
        )
        return ranked[: max(1, int(self._recent_limit))]

    def _load_recent_history(self) -> List[str]:
        key = str(self._recent_settings_key or "").strip()
        if (not self._recent_enabled) or (not key):
            return []
        settings = QtCore.QSettings("Ponker", "Resolve")
        raw = settings.value(key, [])
        if isinstance(raw, (list, tuple)):
            return [str(item or "").strip() for item in list(raw) if str(item or "").strip()]
        if isinstance(raw, str):
            value = str(raw or "").strip()
            if not value:
                return []
            if value.startswith("[") and value.endswith("]"):
                text = value.strip("[]")
                return [piece.strip().strip('"\'') for piece in text.split(",") if piece.strip()]
            return [piece.strip() for piece in value.split("|") if piece.strip()]
        return []

    def _remember_recent(self, value: str) -> None:
        normalized = str(value or "").strip()
        key = str(self._recent_settings_key or "").strip()
        if (not self._recent_enabled) or (not key) or (not normalized):
            return
        values = [v for v in self._load_recent_history() if v]
        values.insert(0, normalized)
        # Persist a bounded interaction history and derive "most used" from it.
        values = values[:128]
        settings = QtCore.QSettings("Ponker", "Resolve")
        settings.setValue(key, values)
