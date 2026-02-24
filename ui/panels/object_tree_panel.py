from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple

from PySide6 import QtCore, QtGui, QtWidgets

from .ai_views_model import AiViewCard, AiViewsModel, build_ai_views_model
from .ai_views_panel import AiViewsPanel
from .object_tree_views import ObjectTreeNode, build_by_file_nodes, friendly_item_type_label, is_element_unclassified
from .base_panel import BasePanel
from ui.context_menu import ContextMenu
from ui.theme import DARK_THEME, normalize_stylesheet
from ui.viewer_visibility_adapter import ViewerVisibilityAdapter


class _ByFileLabelDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(
        self,
        *,
        badge_role: int,
        depth_role: int,
        has_children_role: int,
        expanded_role: int,
        sublabel_role: int,
        selected_role: int,
        quick_can_role: int,
        quick_visible_role: int,
        quick_hover_role: int,
        checkbox_visible_role: int,
        checkbox_checked_role: int,
        parent: Optional[QtWidgets.QWidget] = None,
    ):
        super().__init__(parent)
        self._badge_role = int(badge_role)
        self._depth_role = int(depth_role)
        self._has_children_role = int(has_children_role)
        self._expanded_role = int(expanded_role)
        self._sublabel_role = int(sublabel_role)
        self._selected_role = int(selected_role)
        self._quick_can_role = int(quick_can_role)
        self._quick_visible_role = int(quick_visible_role)
        self._quick_hover_role = int(quick_hover_role)
        self._checkbox_visible_role = int(checkbox_visible_role)
        self._checkbox_checked_role = int(checkbox_checked_role)

    def paint(
        self,
        painter: QtGui.QPainter,
        option: QtWidgets.QStyleOptionViewItem,
        index: QtCore.QModelIndex,
    ) -> None:
        if int(index.column()) != 0:
            super().paint(painter, option, index)
            return

        opt = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        label = str(index.data(int(QtCore.Qt.DisplayRole)) or "").strip()
        sublabel = str(index.data(self._sublabel_role) or "").strip()
        badge_text = str(index.data(self._badge_role) or "").strip()
        depth = max(0, int(index.data(self._depth_role) or 0))
        has_children = bool(index.data(self._has_children_role))
        expanded = bool(index.data(self._expanded_role))
        selected = bool(index.data(self._selected_role))
        can_show_quick_actions = bool(index.data(self._quick_can_role))
        show_quick_actions = bool(index.data(self._quick_visible_role))
        quick_hover_action = str(index.data(self._quick_hover_role) or "").strip().lower()
        checkbox_visible = bool(index.data(self._checkbox_visible_role))
        checkbox_checked = bool(index.data(self._checkbox_checked_role))

        painter.save()
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        if selected:
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(QtGui.QColor(255, 59, 154, 42))
            painter.drawRoundedRect(QtCore.QRectF(opt.rect.adjusted(1, 2, -1, -2)), 6.0, 6.0)

        x = int(opt.rect.left()) + 8 + depth * 14
        y = int(opt.rect.top())
        h = int(opt.rect.height())
        right = int(opt.rect.right()) - 8

        if has_children:
            arrow_rect = QtCore.QRect(x, y + max(0, (h - 12) // 2), 11, 12)
            arrow_color = QtGui.QColor("#FFFFFF") if selected else QtGui.QColor(DARK_THEME.colors.text_secondary)
            painter.setPen(arrow_color)
            painter.setFont(opt.font)
            painter.drawText(arrow_rect, int(QtCore.Qt.AlignCenter), "▼" if expanded else "▶")
            x = arrow_rect.right() + 4
        elif checkbox_visible:
            checkbox_rect = QtCore.QRect(x, y + max(0, (h - 14) // 2), 14, 14)
            self._draw_checkbox(painter, checkbox_rect, checked=checkbox_checked, selected=selected)
            x = checkbox_rect.right() + 6

        quick_action_rects = self._quick_action_rects(opt.rect)
        if quick_action_rects:
            right = min(right, min(rect.left() for rect in quick_action_rects.values()) - 6)

        icon_obj = index.data(int(QtCore.Qt.DecorationRole))
        if isinstance(icon_obj, QtGui.QIcon):
            icon_rect = QtCore.QRect(x, y + max(0, (h - 14) // 2), 14, 14)
            icon_obj.paint(painter, icon_rect)
            x = icon_rect.right() + 6

        badge_font = QtGui.QFont(opt.font)
        badge_font.setPixelSize(11)
        badge_font.setWeight(QtGui.QFont.DemiBold)
        badge_h = 18
        badge_w = 26
        badge_gap = 6
        badge_rect = QtCore.QRect(right - badge_w, y + max(0, (h - badge_h) // 2), badge_w, badge_h)
        if badge_rect.left() > x + 10:
            right = badge_rect.left() - badge_gap
        else:
            badge_rect = QtCore.QRect()

        text_rect = QtCore.QRect(x, y + 3, max(8, right - x), max(8, h - 6))
        main_font = QtGui.QFont(opt.font)
        sub_font = QtGui.QFont(opt.font)
        main_font.setPixelSize(14)
        sub_font.setPixelSize(12)

        text_color = QtGui.QColor(DARK_THEME.colors.text_primary)
        sub_color = QtGui.QColor(DARK_THEME.colors.text_muted)
        if selected:
            text_color = QtGui.QColor("#FFFFFF")
            sub_color = QtGui.QColor(235, 235, 235, 196)

        painter.setPen(text_color)
        painter.setFont(main_font)
        if sublabel:
            main_rect = QtCore.QRect(text_rect.left(), text_rect.top(), text_rect.width(), min(17, text_rect.height()))
            painter.drawText(main_rect, int(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter), label)
            painter.setPen(sub_color)
            painter.setFont(sub_font)
            sub_rect = QtCore.QRect(text_rect.left(), text_rect.top() + 15, text_rect.width(), max(8, text_rect.height() - 15))
            painter.drawText(sub_rect, int(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter), sublabel)
        else:
            painter.drawText(text_rect, int(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter), label)

        if badge_text and badge_rect.isValid():
            badge_bg = QtGui.QColor(DARK_THEME.colors.text_muted)
            badge_bg.setAlpha(22)
            selected_badge_bg = QtGui.QColor(DARK_THEME.colors.text_secondary)
            selected_badge_bg.setAlpha(42)
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(badge_bg if not selected else selected_badge_bg)
            painter.drawRoundedRect(QtCore.QRectF(badge_rect), 8.0, 8.0)
            painter.setFont(badge_font)
            badge_text_color = QtGui.QColor(DARK_THEME.colors.text_muted)
            badge_text_color.setAlpha(178)
            selected_badge_text_color = QtGui.QColor(DARK_THEME.colors.text_primary)
            selected_badge_text_color.setAlpha(220)
            painter.setPen(badge_text_color if not selected else selected_badge_text_color)
            painter.drawText(badge_rect, int(QtCore.Qt.AlignCenter), badge_text)

        if can_show_quick_actions and quick_action_rects and show_quick_actions:
            base_color = QtGui.QColor("#FFFFFF") if selected else QtGui.QColor(DARK_THEME.colors.text_secondary)
            hover_color = QtGui.QColor("#FFFFFF") if selected else QtGui.QColor(DARK_THEME.colors.accent)
            hide_color = hover_color if quick_hover_action == "hide" else base_color
            isolate_color = hover_color if quick_hover_action == "isolate" else base_color
            self._draw_hide_icon(painter, quick_action_rects["hide"], hide_color)
            self._draw_isolate_icon(painter, quick_action_rects["isolate"], isolate_color)
        painter.restore()

    def _quick_action_rects(
        self,
        rect: QtCore.QRect,
    ) -> Dict[str, QtCore.QRect]:
        right = int(rect.right()) - 8
        icon_size = 14
        icon_gap = 6
        actions_width = (icon_size * 2) + icon_gap
        actions_left = right - actions_width + 1
        top = int(rect.top()) + max(0, (int(rect.height()) - icon_size) // 2)
        hide = QtCore.QRect(actions_left, top, icon_size, icon_size)
        isolate = QtCore.QRect(hide.right() + icon_gap, top, icon_size, icon_size)
        min_left = int(rect.left()) + 22
        if hide.left() <= min_left:
            return {}
        return {"hide": hide, "isolate": isolate}

    def _draw_hide_icon(self, painter: QtGui.QPainter, rect: QtCore.QRect, color: QtGui.QColor) -> None:
        painter.save()
        pen = QtGui.QPen(color, 1.4)
        pen.setCapStyle(QtCore.Qt.RoundCap)
        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.NoBrush)
        eye_rect = rect.adjusted(1, 3, -1, -3)
        painter.drawEllipse(eye_rect)
        pupil = QtCore.QRectF(
            float(rect.center().x()) - 1.7,
            float(rect.center().y()) - 1.7,
            3.4,
            3.4,
        )
        painter.setBrush(color)
        painter.drawEllipse(pupil)
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.drawLine(
            QtCore.QPointF(float(rect.left()) + 1.5, float(rect.bottom()) - 1.5),
            QtCore.QPointF(float(rect.right()) - 1.5, float(rect.top()) + 1.5),
        )
        painter.restore()

    def _draw_isolate_icon(self, painter: QtGui.QPainter, rect: QtCore.QRect, color: QtGui.QColor) -> None:
        painter.save()
        pen = QtGui.QPen(color, 1.3)
        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.NoBrush)
        frame = QtCore.QRectF(
            float(rect.left()) + 1.0,
            float(rect.top()) + 1.0,
            float(rect.width()) - 2.0,
            float(rect.height()) - 2.0,
        )
        painter.drawRoundedRect(frame, 2.5, 2.5)
        center = QtCore.QRectF(
            float(rect.center().x()) - 1.8,
            float(rect.center().y()) - 1.8,
            3.6,
            3.6,
        )
        painter.setBrush(color)
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawEllipse(center)
        painter.restore()

    def _draw_checkbox(self, painter: QtGui.QPainter, rect: QtCore.QRect, *, checked: bool, selected: bool) -> None:
        painter.save()
        border = QtGui.QColor("#FFFFFF") if selected else QtGui.QColor(DARK_THEME.colors.border_soft)
        border.setAlpha(190 if selected else 210)
        fill = QtGui.QColor(255, 59, 154, 210) if checked else QtGui.QColor(255, 255, 255, 10)
        painter.setPen(QtGui.QPen(border, 1.1))
        painter.setBrush(fill)
        painter.drawRoundedRect(QtCore.QRectF(rect), 3.0, 3.0)
        if checked:
            check_color = QtGui.QColor("#FFFFFF")
            pen = QtGui.QPen(check_color, 1.8)
            pen.setCapStyle(QtCore.Qt.RoundCap)
            pen.setJoinStyle(QtCore.Qt.RoundJoin)
            painter.setPen(pen)
            p1 = QtCore.QPointF(float(rect.left()) + 3.2, float(rect.center().y()) + 0.5)
            p2 = QtCore.QPointF(float(rect.left()) + 6.0, float(rect.bottom()) - 3.6)
            p3 = QtCore.QPointF(float(rect.right()) - 3.1, float(rect.top()) + 3.4)
            painter.drawLine(p1, p2)
            painter.drawLine(p2, p3)
        painter.restore()


class _ByFileTypeDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(
        self,
        *,
        selected_role: int,
        parent: Optional[QtWidgets.QWidget] = None,
    ):
        super().__init__(parent)
        self._selected_role = int(selected_role)

    def paint(
        self,
        painter: QtGui.QPainter,
        option: QtWidgets.QStyleOptionViewItem,
        index: QtCore.QModelIndex,
    ) -> None:
        if int(index.column()) != 1:
            super().paint(painter, option, index)
            return

        opt = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        opt.text = str(index.data(int(QtCore.Qt.DisplayRole)) or "").strip()
        type_font = QtGui.QFont(opt.font)
        type_font.setPixelSize(12)
        opt.font = type_font

        selected = bool(index.data(self._selected_role))
        if opt.text:
            muted = QtGui.QColor(232, 236, 246, 220) if selected else QtGui.QColor(DARK_THEME.colors.text_muted)
            opt.palette.setColor(QtGui.QPalette.Text, muted)
            opt.palette.setColor(QtGui.QPalette.HighlightedText, muted)

        style = opt.widget.style() if opt.widget is not None else QtWidgets.QApplication.style()
        style.drawControl(QtWidgets.QStyle.CE_ItemViewItem, opt, painter, opt.widget)


@dataclass
class _VirtualTreeNode:
    node_id: str
    columns: Tuple[str, str, str, str]
    sub_label: str
    tooltip: str
    element_ids: Tuple[str, ...]
    primary_guid: str
    badge_text: str
    icon: QtGui.QIcon = field(default_factory=QtGui.QIcon)
    children: List["_VirtualTreeNode"] = field(default_factory=list)
    parent: Optional["_VirtualTreeNode"] = None
    expanded: bool = False
    filtered_out: bool = False


@dataclass(frozen=True)
class _VirtualVisibleRow:
    node_id: str
    depth: int


class _VirtualByFileTableModel(QtCore.QAbstractTableModel):
    _ROLE_NODE_ID = int(QtCore.Qt.UserRole) + 50
    _ROLE_DEPTH = int(QtCore.Qt.UserRole) + 51
    _ROLE_BADGE_TEXT = int(QtCore.Qt.UserRole) + 52
    _ROLE_HAS_CHILDREN = int(QtCore.Qt.UserRole) + 53
    _ROLE_EXPANDED = int(QtCore.Qt.UserRole) + 54
    _ROLE_SUBLABEL = int(QtCore.Qt.UserRole) + 55
    _ROLE_SELECTED = int(QtCore.Qt.UserRole) + 56
    _ROLE_SHOW_QUICK_ACTIONS = int(QtCore.Qt.UserRole) + 57
    _ROLE_QUICK_HOVER_ACTION = int(QtCore.Qt.UserRole) + 58
    _ROLE_CAN_QUICK_ACTIONS = int(QtCore.Qt.UserRole) + 59
    _ROLE_CHECKBOX_VISIBLE = int(QtCore.Qt.UserRole) + 60
    _ROLE_CHECKBOX_CHECKED = int(QtCore.Qt.UserRole) + 61

    def __init__(self, parent: Optional[QtCore.QObject] = None):
        super().__init__(parent)
        self._rows: List[_VirtualVisibleRow] = []
        self._nodes_by_id: Dict[str, _VirtualTreeNode] = {}
        self._selected_ids: Set[str] = set()
        self._hovered_node_id = ""
        self._hovered_action = ""
        self._indent = 14
        self._sort_column = -1
        self._sort_direction = 0

    def update_window(
        self,
        rows: Sequence[_VirtualVisibleRow],
        *,
        nodes_by_id: Dict[str, _VirtualTreeNode],
        selected_ids: Set[str],
        hovered_node_id: str,
        hovered_action: str,
    ) -> None:
        self.beginResetModel()
        self._rows = list(rows)
        self._nodes_by_id = dict(nodes_by_id)
        self._selected_ids = set(selected_ids)
        self._hovered_node_id = str(hovered_node_id or "")
        self._hovered_action = str(hovered_action or "")
        self.endResetModel()

    def set_hover_state(self, node_id: str, action: str) -> None:
        normalized_id = str(node_id or "")
        normalized_action = str(action or "")
        if normalized_id == self._hovered_node_id and normalized_action == self._hovered_action:
            return
        self._hovered_node_id = normalized_id
        self._hovered_action = normalized_action
        if not self._rows:
            return
        top_left = self.index(0, 0)
        bottom_right = self.index(max(0, len(self._rows) - 1), 0)
        self.dataChanged.emit(
            top_left,
            bottom_right,
            [self._ROLE_SHOW_QUICK_ACTIONS, self._ROLE_QUICK_HOVER_ACTION],
        )

    def set_selected_ids(self, selected_ids: Set[str]) -> None:
        normalized = set(str(value or "").strip() for value in set(selected_ids or set()) if str(value or "").strip())
        if normalized == self._selected_ids:
            return
        self._selected_ids = normalized
        if not self._rows:
            return
        top_left = self.index(0, 0)
        bottom_right = self.index(max(0, len(self._rows) - 1), max(0, self.columnCount() - 1))
        self.dataChanged.emit(
            top_left,
            bottom_right,
            [
                int(QtCore.Qt.BackgroundRole),
                int(QtCore.Qt.ForegroundRole),
                self._ROLE_SELECTED,
                self._ROLE_SHOW_QUICK_ACTIONS,
            ],
        )

    def rowCount(self, _parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        return len(self._rows)

    def columnCount(self, _parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        return 4

    def headerData(self, section: int, orientation: QtCore.Qt.Orientation, role: int = int(QtCore.Qt.DisplayRole)):
        if orientation != QtCore.Qt.Horizontal:
            return None
        labels = ("Object", "Type", "System", "GlobalId")
        idx = int(section)
        if idx < 0 or idx >= len(labels):
            return None
        is_active = idx == int(self._sort_column) and int(self._sort_direction) != 0
        if role == int(QtCore.Qt.DisplayRole):
            label = labels[idx]
            if is_active:
                arrow = "▲" if int(self._sort_direction) > 0 else "▼"
                return f"{label} {arrow}"
            return label
        if role == int(QtCore.Qt.FontRole):
            if not is_active:
                return None
            font = QtGui.QFont()
            font.setBold(True)
            return font
        if role == int(QtCore.Qt.ForegroundRole):
            if is_active:
                return QtGui.QColor(DARK_THEME.colors.accent)
            return QtGui.QColor(DARK_THEME.colors.text_secondary)
        return None

    def set_sort_state(self, *, column: int, direction: int) -> None:
        next_column = int(column)
        if next_column < 0 or next_column >= self.columnCount():
            next_column = -1
        next_direction = int(direction)
        if next_column < 0:
            next_direction = 0
        if next_direction not in (-1, 0, 1):
            next_direction = 0
        if next_direction == 0:
            next_column = -1
        if next_column == self._sort_column and next_direction == self._sort_direction:
            return
        self._sort_column = next_column
        self._sort_direction = next_direction
        self.headerDataChanged.emit(QtCore.Qt.Horizontal, 0, max(0, self.columnCount() - 1))

    def data(self, index: QtCore.QModelIndex, role: int = int(QtCore.Qt.DisplayRole)):
        if not index.isValid():
            return None
        row_index = int(index.row())
        if row_index < 0 or row_index >= len(self._rows):
            return None
        row = self._rows[row_index]
        node = self._nodes_by_id.get(row.node_id)
        if node is None:
            return None
        col = int(index.column())

        if role == int(QtCore.Qt.DisplayRole):
            # Presentation rule: only show "Type" values on leaf rows.
            if col == 1 and bool(node.children):
                return ""
            return node.columns[col]

        if role == int(QtCore.Qt.DecorationRole) and col == 0:
            if node.children:
                style = QtWidgets.QApplication.style()
                return style.standardIcon(QtWidgets.QStyle.SP_DirOpenIcon if node.expanded else QtWidgets.QStyle.SP_DirClosedIcon)
            if not node.icon.isNull():
                return node.icon

        if role == int(QtCore.Qt.ToolTipRole):
            return node.tooltip

        if role == int(QtCore.Qt.BackgroundRole) and node.node_id in self._selected_ids:
            return QtGui.QColor(255, 59, 154, 34)

        if role == int(QtCore.Qt.ForegroundRole):
            if node.node_id in self._selected_ids:
                return QtGui.QColor("#FFFFFF")
            return QtGui.QColor(DARK_THEME.colors.text_primary)

        if role == self._ROLE_NODE_ID:
            return node.node_id
        if role == self._ROLE_DEPTH:
            return int(row.depth)
        if role == self._ROLE_BADGE_TEXT and col == 0:
            return str(node.badge_text or "")
        if role == self._ROLE_HAS_CHILDREN and col == 0:
            return bool(node.children)
        if role == self._ROLE_EXPANDED and col == 0:
            return bool(node.expanded)
        if role == self._ROLE_SUBLABEL and col == 0:
            return str(node.sub_label or "")
        if role == self._ROLE_SELECTED:
            return bool(node.node_id in self._selected_ids)
        if role == self._ROLE_CAN_QUICK_ACTIONS and col == 0:
            return bool(node.element_ids)
        if role == self._ROLE_CHECKBOX_VISIBLE and col == 0:
            return bool((not node.children) and str(node.primary_guid or "").strip())
        if role == self._ROLE_CHECKBOX_CHECKED and col == 0:
            return bool(node.node_id in self._selected_ids)
        if role == self._ROLE_SHOW_QUICK_ACTIONS and col == 0:
            return bool(
                node.element_ids
                and (node.node_id == self._hovered_node_id or node.node_id in self._selected_ids)
            )
        if role == self._ROLE_QUICK_HOVER_ACTION and col == 0:
            if node.node_id != self._hovered_node_id:
                return ""
            return str(self._hovered_action or "")
        return None


class _VirtualizedByFileTree(QtWidgets.QWidget):
    selectionChanged = QtCore.Signal()
    customContextMenuRequested = QtCore.Signal(QtCore.QPoint)
    quickActionRequested = QtCore.Signal(str, object)
    sortChanged = QtCore.Signal(int, int)

    def __init__(
        self,
        *,
        row_height: int = 32,
        overscan: int = 8,
        parent: Optional[QtWidgets.QWidget] = None,
    ):
        super().__init__(parent)
        self._row_height = max(18, int(row_height))
        self._overscan = max(2, int(overscan))
        self._filter_pattern = ""
        self._suppress_selection = False
        self._roots: List[_VirtualTreeNode] = []
        self._flat_rows: List[_VirtualVisibleRow] = []
        self._nodes_by_id: Dict[str, _VirtualTreeNode] = {}
        self._guid_to_node_ids: Dict[str, List[str]] = {}
        self._primary_guid_to_node_id: Dict[str, str] = {}
        self._selected_node_ids: List[str] = []
        self._sort_column = -1
        self._sort_direction = 0
        self._smart_sort_enabled = False
        self._group_folders_first = True
        self._original_order_by_node_id: Dict[str, int] = {}
        self._next_original_order = 0
        self._smart_flagged_node_ids: Set[str] = set()
        self._smart_active_search_node_ids: Set[str] = set()
        self._window_start = 0
        self._hovered_node_id = ""
        self._hovered_action = ""
        self._suppress_next_row_click_selection = False
        self._selection_anchor_node_id = ""
        self._tooltip_delay_ms = 350
        self._tooltip_pending_text = ""
        self._tooltip_pending_global_pos = QtCore.QPoint()
        self._tooltip_timer = QtCore.QTimer(self)
        self._tooltip_timer.setSingleShot(True)
        self._tooltip_timer.setInterval(self._tooltip_delay_ms)
        self._tooltip_timer.timeout.connect(self._show_pending_tooltip)
        self._scroll_animation = QtCore.QPropertyAnimation(self)
        self._scroll_animation.setTargetObject(None)
        self._scroll_animation.setPropertyName(b"")

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self._table = QtWidgets.QTableView(self)
        self._model = _VirtualByFileTableModel(self._table)
        self._table.setModel(self._model)
        self._table.setObjectName("ByFileTree")
        self._table.verticalHeader().hide()
        self._table.verticalHeader().setDefaultSectionSize(self._row_height)
        self._table.horizontalHeader().setStretchLastSection(False)
        self._table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        self._table.horizontalHeader().setMinimumSectionSize(72)
        self._table.horizontalHeader().setCascadingSectionResizes(True)
        self._table.horizontalHeader().setSectionsClickable(True)
        self._table.setSortingEnabled(False)
        self._table.setShowGrid(False)
        self._table.setAlternatingRowColors(False)
        self._table.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self._table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self._table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self._table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self._table.setHorizontalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self._table.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self._table.setMouseTracking(True)
        self._table.viewport().setMouseTracking(True)
        self._table.viewport().installEventFilter(self)
        self._table.clicked.connect(self._on_table_clicked)
        self._table.doubleClicked.connect(self._on_table_double_clicked)
        self._table.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._emit_context_menu_requested)
        self._table.horizontalHeader().sectionClicked.connect(self._on_header_section_clicked)

        self._scroll = QtWidgets.QScrollBar(QtCore.Qt.Vertical, self)
        self._scroll.setSingleStep(1)
        self._scroll.valueChanged.connect(self._refresh_window)
        layout.addWidget(self._table, 1)
        layout.addWidget(self._scroll, 0)

    def header(self) -> QtWidgets.QHeaderView:
        return self._table.horizontalHeader()

    def viewport(self) -> QtWidgets.QWidget:
        return self._table.viewport()

    def scroll_value(self) -> int:
        return int(self._scroll.value())

    def set_scroll_value(self, value: int) -> None:
        self._stop_scroll_animation()
        target = max(0, int(value))
        if target > int(self._scroll.maximum()):
            target = int(self._scroll.maximum())
        self._scroll.setValue(target)

    def setColumnWidth(self, column: int, width: int) -> None:
        self._table.setColumnWidth(int(column), int(width))

    def columnWidth(self, column: int) -> int:
        return int(self._table.columnWidth(int(column)))

    def setItemDelegateForColumn(self, column: int, delegate: QtWidgets.QAbstractItemDelegate) -> None:
        self._table.setItemDelegateForColumn(int(column), delegate)

    def sort_state(self) -> Tuple[int, int]:
        return int(self._sort_column), int(self._sort_direction)

    def smart_sort_enabled(self) -> bool:
        return bool(self._smart_sort_enabled)

    def group_folders_first(self) -> bool:
        return bool(self._group_folders_first)

    def set_smart_sort_enabled(self, enabled: bool) -> None:
        wanted = bool(enabled)
        if wanted == self._smart_sort_enabled:
            return
        self._smart_sort_enabled = wanted
        self._refresh_flat_rows()
        self._refresh_window()

    def set_sort_state(self, *, column: int, direction: int, emit_signal: bool) -> None:
        next_column = int(column)
        if next_column < 0 or next_column >= self._model.columnCount():
            next_column = -1
        next_direction = int(direction)
        if next_column < 0:
            next_direction = 0
        if next_direction not in (-1, 0, 1):
            next_direction = 0
        if next_direction == 0:
            next_column = -1
        if next_column == self._sort_column and next_direction == self._sort_direction:
            return
        self._sort_column = next_column
        self._sort_direction = next_direction
        self._model.set_sort_state(column=self._sort_column, direction=self._sort_direction)
        self._refresh_flat_rows()
        self._refresh_window()
        if emit_signal:
            self.sortChanged.emit(int(self._sort_column), int(self._sort_direction))

    def set_group_folders_first(self, enabled: bool) -> None:
        wanted = bool(enabled)
        if wanted == self._group_folders_first:
            return
        self._group_folders_first = wanted
        self._refresh_flat_rows()
        self._refresh_window()

    def set_smart_context(self, *, flagged_guids: Set[str], active_search_guids: Set[str]) -> None:
        flagged = set(str(v or "").strip() for v in set(flagged_guids or set()) if str(v or "").strip())
        active = set(str(v or "").strip() for v in set(active_search_guids or set()) if str(v or "").strip())

        flagged_node_ids: Set[str] = set()
        for guid in flagged:
            for node_id in list(self._guid_to_node_ids.get(guid, [])):
                current = str(node_id or "").strip()
                if current:
                    flagged_node_ids.add(current)

        active_node_ids: Set[str] = set()
        for guid in active:
            for node_id in list(self._guid_to_node_ids.get(guid, [])):
                current = str(node_id or "").strip()
                if current:
                    active_node_ids.add(current)

        if flagged_node_ids == self._smart_flagged_node_ids and active_node_ids == self._smart_active_search_node_ids:
            return
        self._smart_flagged_node_ids = flagged_node_ids
        self._smart_active_search_node_ids = active_node_ids
        if self._smart_sort_enabled:
            self._refresh_flat_rows()
            self._refresh_window()

    def set_tree(self, roots: Sequence[_VirtualTreeNode]) -> None:
        self._roots = list(roots or [])
        self._nodes_by_id = {}
        self._guid_to_node_ids = {}
        self._primary_guid_to_node_id = {}
        self._smart_flagged_node_ids = set()
        self._smart_active_search_node_ids = set()
        self._original_order_by_node_id = {}
        self._next_original_order = 0
        for root in self._roots:
            self._index_node(root)
        self._apply_filter()
        self._refresh_flat_rows()
        self._reconcile_selection()
        self._refresh_window()

    def set_filter(self, pattern: str) -> None:
        self._filter_pattern = str(pattern or "").strip().lower()
        self._apply_filter()
        self._refresh_flat_rows()
        self._refresh_window()

    def set_expansion_depth(self, levels: int) -> None:
        max_levels = max(0, int(levels))
        for root in self._roots:
            self._set_node_expansion_depth(root, current_level=1, max_level=max_levels)
        self._refresh_flat_rows()
        self._refresh_window()

    def collapse_all(self) -> None:
        for root in self._roots:
            self._set_node_expansion_depth(root, current_level=1, max_level=0)
        self._refresh_flat_rows()
        self._refresh_window()

    def expand_selection_path(self) -> None:
        selected = list(self._selected_node_ids)
        if not selected:
            self.set_expansion_depth(2)
            return
        self.collapse_all()
        for node_id in selected:
            node = self._nodes_by_id.get(node_id)
            while node is not None and node.parent is not None:
                node.parent.expanded = True
                node = node.parent
            selected_node = self._nodes_by_id.get(node_id)
            if selected_node is not None and selected_node.children:
                selected_node.expanded = True
        self._refresh_flat_rows()
        self._refresh_window()
        self.scroll_to_selected(center=True)

    def selected_element_ids(self) -> List[str]:
        guids: List[str] = []
        for node_id in list(self._selected_node_ids):
            node = self._nodes_by_id.get(node_id)
            if not self._is_selectable_node(node):
                continue
            for guid in self._node_selection_element_ids(node):
                if guid in guids:
                    continue
                guids.append(guid)
        return guids

    def element_ids_at(self, pos: QtCore.QPoint) -> List[str]:
        node = self.node_at(pos)
        if node is None:
            return []
        return [str(g) for g in node.element_ids if str(g).strip()]

    def selected_nodes(self) -> List[_VirtualTreeNode]:
        rows: List[_VirtualTreeNode] = []
        for node_id in self._selected_node_ids:
            node = self._nodes_by_id.get(node_id)
            if node is not None:
                rows.append(node)
        return rows

    def node_at(self, pos: QtCore.QPoint) -> Optional[_VirtualTreeNode]:
        index = self._table.indexAt(pos)
        if not index.isValid():
            return None
        row = int(index.row())
        if row < 0:
            return None
        offset = self._window_start + row
        if offset < 0 or offset >= len(self._flat_rows):
            return None
        row_ref = self._flat_rows[offset]
        return self._nodes_by_id.get(row_ref.node_id)

    def clearSelection(self) -> None:
        self._set_selected_node_ids([], emit_signal=False)
        self._selection_anchor_node_id = ""

    def sync_selected_guids(self, guids: Sequence[str], *, scroll_to_first: bool) -> None:
        normalized: List[str] = []
        for guid in list(guids or []):
            current = str(guid or "").strip()
            if not current or current in normalized:
                continue
            if current not in self._guid_to_node_ids:
                continue
            normalized.append(current)
        selected_node_ids: List[str] = []
        for guid in normalized:
            preferred = str(self._primary_guid_to_node_id.get(guid, "") or "").strip()
            if preferred:
                node_id = preferred
            else:
                node_ids = self._guid_to_node_ids.get(guid, [])
                if not node_ids:
                    continue
                node_id = str(node_ids[0] or "").strip()
            if not node_id:
                continue
            node = self._nodes_by_id.get(node_id)
            if not self._is_selectable_node(node):
                continue
            if scroll_to_first:
                while node is not None and node.parent is not None:
                    if not bool(node.parent.expanded):
                        node.parent.expanded = True
                    node = node.parent
            if node_id not in selected_node_ids:
                selected_node_ids.append(node_id)
        self._set_selected_node_ids(selected_node_ids, emit_signal=False)
        self._selection_anchor_node_id = self._selected_node_ids[0] if self._selected_node_ids else ""
        if scroll_to_first:
            self._refresh_flat_rows()
            self._refresh_window()
        if scroll_to_first and self._selected_node_ids:
            self.scroll_to_selected(center=True)

    def scroll_to_selected(self, *, center: bool) -> None:
        if not self._selected_node_ids:
            return
        target_id = self._selected_node_ids[0]
        for idx, row in enumerate(self._flat_rows):
            if row.node_id != target_id:
                continue
            visible = self._visible_row_capacity()
            if center:
                top = max(0, int(idx - max(1, visible // 2)))
            else:
                top = int(idx)
            target_value = min(int(self._scroll.maximum()), int(top))
            self._animate_scroll_to(target_value)
            return

    def _stop_scroll_animation(self) -> None:
        if self._scroll_animation.state() == QtCore.QAbstractAnimation.Running:
            self._scroll_animation.stop()

    def _animate_scroll_to(self, target_value: int) -> None:
        target = max(0, int(target_value))
        current = int(self._scroll.value())
        if target == current:
            return
        distance = abs(target - current)
        if distance <= 2:
            self._scroll.setValue(target)
            return
        duration = max(120, min(300, 110 + distance * 14))
        self._stop_scroll_animation()
        self._scroll_animation.setTargetObject(self._scroll)
        self._scroll_animation.setPropertyName(b"value")
        self._scroll_animation.setStartValue(current)
        self._scroll_animation.setEndValue(target)
        self._scroll_animation.setDuration(int(duration))
        self._scroll_animation.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self._scroll_animation.start()

    def eventFilter(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if watched is self._table.viewport():
            event_type = int(event.type())
            if event_type == int(QtCore.QEvent.Resize):
                self._refresh_window()
            elif event_type == int(QtCore.QEvent.MouseMove):
                move = event  # type: ignore[assignment]
                if isinstance(move, QtGui.QMouseEvent):
                    self._update_hover_state(move.position().toPoint())
                    self._schedule_delayed_tooltip(move.position().toPoint())
            elif event_type == int(QtCore.QEvent.Wheel):
                wheel = event  # type: ignore[assignment]
                if isinstance(wheel, QtGui.QWheelEvent):
                    self._stop_scroll_animation()
                    self._clear_pending_tooltip(hide_visible=True)
                    delta = int(wheel.angleDelta().y())
                    if delta != 0:
                        steps = -1 if delta < 0 else 1
                        self._scroll.setValue(self._scroll.value() - steps * 3)
                        return True
            elif event_type == int(QtCore.QEvent.MouseButtonPress):
                self._stop_scroll_animation()
                self._clear_pending_tooltip(hide_visible=True)
                press = event  # type: ignore[assignment]
                if isinstance(press, QtGui.QMouseEvent):
                    if press.button() == QtCore.Qt.LeftButton:
                        pos = press.position().toPoint()
                        if not self._table.indexAt(pos).isValid():
                            self._set_selected_node_ids([], emit_signal=True)
                            self._selection_anchor_node_id = ""
                            return True
                        checkbox_node_id = self._checkbox_hit_node_id(pos)
                        if checkbox_node_id:
                            self._toggle_checkbox_selection(checkbox_node_id)
                            self._suppress_next_row_click_selection = True
                            return True
                        handled_quick = self._trigger_quick_action_at(pos)
                        if handled_quick:
                            return True
                        if self._toggle_if_expander_hit(pos):
                            self._suppress_next_row_click_selection = True
                            return True
            elif event_type == int(QtCore.QEvent.MouseButtonRelease):
                release = event  # type: ignore[assignment]
                if isinstance(release, QtGui.QMouseEvent):
                    if release.button() == QtCore.Qt.LeftButton and self._suppress_next_row_click_selection:
                        self._suppress_next_row_click_selection = False
                        return True
            elif event_type == int(QtCore.QEvent.ToolTip):
                # Replace default immediate tooltip with delayed custom tooltip.
                return True
            elif event_type in (int(QtCore.QEvent.Leave), int(QtCore.QEvent.HoverLeave)):
                self._set_hover_state("", "")
                self._table.viewport().unsetCursor()
                self._clear_pending_tooltip(hide_visible=True)
        return super().eventFilter(watched, event)

    def _schedule_delayed_tooltip(self, pos: QtCore.QPoint) -> None:
        index = self._table.indexAt(pos)
        node = self.node_at(pos)
        if not index.isValid() or node is None:
            self._clear_pending_tooltip(hide_visible=True)
            return
        text = str(node.tooltip or "").strip()
        if not text:
            self._clear_pending_tooltip(hide_visible=True)
            return
        row_rect = self._table.visualRect(index)
        anchor_local = QtCore.QPoint(
            int(self._table.viewport().width()) + 16,
            max(8, int(row_rect.center().y())),
        )
        global_pos = self._table.viewport().mapToGlobal(anchor_local)
        if text == self._tooltip_pending_text and global_pos == self._tooltip_pending_global_pos and self._tooltip_timer.isActive():
            return
        self._tooltip_pending_text = text
        self._tooltip_pending_global_pos = global_pos
        self._tooltip_timer.start()

    def _show_pending_tooltip(self) -> None:
        text = str(self._tooltip_pending_text or "").strip()
        if not text:
            return
        QtWidgets.QToolTip.showText(self._tooltip_pending_global_pos, text, self._table.viewport())

    def _clear_pending_tooltip(self, *, hide_visible: bool) -> None:
        self._tooltip_timer.stop()
        self._tooltip_pending_text = ""
        self._tooltip_pending_global_pos = QtCore.QPoint()
        if hide_visible:
            QtWidgets.QToolTip.hideText()

    def _update_hover_state(self, pos: QtCore.QPoint) -> None:
        index = self._table.indexAt(pos)
        if not index.isValid():
            self._set_hover_state("", "")
            self._table.viewport().unsetCursor()
            return
        node = self.node_at(pos)
        if node is None or not node.element_ids:
            self._set_hover_state("", "")
            self._table.viewport().unsetCursor()
            return
        action = ""
        if int(index.column()) == 0:
            _, action = self._quick_action_hit_test(pos, visible_only=False)
        self._set_hover_state(node.node_id, action)
        if action:
            self._table.viewport().setCursor(QtCore.Qt.PointingHandCursor)
        else:
            self._table.viewport().unsetCursor()

    def _set_hover_state(self, node_id: str, action: str) -> None:
        normalized_id = str(node_id or "")
        normalized_action = str(action or "")
        if normalized_id == self._hovered_node_id and normalized_action == self._hovered_action:
            return
        self._hovered_node_id = normalized_id
        self._hovered_action = normalized_action
        self._model.set_hover_state(normalized_id, normalized_action)

    def _trigger_quick_action_at(self, pos: QtCore.QPoint) -> bool:
        node, action = self._quick_action_hit_test(pos, visible_only=True)
        if node is None or not action:
            return False
        ids = [str(g) for g in list(node.element_ids or ()) if str(g).strip()]
        if not ids:
            return False
        self.quickActionRequested.emit(action, ids)
        return True

    def _quick_action_hit_test(self, pos: QtCore.QPoint, *, visible_only: bool) -> Tuple[Optional[_VirtualTreeNode], str]:
        index = self._table.indexAt(pos)
        if not index.isValid() or int(index.column()) != 0:
            return None, ""
        node = self.node_at(pos)
        if node is None or not node.element_ids:
            return None, ""
        if visible_only and not self._can_show_quick_actions(node):
            return node, ""
        rects = self._quick_action_rects(index, node)
        if not rects:
            return node, ""
        point = QtCore.QPoint(int(pos.x()), int(pos.y()))
        if rects["hide"].contains(point):
            return node, "hide"
        if rects["isolate"].contains(point):
            return node, "isolate"
        return node, ""

    def _can_show_quick_actions(self, node: _VirtualTreeNode) -> bool:
        if not node.element_ids:
            return False
        if node.node_id == self._hovered_node_id:
            return True
        return node.node_id in self._selected_node_ids

    def _quick_action_rects(
        self,
        index: QtCore.QModelIndex,
        node: _VirtualTreeNode,
    ) -> Dict[str, QtCore.QRect]:
        rect = self._table.visualRect(index)
        if not rect.isValid():
            return {}
        right = int(rect.right()) - 8
        icon_size = 14
        icon_gap = 6
        actions_width = (icon_size * 2) + icon_gap
        actions_left = right - actions_width + 1
        top = int(rect.top()) + max(0, (int(rect.height()) - icon_size) // 2)
        hide = QtCore.QRect(actions_left, top, icon_size, icon_size)
        isolate = QtCore.QRect(hide.right() + icon_gap, top, icon_size, icon_size)
        min_left = int(rect.left()) + 22
        if hide.left() <= min_left:
            return {}
        return {"hide": hide, "isolate": isolate}

    def _checkbox_hit_node_id(self, pos: QtCore.QPoint) -> str:
        index = self._table.indexAt(pos)
        if not index.isValid() or int(index.column()) != 0:
            return ""
        row = int(index.row())
        offset = self._window_start + row
        if offset < 0 or offset >= len(self._flat_rows):
            return ""
        row_ref = self._flat_rows[offset]
        node = self._nodes_by_id.get(row_ref.node_id)
        if not self._is_checkbox_node(node):
            return ""
        hit_rect = self._checkbox_hit_rect(index, depth=int(row_ref.depth))
        if not hit_rect.contains(QtCore.QPoint(int(pos.x()), int(pos.y()))):
            return ""
        return str(row_ref.node_id or "")

    def _checkbox_hit_rect(self, index: QtCore.QModelIndex, *, depth: int) -> QtCore.QRect:
        row_rect = self._table.visualRect(index)
        box_left = int(row_rect.left()) + 8 + max(0, int(depth)) * 14
        box_top = int(row_rect.top()) + max(0, (int(row_rect.height()) - 14) // 2)
        # Slightly larger hit target than paint rect for easier clicking.
        return QtCore.QRect(box_left - 2, box_top - 2, 18, 18)

    def _toggle_checkbox_selection(self, node_id: str) -> None:
        target = str(node_id or "").strip()
        if not target:
            return
        next_selected = list(self._selected_node_ids)
        if target in next_selected:
            next_selected.remove(target)
        else:
            next_selected.append(target)
        self._selection_anchor_node_id = target
        self._set_selected_node_ids(next_selected, emit_signal=True)

    def _toggle_if_expander_hit(self, pos: QtCore.QPoint) -> bool:
        index = self._table.indexAt(pos)
        if not index.isValid() or int(index.column()) != 0:
            return False
        row = int(index.row())
        offset = self._window_start + row
        if offset < 0 or offset >= len(self._flat_rows):
            return False
        row_ref = self._flat_rows[offset]
        node = self._nodes_by_id.get(row_ref.node_id)
        if node is None or not node.children:
            return False
        hit_rect = self._expander_hit_rect(index, depth=int(row_ref.depth))
        if not hit_rect.contains(QtCore.QPoint(int(pos.x()), int(pos.y()))):
            return False
        node.expanded = not bool(node.expanded)
        self._refresh_flat_rows()
        self._refresh_window()
        return True

    def _on_header_section_clicked(self, section: int) -> None:
        col = int(section)
        if self._smart_sort_enabled:
            self._smart_sort_enabled = False
        current_col, current_dir = self.sort_state()
        if col != current_col:
            self.set_sort_state(column=col, direction=1, emit_signal=True)
            return
        if current_dir > 0:
            self.set_sort_state(column=col, direction=-1, emit_signal=True)
            return
        if current_dir < 0:
            self.set_sort_state(column=-1, direction=0, emit_signal=True)
            return
        self.set_sort_state(column=col, direction=1, emit_signal=True)

    def _expander_hit_rect(self, index: QtCore.QModelIndex, *, depth: int) -> QtCore.QRect:
        row_rect = self._table.visualRect(index)
        icon_left = 8 + max(0, int(depth)) * 14
        icon_top = int(row_rect.top()) + max(0, (int(row_rect.height()) - 12) // 2)
        # Keep expander hit target tight to the arrow glyph so label clicks only select.
        return QtCore.QRect(icon_left - 1, icon_top - 1, 13, 14)

    def _emit_context_menu_requested(self, pos: QtCore.QPoint) -> None:
        self.customContextMenuRequested.emit(pos)

    def _on_table_double_clicked(self, index: QtCore.QModelIndex) -> None:
        # Keep row interactions selection-only; expansion is handled by arrow hits.
        _ = index
        return

    def _on_table_clicked(self, index: QtCore.QModelIndex) -> None:
        if self._suppress_next_row_click_selection:
            self._suppress_next_row_click_selection = False
            return
        if not index.isValid():
            return
        row = int(index.row())
        offset = self._window_start + row
        if offset < 0 or offset >= len(self._flat_rows):
            return
        row_ref = self._flat_rows[offset]
        node_id = str(row_ref.node_id or "").strip()
        if not node_id:
            return
        node = self._nodes_by_id.get(node_id)
        if not self._is_selectable_node(node):
            return
        mods = QtWidgets.QApplication.keyboardModifiers()
        multi = bool(mods & (QtCore.Qt.ControlModifier | QtCore.Qt.MetaModifier))
        shift = bool(mods & QtCore.Qt.ShiftModifier)
        next_selected: List[str] = list(self._selected_node_ids)
        if shift:
            anchor_id = str(self._selection_anchor_node_id or "").strip()
            range_node_ids = self._sibling_range_selection(anchor_id, node_id)
            if multi:
                for current_id in range_node_ids:
                    if current_id not in next_selected:
                        next_selected.append(current_id)
            else:
                next_selected = list(range_node_ids)
            if not anchor_id:
                self._selection_anchor_node_id = node_id
        elif multi:
            if node_id in next_selected:
                next_selected.remove(node_id)
            else:
                next_selected.append(node_id)
            self._selection_anchor_node_id = node_id
        else:
            next_selected = [node_id]
            self._selection_anchor_node_id = node_id
        self._set_selected_node_ids(next_selected, emit_signal=True)

    def _index_node(self, node: _VirtualTreeNode) -> None:
        self._nodes_by_id[node.node_id] = node
        if node.node_id not in self._original_order_by_node_id:
            self._original_order_by_node_id[node.node_id] = int(self._next_original_order)
            self._next_original_order += 1
        primary = str(node.primary_guid or "").strip()
        if primary and primary not in self._primary_guid_to_node_id:
            self._primary_guid_to_node_id[primary] = node.node_id
        for guid in list(node.element_ids or ()):
            current = str(guid or "").strip()
            if not current:
                continue
            self._guid_to_node_ids.setdefault(current, []).append(node.node_id)
        for child in list(node.children or []):
            child.parent = node
            self._index_node(child)

    def _set_node_expansion_depth(self, node: _VirtualTreeNode, *, current_level: int, max_level: int) -> None:
        node.expanded = bool(current_level <= max_level)
        for child in list(node.children or []):
            self._set_node_expansion_depth(child, current_level=current_level + 1, max_level=max_level)

    def _apply_filter(self) -> None:
        pattern = str(self._filter_pattern or "").strip().lower()
        for root in self._roots:
            self._mark_node_visibility(root, pattern)

    def _mark_node_visibility(self, node: _VirtualTreeNode, pattern: str) -> bool:
        searchable = " ".join([*(str(value or "") for value in node.columns), str(node.sub_label or "")]).lower()
        match_self = (not pattern) or (pattern in searchable)
        match_child = False
        for child in list(node.children or []):
            if self._mark_node_visibility(child, pattern):
                match_child = True
        visible = bool(match_self or match_child)
        node.filtered_out = not visible
        return visible

    def _refresh_flat_rows(self) -> None:
        rows: List[_VirtualVisibleRow] = []
        for root in self._sorted_siblings(self._roots):
            self._flatten_node(root, depth=0, sink=rows)
        self._flat_rows = rows
        self._reconcile_selection()
        self._sync_scrollbar_range()

    def _flatten_node(self, node: _VirtualTreeNode, *, depth: int, sink: List[_VirtualVisibleRow]) -> None:
        if node.filtered_out:
            return
        sink.append(_VirtualVisibleRow(node_id=node.node_id, depth=depth))
        if not node.expanded:
            return
        for child in self._sorted_siblings(list(node.children or [])):
            self._flatten_node(child, depth=depth + 1, sink=sink)

    def _sorted_siblings(self, nodes: Sequence[_VirtualTreeNode]) -> List[_VirtualTreeNode]:
        base = list(nodes or [])
        if not base:
            return []
        if self._smart_sort_enabled:
            return self._smart_sorted_siblings(base)
        if int(self._sort_direction) == 0 or int(self._sort_column) < 0:
            return base
        col = int(self._sort_column)
        reverse = int(self._sort_direction) < 0

        def key(node: _VirtualTreeNode) -> Tuple[str, str, int]:
            value = self._node_sort_text(node, col)
            label = str((node.columns[0] if node.columns else "") or "").strip().casefold()
            return value, label, int(self._original_order_by_node_id.get(str(node.node_id or ""), 0))

        if not self._group_folders_first:
            return sorted(base, key=key, reverse=reverse)
        groups = [node for node in base if bool(node.children)]
        leaves = [node for node in base if not bool(node.children)]
        groups = sorted(groups, key=key, reverse=reverse)
        leaves = sorted(leaves, key=key, reverse=reverse)
        # Keep container rows above element rows, like a file explorer.
        return [*groups, *leaves]

    def _smart_sorted_siblings(self, nodes: Sequence[_VirtualTreeNode]) -> List[_VirtualTreeNode]:
        base = list(nodes or [])
        if not base:
            return []
        selected = set(self._selected_node_ids)

        def key(node: _VirtualTreeNode) -> Tuple[int, int, str, int]:
            node_id = str(node.node_id or "")
            if node_id in selected:
                priority = 0
            elif node_id in self._smart_flagged_node_ids:
                priority = 1
            elif node_id in self._smart_active_search_node_ids:
                priority = 2
            else:
                priority = 3
            folder_rank = 0 if (self._group_folders_first and bool(node.children)) else 1
            name = self._node_sort_text(node, 0)
            original = int(self._original_order_by_node_id.get(node_id, 0))
            return priority, folder_rank, name, original

        return sorted(base, key=key)

    def _node_sort_text(self, node: _VirtualTreeNode, col: int) -> str:
        values = list(node.columns or ("", "", "", ""))
        value = str(values[col] if 0 <= col < len(values) else "").strip()
        if col == 1 and bool(node.children) and not value:
            value = str(node.sub_label or values[0] if values else "").strip()
        if col == 3 and not value:
            value = str(node.primary_guid or "").strip()
        if not value:
            value = str(values[0] if values else "").strip()
        return value.casefold()

    def _reconcile_selection(self) -> None:
        valid = set(self._nodes_by_id.keys())
        normalized: List[str] = []
        for node_id in list(self._selected_node_ids):
            current = str(node_id or "").strip()
            if not current or current in normalized:
                continue
            if current not in valid:
                continue
            node = self._nodes_by_id.get(current)
            if not self._is_selectable_node(node):
                continue
            normalized.append(current)
        self._selected_node_ids = normalized
        if self._selection_anchor_node_id and self._selection_anchor_node_id not in valid:
            self._selection_anchor_node_id = ""
        self._model.set_selected_ids(set(self._selected_node_ids))

    def _set_selected_node_ids(self, node_ids: Sequence[str], *, emit_signal: bool) -> None:
        normalized: List[str] = []
        valid = set(self._nodes_by_id.keys())
        for node_id in list(node_ids or []):
            current = str(node_id or "").strip()
            if not current or current in normalized:
                continue
            if current not in valid:
                continue
            node = self._nodes_by_id.get(current)
            if not self._is_selectable_node(node):
                continue
            normalized.append(current)
        changed = normalized != self._selected_node_ids
        self._selected_node_ids = normalized
        self._model.set_selected_ids(set(self._selected_node_ids))
        if changed and emit_signal and not self._suppress_selection:
            self.selectionChanged.emit()

    def _is_selectable_node(self, node: Optional[_VirtualTreeNode]) -> bool:
        if node is None:
            return False
        return bool(self._node_selection_element_ids(node))

    def _is_checkbox_node(self, node: Optional[_VirtualTreeNode]) -> bool:
        if node is None:
            return False
        if bool(node.children):
            return False
        return bool(str(node.primary_guid or "").strip())

    def _node_selection_element_ids(self, node: Optional[_VirtualTreeNode]) -> List[str]:
        if node is None:
            return []
        ids: List[str] = []
        for value in list(node.element_ids or ()):
            guid = str(value or "").strip()
            if not guid or guid in ids:
                continue
            ids.append(guid)
        return ids

    def _flat_offset_for_node_id(self, node_id: str) -> int:
        wanted = str(node_id or "").strip()
        if not wanted:
            return -1
        for idx, row in enumerate(self._flat_rows):
            if str(row.node_id or "") == wanted:
                return idx
        return -1

    def _visible_sibling_offsets(self, parent_node_id: str) -> List[int]:
        wanted_parent = str(parent_node_id or "")
        offsets: List[int] = []
        for idx, row in enumerate(self._flat_rows):
            node = self._nodes_by_id.get(str(row.node_id or ""))
            if not self._is_selectable_node(node):
                continue
            parent = node.parent if node is not None else None
            current_parent = str(parent.node_id if parent is not None else "")
            if current_parent != wanted_parent:
                continue
            offsets.append(idx)
        return offsets

    def _sibling_range_selection(self, anchor_node_id: str, target_node_id: str) -> List[str]:
        target_id = str(target_node_id or "").strip()
        target = self._nodes_by_id.get(target_id)
        if not self._is_selectable_node(target):
            return []
        anchor_id = str(anchor_node_id or "").strip()
        anchor = self._nodes_by_id.get(anchor_id)
        if not self._is_selectable_node(anchor):
            return [target_id]
        anchor_parent = anchor.parent if anchor is not None else None
        target_parent = target.parent if target is not None else None
        anchor_parent_id = str(anchor_parent.node_id if anchor_parent is not None else "")
        target_parent_id = str(target_parent.node_id if target_parent is not None else "")
        if anchor_parent_id != target_parent_id:
            return [target_id]
        sibling_offsets = self._visible_sibling_offsets(target_parent_id)
        if not sibling_offsets:
            return [target_id]
        anchor_offset = self._flat_offset_for_node_id(anchor_id)
        target_offset = self._flat_offset_for_node_id(target_id)
        if anchor_offset < 0 or target_offset < 0:
            return [target_id]
        if anchor_offset not in sibling_offsets or target_offset not in sibling_offsets:
            return [target_id]
        anchor_pos = sibling_offsets.index(anchor_offset)
        target_pos = sibling_offsets.index(target_offset)
        lo = min(anchor_pos, target_pos)
        hi = max(anchor_pos, target_pos)
        result: List[str] = []
        for pos in range(lo, hi + 1):
            offset = sibling_offsets[pos]
            if offset < 0 or offset >= len(self._flat_rows):
                continue
            row = self._flat_rows[offset]
            current_id = str(row.node_id or "").strip()
            if current_id and current_id not in result:
                result.append(current_id)
        return result or [target_id]

    def _sync_scrollbar_range(self) -> None:
        visible = self._visible_row_capacity()
        maximum = max(0, len(self._flat_rows) - visible)
        self._scroll.setPageStep(visible)
        self._scroll.setRange(0, maximum)
        if self._scroll.value() > maximum:
            self._scroll.setValue(maximum)

    def _visible_row_capacity(self) -> int:
        viewport_h = max(1, int(self._table.viewport().height()))
        return max(1, int(viewport_h // self._row_height))

    def _refresh_window(self) -> None:
        self._sync_scrollbar_range()
        total = len(self._flat_rows)
        visible = self._visible_row_capacity()
        start = max(0, min(int(self._scroll.value()), max(0, total - visible)))
        count = min(total - start, visible + self._overscan) if total > start else 0
        end = start + count
        self._window_start = start
        window_rows = self._flat_rows[start:end]
        self._model.update_window(
            window_rows,
            nodes_by_id=self._nodes_by_id,
            selected_ids=set(self._selected_node_ids),
            hovered_node_id=self._hovered_node_id,
            hovered_action=self._hovered_action,
        )

class ObjectTreePanel(BasePanel):
    _ROLE_ELEMENT_IDS = int(QtCore.Qt.UserRole) + 1
    _ROLE_PRIMARY_GUID = int(QtCore.Qt.UserRole) + 2
    _ROLE_BADGE_TEXT = int(QtCore.Qt.UserRole) + 3
    _BY_FILE_COLUMN_WIDTHS_KEY = "object_tree/by_file_column_widths"
    _BY_FILE_SORT_STATE_KEY = "object_tree/by_file_sort_state"
    _EXPAND_FULL_CONFIRM_THRESHOLD = 1200

    def __init__(
        self,
        parent: Optional[QtWidgets.QWidget] = None,
    ):
        super().__init__("Object Tree", parent)
        self.setObjectName("ObjectTreePanel")
        body = QtWidgets.QWidget(self)
        root = QtWidgets.QVBoxLayout(body)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        self._last_model_signature: Optional[tuple] = None
        self._last_ai_signature: Optional[tuple] = None
        self._last_selected_signature: tuple[str, ...] = tuple()
        self._recent_selected: List[str] = []
        self._suppress_by_file_selection = False
        self._ai_views_model = AiViewsModel(empty_message="", health=None, cards=tuple())
        self._theme_signature: Optional[tuple] = None
        self._class_mode_suggestion_buttons: List[QtWidgets.QToolButton] = []
        self._class_mode_selected_label = ""
        self._class_mode_selected_source = "manual"
        self._class_mode_active_guid = ""
        self._by_file_index: Dict[str, object] = {}
        self._last_by_file_synced_selection: tuple[str, ...] = tuple()
        self._settings = QtCore.QSettings()
        self._quick_start_state: Dict[str, object] = {"currentStep": 1, "completedSteps": []}
        self._quick_start_project_id = ""

        self.view_tabs = QtWidgets.QTabBar(self)
        self.view_tabs.setObjectName("ObjectTreeTabs")
        self.view_tabs.addTab("AI Views")
        self.view_tabs.addTab("By File")
        self.view_tabs.setCurrentIndex(0)
        self.view_tabs.currentChanged.connect(self._on_view_tab_changed)
        root.addWidget(self.view_tabs, 0)

        self.inner_tabs = QtWidgets.QTabWidget(self)
        self.inner_tabs.setObjectName("ObjectTreeInnerTabs")

        tree_tab = QtWidgets.QWidget(self.inner_tabs)
        tree_layout = QtWidgets.QVBoxLayout(tree_tab)
        tree_layout.setContentsMargins(0, 0, 0, 0)
        tree_layout.setSpacing(6)

        self.ai_tree_search = QtWidgets.QLineEdit(tree_tab)
        self.ai_tree_search.setPlaceholderText("Search tasks...")
        self.ai_tree_search.textChanged.connect(self._on_ai_search_changed)

        self.by_file_tree_search = QtWidgets.QLineEdit(tree_tab)
        self.by_file_tree_search.setPlaceholderText("Search objects...")
        self.by_file_tree_search.textChanged.connect(self._on_by_file_search_changed)

        self.tree_search_stack = QtWidgets.QStackedWidget(tree_tab)
        self.tree_search_stack.addWidget(self.ai_tree_search)
        self.tree_search_stack.addWidget(self.by_file_tree_search)
        tree_layout.addWidget(self.tree_search_stack, 0)

        self.by_file_toolbar = QtWidgets.QWidget(tree_tab)
        by_file_toolbar_layout = QtWidgets.QHBoxLayout(self.by_file_toolbar)
        by_file_toolbar_layout.setContentsMargins(0, 0, 0, 0)
        by_file_toolbar_layout.setSpacing(6)
        self.by_file_summary_label = QtWidgets.QLabel("Elements: 0 | Systems: 0", self.by_file_toolbar)
        self.by_file_summary_label.setObjectName("ByFileSummary")
        self.by_file_actions_btn = QtWidgets.QToolButton(self.by_file_toolbar)
        self.by_file_actions_btn.setText("⋮")
        self.by_file_actions_btn.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.by_file_actions_btn.setToolTip("Tree actions")
        self.by_file_actions_menu = QtWidgets.QMenu(self.by_file_actions_btn)
        self.by_file_sort_menu = self.by_file_actions_menu.addMenu("Sort by")
        self.by_file_smart_sort_action = self.by_file_sort_menu.addAction("Smart sort")
        self.by_file_smart_sort_action.setCheckable(True)
        self.by_file_smart_sort_action.toggled.connect(self._on_by_file_smart_sort_toggled)
        self.by_file_sort_menu.addSeparator()
        self.by_file_sort_group = QtGui.QActionGroup(self.by_file_sort_menu)
        self.by_file_sort_group.setExclusive(True)
        self._by_file_sort_actions: List[Tuple[QtGui.QAction, int, int]] = []
        for label, column, direction in (
            ("Name (A→Z)", 0, 1),
            ("Name (Z→A)", 0, -1),
            ("Type (A→Z)", 1, 1),
            ("Type (Z→A)", 1, -1),
            ("System (A→Z)", 2, 1),
            ("System (Z→A)", 2, -1),
            ("GlobalId (A→Z)", 3, 1),
            ("GlobalId (Z→A)", 3, -1),
        ):
            action = self.by_file_sort_menu.addAction(label)
            action.setCheckable(True)
            self.by_file_sort_group.addAction(action)
            action.triggered.connect(
                lambda checked=False, col=column, dirn=direction: self._on_by_file_sort_preset(col, dirn)
            )
            self._by_file_sort_actions.append((action, int(column), int(direction)))
        self.by_file_actions_menu.addSeparator()
        self.by_file_group_folders_first_action = self.by_file_actions_menu.addAction("Group folders first")
        self.by_file_group_folders_first_action.setCheckable(True)
        self.by_file_group_folders_first_action.toggled.connect(self._on_by_file_group_folders_first_toggled)
        self.by_file_reset_sort_action = self.by_file_actions_menu.addAction("Reset sorting")
        self.by_file_reset_sort_action.triggered.connect(self._on_by_file_reset_sorting)
        self.by_file_actions_menu.addSeparator()
        self.by_file_expand_all_action = self.by_file_actions_menu.addAction("Expand all")
        self.by_file_expand_all_action.triggered.connect(self._expand_by_file_tree_all)
        self.by_file_expand_fully_action = self.by_file_actions_menu.addAction("Expand fully...")
        self.by_file_expand_fully_action.triggered.connect(self._expand_by_file_tree_fully)
        self.by_file_expand_path_action = self.by_file_actions_menu.addAction("Expand selection path")
        self.by_file_expand_path_action.triggered.connect(self._expand_by_file_tree_selection_path)
        self.by_file_collapse_action = self.by_file_actions_menu.addAction("Collapse all")
        self.by_file_collapse_action.triggered.connect(self._collapse_by_file_tree)
        self.by_file_actions_menu.aboutToShow.connect(self._sync_by_file_actions_menu_state)
        self.by_file_actions_btn.setMenu(self.by_file_actions_menu)
        by_file_toolbar_layout.addWidget(self.by_file_summary_label, 0)
        by_file_toolbar_layout.addStretch(1)
        by_file_toolbar_layout.addWidget(self.by_file_actions_btn, 0)
        self.by_file_toolbar.setStyleSheet(
            normalize_stylesheet(
                f"""
                QLabel#ByFileSummary {{
                    color: {DARK_THEME.colors.text_secondary};
                    font-size: 12px;
                    font-weight: 600;
                }}
                QToolButton {{
                    border: 1px solid {DARK_THEME.colors.border_soft};
                    border-radius: 8px;
                    background: rgba(255, 255, 255, 8);
                    color: {DARK_THEME.colors.text_primary};
                    min-width: 22px;
                    min-height: 22px;
                    padding: 0px 5px;
                }}
                QToolButton:hover {{
                    background: rgba(255, 255, 255, 14);
                }}
                """,
                DARK_THEME,
            )
        )

        self.tree_tools_stack = QtWidgets.QStackedWidget(tree_tab)
        self.tree_tools_stack.addWidget(QtWidgets.QWidget(tree_tab))
        self.tree_tools_stack.addWidget(self.by_file_toolbar)
        tree_layout.addWidget(self.tree_tools_stack, 0)

        self.ai_views_panel = AiViewsPanel(tree_tab)
        self.ai_views_panel.primaryActionRequested.connect(self._on_ai_primary_action)
        self.ai_views_panel.secondaryActionRequested.connect(self._on_ai_secondary_action)
        self.ai_views_panel.rowSelectRequested.connect(self._on_ai_row_selected)
        self.ai_views_panel.healthBulletRequested.connect(self._on_ai_health_bullet)
        self.ai_views_panel.workflowActionRequested.connect(self._on_ai_workflow_action)

        self.by_file_tree = self._create_tree_widget(tree_tab)

        self.tree_stack = QtWidgets.QStackedWidget(tree_tab)
        self.tree_stack.addWidget(self.ai_views_panel)
        self.tree_stack.addWidget(self.by_file_tree)
        tree_layout.addWidget(self.tree_stack, 1)

        # Keep guided-classification banner in the Tree tab while the left
        # duplicate properties rendering is disabled.
        self.class_mode_frame = QtWidgets.QFrame(tree_tab)
        self.class_mode_frame.setObjectName("ClassificationModeBanner")
        self.class_mode_frame.setVisible(False)
        self.class_mode_frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        class_mode_layout = QtWidgets.QVBoxLayout(self.class_mode_frame)
        class_mode_layout.setContentsMargins(10, 10, 10, 10)
        class_mode_layout.setSpacing(8)

        class_mode_title = QtWidgets.QLabel("Classification needed", self.class_mode_frame)
        class_mode_title.setStyleSheet("font-weight: 700;")
        class_mode_layout.addWidget(class_mode_title, 0)

        class_mode_text = QtWidgets.QLabel(
            "This element is missing classification. Fixing this improves filters and auto-fix.",
            self.class_mode_frame,
        )
        class_mode_text.setWordWrap(True)
        class_mode_layout.addWidget(class_mode_text, 0)

        self.class_mode_element_label = QtWidgets.QLabel("-", self.class_mode_frame)
        self.class_mode_element_label.setStyleSheet(f"color: {DARK_THEME.colors.text_secondary};")
        class_mode_layout.addWidget(self.class_mode_element_label, 0)

        self.class_mode_suggestions_wrap = QtWidgets.QWidget(self.class_mode_frame)
        self.class_mode_suggestions_layout = QtWidgets.QHBoxLayout(self.class_mode_suggestions_wrap)
        self.class_mode_suggestions_layout.setContentsMargins(0, 0, 0, 0)
        self.class_mode_suggestions_layout.setSpacing(6)
        class_mode_layout.addWidget(self.class_mode_suggestions_wrap, 0)

        class_mode_actions = QtWidgets.QHBoxLayout()
        class_mode_actions.setSpacing(6)
        self.class_mode_apply_btn = QtWidgets.QPushButton("Apply classification", self.class_mode_frame)
        self.class_mode_apply_btn.setProperty("role", "primary")
        self.class_mode_apply_btn.clicked.connect(self._on_class_mode_apply)
        self.class_mode_next_btn = QtWidgets.QPushButton("Next unclassified", self.class_mode_frame)
        self.class_mode_next_btn.clicked.connect(self._on_class_mode_next)
        self.class_mode_exit_btn = QtWidgets.QPushButton("Exit", self.class_mode_frame)
        self.class_mode_exit_btn.clicked.connect(self._on_class_mode_exit)
        class_mode_actions.addWidget(self.class_mode_apply_btn, 0)
        class_mode_actions.addWidget(self.class_mode_next_btn, 0)
        class_mode_actions.addWidget(self.class_mode_exit_btn, 0)
        class_mode_actions.addStretch(1)
        class_mode_layout.addLayout(class_mode_actions)
        class_mode_stylesheet = f"""
            QFrame#ClassificationModeBanner {{
                border: 1px solid {DARK_THEME.colors.border};
                border-radius: 10px;
                background: {DARK_THEME.colors.panel};
            }}
            QFrame#ClassificationModeBanner QToolButton {{
                border: 1px solid {DARK_THEME.colors.border};
                border-radius: 8px;
                padding: 4px 8px;
                background: {DARK_THEME.colors.panel_alt};
                color: {DARK_THEME.colors.text_primary};
            }}
            QFrame#ClassificationModeBanner QToolButton:checked {{
                border: 1px solid rgba(255, 46, 136, 0.58);
                background: rgba(255, 46, 136, 0.16);
            }}
            """
        self.class_mode_frame.setStyleSheet(normalize_stylesheet(class_mode_stylesheet))

        tree_layout.insertWidget(0, self.class_mode_frame, 0)
        self.inner_tabs.addTab(tree_tab, "Tree")
        root.addWidget(self.inner_tabs, 1)

        self._on_view_tab_changed(0)

        self._refresh_timer = QtCore.QTimer(self)
        self._refresh_timer.setInterval(1000)
        self._refresh_timer.timeout.connect(self._refresh_from_host)
        self._refresh_timer.start()
        self.add_tab("object_tree", "Object Tree", body)
        QtCore.QTimer.singleShot(0, self._refresh_from_host)

    def _create_tree_widget(self, parent: QtWidgets.QWidget) -> _VirtualizedByFileTree:
        tree = _VirtualizedByFileTree(parent=parent)
        header = tree.header()
        header.sectionResized.connect(self._on_by_file_section_resized)
        tree.sortChanged.connect(self._on_by_file_sort_changed)
        self._restore_by_file_column_widths(tree)
        self._restore_by_file_sort_state(tree)
        tree.selectionChanged.connect(self._on_by_file_selection_changed)
        tree.customContextMenuRequested.connect(self._on_by_file_context_menu)
        tree.quickActionRequested.connect(self._on_by_file_quick_action)
        tree.setItemDelegateForColumn(
            0,
            _ByFileLabelDelegate(
                badge_role=_VirtualByFileTableModel._ROLE_BADGE_TEXT,
                depth_role=_VirtualByFileTableModel._ROLE_DEPTH,
                has_children_role=_VirtualByFileTableModel._ROLE_HAS_CHILDREN,
                expanded_role=_VirtualByFileTableModel._ROLE_EXPANDED,
                sublabel_role=_VirtualByFileTableModel._ROLE_SUBLABEL,
                selected_role=_VirtualByFileTableModel._ROLE_SELECTED,
                quick_can_role=_VirtualByFileTableModel._ROLE_CAN_QUICK_ACTIONS,
                quick_visible_role=_VirtualByFileTableModel._ROLE_SHOW_QUICK_ACTIONS,
                quick_hover_role=_VirtualByFileTableModel._ROLE_QUICK_HOVER_ACTION,
                checkbox_visible_role=_VirtualByFileTableModel._ROLE_CHECKBOX_VISIBLE,
                checkbox_checked_role=_VirtualByFileTableModel._ROLE_CHECKBOX_CHECKED,
                parent=tree,
            ),
        )
        tree.setItemDelegateForColumn(
            1,
            _ByFileTypeDelegate(
                selected_role=_VirtualByFileTableModel._ROLE_SELECTED,
                parent=tree,
            ),
        )
        tree_stylesheet = f"""
            QTableView#ByFileTree {{
                background: {DARK_THEME.colors.panel_overlay};
                border: 1px solid {DARK_THEME.colors.border};
                border-radius: 12px;
                padding: 4px;
            }}
            QTableView#ByFileTree::item {{
                min-height: 32px;
                padding: 4px 8px;
                border-radius: 6px;
            }}
            QTableView#ByFileTree::item:hover {{
                background: rgba(255, 255, 255, 6);
            }}
            QTableView#ByFileTree::item:selected {{
                background: rgba(255, 59, 154, 22);
                color: {DARK_THEME.colors.text_primary};
            }}
            QLabel#ByFileSummary {{
                color: {DARK_THEME.colors.text_secondary};
                font-size: 12px;
                font-weight: 600;
            }}
        """
        tree.setStyleSheet(normalize_stylesheet(tree_stylesheet))
        self._sync_by_file_actions_menu_state()
        return tree

    def _default_by_file_column_widths(self) -> List[int]:
        return [360, 160, 180, 240]

    def _restore_by_file_column_widths(self, tree) -> None:
        raw = self._settings.value(self._BY_FILE_COLUMN_WIDTHS_KEY, "")
        widths: List[int] = []
        if isinstance(raw, list):
            for value in raw:
                try:
                    widths.append(max(72, int(value)))
                except Exception:
                    continue
        elif isinstance(raw, str) and raw.strip():
            try:
                parsed = json.loads(raw)
            except Exception:
                parsed = []
            if isinstance(parsed, list):
                for value in parsed:
                    try:
                        widths.append(max(72, int(value)))
                    except Exception:
                        continue
        if len(widths) < 4:
            widths = list(self._default_by_file_column_widths())
        for col, width in enumerate(widths[:4]):
            tree.setColumnWidth(col, int(width))

    def _restore_by_file_sort_state(self, tree: _VirtualizedByFileTree) -> None:
        raw = self._settings.value(self._BY_FILE_SORT_STATE_KEY, "")
        column = -1
        direction = 0
        if isinstance(raw, str) and raw.strip():
            try:
                parsed = json.loads(raw)
            except Exception:
                parsed = {}
        elif isinstance(raw, dict):
            parsed = dict(raw)
        else:
            parsed = {}
        if isinstance(parsed, dict):
            try:
                column = int(parsed.get("column", -1))
            except Exception:
                column = -1
            try:
                direction = int(parsed.get("direction", 0))
            except Exception:
                direction = 0
        tree.set_sort_state(column=column, direction=direction, emit_signal=False)

    def _on_by_file_section_resized(self, _index: int, _old_size: int, _new_size: int) -> None:
        if not hasattr(self, "by_file_tree"):
            return
        widths = [max(72, int(self.by_file_tree.columnWidth(col))) for col in range(4)]
        self._settings.setValue(self._BY_FILE_COLUMN_WIDTHS_KEY, json.dumps(widths))

    def _on_by_file_sort_changed(self, column: int, direction: int) -> None:
        payload = {"column": int(column), "direction": int(direction)}
        self._settings.setValue(self._BY_FILE_SORT_STATE_KEY, json.dumps(payload))
        self._sync_by_file_actions_menu_state()

    def show_tree_tab(self) -> None:
        self.inner_tabs.setCurrentIndex(0)

    def show_ai_views(self) -> None:
        self.view_tabs.setCurrentIndex(0)
        self.show_tree_tab()

    def show_by_file(self) -> None:
        self.view_tabs.setCurrentIndex(1)
        self.show_tree_tab()

    def focus_search(self) -> None:
        self.show_tree_tab()
        if int(self.view_tabs.currentIndex()) <= 0:
            self.ai_tree_search.setFocus()
        else:
            self.by_file_tree_search.setFocus()

    def refresh_now(self) -> None:
        self._last_ai_signature = None
        self._last_model_signature = None
        self._refresh_from_host()

    def _on_view_tab_changed(self, index: int) -> None:
        safe_index = 0 if int(index) <= 0 else 1
        self.tree_search_stack.setCurrentIndex(safe_index)
        self.tree_stack.setCurrentIndex(safe_index)
        self.tree_tools_stack.setCurrentIndex(safe_index)

    def _on_ai_search_changed(self, text: str) -> None:
        self.ai_views_panel.set_filter(text)

    def _classification_mode_state(self, host) -> Dict[str, object]:
        if hasattr(host, "classificationModeState"):
            try:
                payload = host.classificationModeState()
                if isinstance(payload, dict):
                    return dict(payload)
            except Exception:
                return {"enabled": False, "source": "", "focusElementId": ""}
        return {"enabled": False, "source": "", "focusElementId": ""}

    def _classification_target_guid(self, host, preferred: str = "") -> str:
        state = getattr(host, "state", None)
        if state is None:
            return ""
        ifc_index = dict(getattr(state, "ifc_index", {}) or {})
        selected = [str(g) for g in list(getattr(state, "selected_elements", []) or []) if str(g).strip()]
        if selected and selected[0] in ifc_index:
            return selected[0]
        if preferred and preferred in ifc_index:
            return str(preferred)
        unclassified = self._unclassified_ids()
        if unclassified:
            return str(unclassified[0])
        return ""

    def _unclassified_ids(self) -> List[str]:
        card = self._card_by_id("unclassified")
        if card is None:
            return []
        return [str(guid) for guid in list(card.element_ids or ()) if str(guid).strip()]

    def _refresh_classification_mode(self, host) -> None:
        mode = self._classification_mode_state(host)
        enabled = bool(mode.get("enabled"))
        self.class_mode_frame.setVisible(enabled)
        if not enabled:
            self._class_mode_active_guid = ""
            return

        focus_guid = str(mode.get("focusElementId") or "").strip()
        guid = self._classification_target_guid(host, preferred=focus_guid)
        if not guid:
            self.class_mode_element_label.setText("No unclassified elements left.")
            self._set_class_mode_suggestions([])
            self.class_mode_apply_btn.setEnabled(False)
            self.class_mode_next_btn.setEnabled(False)
            return

        state = getattr(host, "state", None)
        elem = (getattr(state, "ifc_index", {}) or {}).get(guid) if state is not None else None
        display = self._display_name_for_element(guid, elem)
        self.class_mode_element_label.setText(f"Current: {display}")
        suggestions = self._classification_suggestions(host, guid, elem)
        self._set_class_mode_suggestions(suggestions)
        self.class_mode_apply_btn.setEnabled(bool(self._class_mode_selected_label))
        self.class_mode_next_btn.setEnabled(bool(self._unclassified_ids()))

        if guid != self._class_mode_active_guid:
            self._class_mode_active_guid = guid
            if hasattr(host, "_focus_ponker_classification_property"):
                host._focus_ponker_classification_property()
            if hasattr(host, "enableClassificationMode"):
                try:
                    host.enableClassificationMode(source=str(mode.get("source") or "aiViewsGo"), focusElementId=guid)
                except Exception:
                    pass

    def _set_class_mode_suggestions(self, suggestions: List[Dict[str, object]]) -> None:
        while self.class_mode_suggestions_layout.count():
            item = self.class_mode_suggestions_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._class_mode_suggestion_buttons = []
        self._class_mode_selected_label = ""
        self._class_mode_selected_source = "manual"

        if not suggestions:
            fallback = QtWidgets.QLabel("No suggestions available.", self.class_mode_suggestions_wrap)
            fallback.setStyleSheet(f"color: {DARK_THEME.colors.text_secondary};")
            self.class_mode_suggestions_layout.addWidget(fallback, 0)
            self.class_mode_suggestions_layout.addStretch(1)
            return

        for idx, suggestion in enumerate(suggestions[:3]):
            label = str(suggestion.get("label") or "").strip()
            if not label:
                continue
            score = float(suggestion.get("score", 0.0) or 0.0)
            source = str(suggestion.get("source") or "manual").strip() or "manual"
            button = QtWidgets.QToolButton(self.class_mode_suggestions_wrap)
            button.setCheckable(True)
            button.setAutoExclusive(True)
            button.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)
            button.setText(f"{label} ({score:.2f})" if score > 0.0 else label)
            button.clicked.connect(
                lambda _checked=False, lbl=label, src=source: self._on_class_mode_suggestion_selected(lbl, src)
            )
            self.class_mode_suggestions_layout.addWidget(button, 0)
            self._class_mode_suggestion_buttons.append(button)
            if idx == 0:
                button.setChecked(True)
                self._on_class_mode_suggestion_selected(label, source)

        self.class_mode_suggestions_layout.addStretch(1)

    def _on_class_mode_suggestion_selected(self, label: str, source: str) -> None:
        self._class_mode_selected_label = str(label or "").strip()
        self._class_mode_selected_source = str(source or "manual").strip() or "manual"
        self.class_mode_apply_btn.setEnabled(bool(self._class_mode_selected_label))

    def _display_name_for_element(self, guid: str, elem) -> str:
        if elem is None:
            return str(guid)
        name = str(getattr(elem, "name", "") or "").strip()
        if name:
            return name
        ifc_type = str(getattr(elem, "type", "") or "").strip()
        if ifc_type:
            return f"{ifc_type} ({guid[:8]})"
        return str(guid)

    def _classification_suggestions(self, host, guid: str, elem) -> List[Dict[str, object]]:
        if hasattr(host, "classificationSuggestionsForElement"):
            try:
                rows = host.classificationSuggestionsForElement(guid)
                if isinstance(rows, list):
                    cleaned = []
                    for row in rows:
                        if not isinstance(row, dict):
                            continue
                        label = str(row.get("label") or "").strip()
                        if not label:
                            continue
                        cleaned.append(
                            {
                                "label": label,
                                "score": float(row.get("score", 0.0) or 0.0),
                                "source": str(row.get("source") or "manual"),
                            }
                        )
                    if cleaned:
                        return cleaned[:3]
            except Exception:
                pass

        name = str(getattr(elem, "name", "") or "").lower() if elem is not None else ""
        ifc_type = str(getattr(elem, "type", "") or "").lower() if elem is not None else ""
        suggestions: List[Dict[str, object]] = []
        if "drain" in name:
            suggestions.append({"label": "Drainage", "score": 0.06, "source": "ai"})
        if "pipe" in ifc_type:
            suggestions.append({"label": "Plumbing", "score": 0.04, "source": "heuristic"})
        if "cable" in ifc_type:
            suggestions.append({"label": "Electrical", "score": 0.04, "source": "heuristic"})
        suggestions.append({"label": "Unknown", "score": 0.0, "source": "manual"})
        deduped: List[Dict[str, object]] = []
        seen: List[str] = []
        for row in suggestions:
            key = str(row.get("label") or "").strip().lower()
            if not key or key in seen:
                continue
            seen.append(key)
            deduped.append(row)
        return deduped[:3]

    def _resolve_host(self):
        widget = self.parentWidget()
        while widget is not None:
            if hasattr(widget, "state"):
                return widget
            widget = widget.parentWidget()
        window = self.window()
        if window is not None and hasattr(window, "state"):
            return window
        return None

    def _refresh_from_host(self) -> None:
        host = self._resolve_host()
        if host is None:
            return
        self._apply_theme_from_host(host)
        self._capture_recent_selection(host)

        model_sig = self._model_signature(host)
        if model_sig != self._last_model_signature:
            self._last_model_signature = model_sig
            self._rebuild_by_file_tree(host)

        ai_sig = self._ai_signature(host)
        if ai_sig != self._last_ai_signature:
            self._last_ai_signature = ai_sig
            self._rebuild_ai_views(host)
        self._apply_smart_sort_context(host)
        self._refresh_classification_mode(host)
        selected = self._host_selected_guids(host)
        self.sync_selection_from_store(selected, scroll_to_first=False)

    def _capture_recent_selection(self, host) -> None:
        current_selection = tuple(self._host_selected_guids(host))
        if current_selection == self._last_selected_signature:
            return
        self._last_selected_signature = current_selection
        for guid in current_selection:
            if guid in self._recent_selected:
                self._recent_selected.remove(guid)
            self._recent_selected.append(guid)
        if len(self._recent_selected) > 10:
            self._recent_selected = self._recent_selected[-10:]

    def _host_selected_guids(self, host) -> List[str]:
        store = getattr(host, "currentSelectionStore", None)
        if store is not None and hasattr(store, "getSelectionArray"):
            out: List[str] = []
            for guid in list(store.getSelectionArray() or []):
                key = str(guid or "").strip()
                if not key or key in out:
                    continue
                out.append(key)
            return out
        state = getattr(host, "state", None)
        if state is None:
            return []
        selected = getattr(state, "selectedIds", getattr(state, "selectedElementKeys", getattr(state, "selected_elements", [])))
        out: List[str] = []
        for guid in list(selected or []):
            key = str(guid or "").strip()
            if not key or key in out:
                continue
            out.append(key)
        return out

    def _model_signature(self, host) -> tuple:
        state = getattr(host, "state", None)
        if state is None:
            return tuple()
        ifc_index = getattr(state, "ifc_index", {}) or {}
        model_label = self._default_model_file_label(host)
        return (id(ifc_index), len(ifc_index), model_label)

    def _ai_signature(self, host) -> tuple:
        state = getattr(host, "state", None)
        if state is None:
            return tuple()

        issues = list(getattr(state, "bcf_issues", []) or [])
        issue_acc = 0
        for issue in issues:
            issue_acc ^= hash(
                (
                    str(getattr(issue, "issue_id", "") or ""),
                    str(getattr(issue, "guid_a", "") or ""),
                    str(getattr(issue, "guid_b", "") or ""),
                )
            )

        ifc_index = getattr(state, "ifc_index", {}) or {}
        class_labels = self._classification_labels(host, ifc_index)
        classification_acc = 0
        for guid, elem in ifc_index.items():
            classification_acc ^= hash(
                (
                    str(guid),
                    class_labels.get(str(guid), ""),
                    str(getattr(elem, "type", "") or ""),
                    str(getattr(elem, "system", "") or ""),
                    str(getattr(elem, "discipline", "") or ""),
                )
            )

        active_test = getattr(host, "_active_clash_test", None)
        active_test_name = str(getattr(active_test, "name", "") or "")
        clash_workflow = getattr(host, "_clash_workflow_state", None)
        has_run = bool(getattr(clash_workflow, "lastRun", None))
        active_step = str(getattr(clash_workflow, "activeStep", "") or "")
        selected_test = str(getattr(clash_workflow, "selectedTestId", "") or "")
        return (
            len(ifc_index),
            len(issues),
            issue_acc,
            classification_acc,
            tuple(self._recent_selected),
            active_test_name,
            has_run,
            active_step,
            selected_test,
        )

    def _default_model_file_label(self, host) -> str:
        state = getattr(host, "state", None)
        if state is None:
            return "Model file"
        active_model = getattr(state, "active_model", None)
        source_path = str(getattr(active_model, "sourcePath", "") or "").strip()
        if source_path:
            return Path(source_path).name or source_path
        ifc_path = str(getattr(state, "ifc_path", "") or "").strip()
        if ifc_path:
            return Path(ifc_path).name or ifc_path
        return "Model file"

    def _classification_labels(self, host, ifc_index: Dict[str, object]) -> Dict[str, str]:
        labels: Dict[str, str] = {}
        overrides = getattr(host, "_class_overrides", {}) or {}
        for guid, elem in ifc_index.items():
            key = str(guid)
            label = ""
            if isinstance(overrides, dict):
                payload = overrides.get(key)
                if isinstance(payload, dict):
                    label = str(payload.get("label", "") or "").strip()
            if not label:
                label = str(getattr(elem, "class_name", "") or "").strip()
            labels[key] = label
        return labels

    def _apply_smart_sort_context(self, host) -> None:
        if not hasattr(self, "by_file_tree"):
            return
        flagged, active = self._collect_smart_sort_guid_sets(host)
        self.by_file_tree.set_smart_context(
            flagged_guids=set(flagged),
            active_search_guids=set(active),
        )

    def _collect_smart_sort_guid_sets(self, host) -> Tuple[Set[str], Set[str]]:
        state = getattr(host, "state", None)
        if state is None:
            return set(), set()
        ifc_index = dict(getattr(state, "ifc_index", {}) or {})
        if not ifc_index:
            return set(), set()

        unclassified: Set[str] = set()
        try:
            class_labels = self._classification_labels(host, ifc_index)
            for guid, elem in ifc_index.items():
                key = str(guid or "").strip()
                if not key:
                    continue
                if is_element_unclassified(elem, class_labels.get(key, "")):
                    unclassified.add(key)
        except Exception:
            unclassified = set()

        clash_guids: Set[str] = set()
        try:
            for issue in list(getattr(state, "bcf_issues", []) or []):
                guid_a = str(getattr(issue, "guid_a", "") or "").strip()
                guid_b = str(getattr(issue, "guid_b", "") or "").strip()
                if guid_a:
                    clash_guids.add(guid_a)
                if guid_b:
                    clash_guids.add(guid_b)
        except Exception:
            clash_guids = set()

        active_search_guids: Set[str] = set()
        try:
            if hasattr(host, "_search_set_guids_for_choice"):
                choice = None
                has_choice = False
                if hasattr(host, "analyze_active_sets_combo"):
                    combo = getattr(host, "analyze_active_sets_combo", None)
                    if combo is not None and hasattr(combo, "currentData"):
                        choice = combo.currentData()
                        has_choice = True
                if has_choice:
                    result = host._search_set_guids_for_choice(choice)
                elif hasattr(host, "_active_search_set_guids"):
                    result = host._active_search_set_guids()
                else:
                    all_enabled_id = getattr(host, "SEARCH_SET_ALL_ENABLED_ID", None)
                    result = host._search_set_guids_for_choice(all_enabled_id)
                active_search_guids = {
                    str(g).strip() for g in set(result or set()) if str(g).strip()
                }
            elif hasattr(host, "_active_search_set_guids"):
                result = host._active_search_set_guids()
                active_search_guids = {
                    str(g).strip() for g in set(result or set()) if str(g).strip()
                }
        except Exception:
            active_search_guids = set()

        flagged = set(unclassified)
        flagged.update(clash_guids)
        return flagged, active_search_guids

    def _quick_start_project_id_for_host(self, host) -> str:
        state = getattr(host, "state", None)
        if state is None:
            return "default"
        raw = str(getattr(state, "ifc_path", "") or "").strip()
        if raw:
            raw = Path(raw).stem or raw
        if not raw:
            raw = self._default_model_file_label(host)
        cleaned = "".join(ch if str(ch).isalnum() or ch in {"-", "_", "."} else "_" for ch in str(raw))
        cleaned = cleaned.strip("._")
        return cleaned or "default"

    def _normalize_quick_start_state(self, state_obj: object) -> Dict[str, object]:
        payload = dict(state_obj) if isinstance(state_obj, dict) else {}
        completed: List[int] = []
        for raw in list(payload.get("completedSteps") or []):
            try:
                step_number = int(raw)
            except Exception:
                continue
            if 1 <= step_number <= 4 and step_number not in completed:
                completed.append(step_number)
        completed.sort()
        try:
            current = int(payload.get("currentStep", 1))
        except Exception:
            current = 1
        if current < 1:
            current = 1
        if current > 5:
            current = 5
        if len(completed) >= 4:
            current = 5
        else:
            while current in completed and current <= 4:
                current += 1
            if current > 4:
                for step_number in range(1, 5):
                    if step_number not in completed:
                        current = step_number
                        break
        return {"currentStep": int(current), "completedSteps": list(completed)}

    def _load_quick_start_state_for_project(self, host) -> None:
        project_id = self._quick_start_project_id_for_host(host)
        if project_id == self._quick_start_project_id:
            return
        self._quick_start_project_id = project_id
        key = f"objectTree/aiViews/quickStart/{project_id}"
        raw = self._settings.value(key, "")
        payload: object = {}
        if isinstance(raw, str) and raw.strip():
            try:
                payload = json.loads(raw)
            except Exception:
                payload = {}
        elif isinstance(raw, dict):
            payload = raw
        self._quick_start_state = self._normalize_quick_start_state(payload)

    def _save_quick_start_state(self) -> None:
        if not self._quick_start_project_id:
            return
        key = f"objectTree/aiViews/quickStart/{self._quick_start_project_id}"
        payload = self._normalize_quick_start_state(self._quick_start_state)
        self._quick_start_state = payload
        self._settings.setValue(key, json.dumps(payload))

    def _reset_quick_start_state(self, host) -> None:
        self._load_quick_start_state_for_project(host)
        self._quick_start_state = {"currentStep": 1, "completedSteps": []}
        self._save_quick_start_state()
        self._show_status("Quick start reset.", 2200)

    def _complete_quick_start_step(self, action_id: str) -> None:
        step_by_action = {
            "classify": 1,
            "runClash": 2,
            "reviewClashes": 3,
            "highRisk": 4,
        }
        step_number = step_by_action.get(str(action_id or "").strip())
        if step_number is None:
            return
        payload = self._normalize_quick_start_state(self._quick_start_state)
        completed = list(payload.get("completedSteps") or [])
        current = int(payload.get("currentStep") or 1)
        if step_number not in completed:
            completed.append(step_number)
            completed.sort()
        if current <= step_number:
            current = step_number + 1
        while current in completed and current <= 4:
            current += 1
        if len(completed) >= 4:
            current = 5
        self._quick_start_state = self._normalize_quick_start_state(
            {"currentStep": current, "completedSteps": completed}
        )
        self._save_quick_start_state()
        self._show_status("Step completed", 1800)

    def _apply_theme_from_host(self, host) -> None:
        signature = (
            str(getattr(host, "COLOR_BG", "")),
            str(getattr(host, "COLOR_SECONDARY_BG", "")),
            str(getattr(host, "COLOR_CARD", "")),
            str(getattr(host, "COLOR_TEXT_PRIMARY", "")),
            str(getattr(host, "COLOR_TEXT_SECONDARY", "")),
            str(getattr(host, "COLOR_TEXT_INACTIVE", "")),
            str(getattr(host, "COLOR_BORDER", "")),
            str(getattr(host, "COLOR_ACCENT", "")),
            str(getattr(host, "COLOR_ACCENT_HOVER", "")),
        )
        if signature == self._theme_signature:
            return
        self._theme_signature = signature
        self.ai_views_panel.set_theme(
            {
                "panel_bg": str(getattr(host, "COLOR_BG", DARK_THEME.colors.background)),
                "surface_1": str(getattr(host, "COLOR_SECONDARY_BG", DARK_THEME.colors.panel)),
                "surface_2": str(getattr(host, "COLOR_CARD", DARK_THEME.colors.panel_alt)),
                "text_1": str(getattr(host, "COLOR_TEXT_PRIMARY", DARK_THEME.colors.text_primary)),
                "text_2": str(getattr(host, "COLOR_TEXT_SECONDARY", DARK_THEME.colors.text_secondary)),
                "text_inactive": str(getattr(host, "COLOR_TEXT_INACTIVE", DARK_THEME.colors.text_muted)),
                "border": str(getattr(host, "COLOR_BORDER", DARK_THEME.colors.border)),
                "accent": str(getattr(host, "COLOR_ACCENT", DARK_THEME.colors.accent)),
                "accent_hover": str(getattr(host, "COLOR_ACCENT_HOVER", DARK_THEME.colors.accent_hover)),
            }
        )

    def _rebuild_by_file_tree(self, host) -> None:
        state = getattr(host, "state", None)
        if state is None:
            self._by_file_index = {}
            self._populate_by_file_tree([])
            self.by_file_summary_label.setText("Elements: 0 | Systems: 0")
            return
        ifc_index = dict(getattr(state, "ifc_index", {}) or {})
        self._by_file_index = dict(ifc_index)
        nodes = build_by_file_nodes(ifc_index, default_file_label=self._default_model_file_label(host))
        self._populate_by_file_tree(nodes)
        systems = set()
        for elem in ifc_index.values():
            systems.update(str(name).strip() for name in list(getattr(elem, "systems", []) or []) if str(name).strip())
            system = str(getattr(elem, "system", "") or "").strip()
            if system:
                systems.add(system)
        self.by_file_summary_label.setText(f"Elements: {len(ifc_index)} | Systems: {len(systems)}")
        self._on_by_file_search_changed(self.by_file_tree_search.text())

    def _rebuild_ai_views(self, host) -> None:
        state = getattr(host, "state", None)
        if state is None:
            self.ai_views_panel.set_model(
                AiViewsModel(
                    empty_message="Load a model to use AI Views",
                    health=None,
                    workflow=None,
                    cards=tuple(),
                )
            )
            return

        self._load_quick_start_state_for_project(host)
        ifc_index = dict(getattr(state, "ifc_index", {}) or {})
        issues = list(getattr(state, "bcf_issues", []) or [])
        labels = self._classification_labels(host, ifc_index)
        active_test = getattr(host, "_active_clash_test", None)
        active_test_name = str(getattr(active_test, "name", "") or "").strip() or "active test"
        clash_workflow = getattr(host, "_clash_workflow_state", None)
        has_run = bool(getattr(clash_workflow, "lastRun", None))
        selected_test_id = str(getattr(clash_workflow, "selectedTestId", "") or "")

        self._ai_views_model = build_ai_views_model(
            model_state={
                "elements": ifc_index,
                "class_labels": labels,
            },
            clash_state={
                "issues": issues,
                "active_test_name": active_test_name,
                "has_run": has_run,
                "selected_test_id": selected_test_id,
            },
            selection_state={
                "recent_selected": list(self._recent_selected),
            },
            quick_start_state=dict(self._quick_start_state),
        )
        self.ai_views_panel.set_model(self._ai_views_model)
        self.ai_views_panel.set_filter(self.ai_tree_search.text())

    def _populate_by_file_tree(self, nodes: List[ObjectTreeNode]) -> None:
        runtime_roots = [self._virtual_tree_node_from_object_node(node) for node in nodes]
        self._suppress_by_file_selection = True
        try:
            self.by_file_tree.set_tree(runtime_roots)
            self.by_file_tree.set_expansion_depth(1)
        finally:
            self._suppress_by_file_selection = False

    def _virtual_tree_node_from_object_node(self, node: ObjectTreeNode) -> _VirtualTreeNode:
        text = str(node.label or "")
        row = [text, "", "", ""]
        sub_label = ""
        node_id = str(node.id or "")
        if node_id.startswith("by-file:element:"):
            guid = node_id.split("by-file:element:", 1)[-1].strip()
            elem = self._by_file_index.get(guid)
            if elem is not None:
                name = str(getattr(elem, "name", "") or "").strip()
                row[0] = name or guid or text
                row[1] = friendly_item_type_label(getattr(elem, "type", ""))
                systems = [str(value).strip() for value in list(getattr(elem, "systems", []) or []) if str(value).strip()]
                system = systems[0] if systems else str(getattr(elem, "system", "") or "").strip()
                discipline = str(getattr(elem, "discipline", "") or "").strip()
                row[2] = system or discipline or "-"
                row[3] = guid
                tooltip = (
                    f"Name: {row[0]}\n"
                    f"Type: {row[1]}\n"
                    f"System: {row[2]}\n"
                    f"Discipline: {discipline or '-'}\n"
                    f"GlobalId: {guid}"
                )
            else:
                row[3] = guid
                tooltip = f"GlobalId: {guid}"
            primary_guid = guid
        else:
            cleaned_label, derived_type = self._split_group_label(text)
            row[0] = cleaned_label
            sub_label = derived_type
            if node_id.startswith("by-file:file:"):
                sub_label = "File"
            elif node_id.startswith("by-file:type:"):
                # Type-group labels (e.g., "MEP Segments", "Pipes") already
                # convey their category; avoid repeating "Type" as sublabel.
                if str(sub_label or "").strip().lower() == "type":
                    sub_label = ""
            tooltip = row[0]
            if node.count is not None:
                tooltip = f"{row[0]}\nElements: {int(node.count)}"
            primary_guid = ""

        runtime = _VirtualTreeNode(
            node_id=node_id,
            columns=(str(row[0]), str(row[1]), str(row[2]), str(row[3])),
            sub_label=str(sub_label or ""),
            tooltip=tooltip,
            element_ids=tuple(str(value) for value in list(node.element_ids or ()) if str(value).strip()),
            primary_guid=primary_guid,
            badge_text=str(int(node.count)) if node.count is not None else "",
            icon=self._icon_for_by_file_node(node),
            children=[],
            expanded=False,
            filtered_out=False,
        )
        runtime.children = [self._virtual_tree_node_from_object_node(child) for child in list(node.children or ())]
        return runtime

    def _split_group_label(self, label: str) -> Tuple[str, str]:
        raw = str(label or "").strip()
        if ":" not in raw:
            return raw, ""
        prefix, remainder = raw.split(":", 1)
        key = str(prefix or "").strip()
        value = str(remainder or "").strip()
        if not key or not value:
            return raw, ""
        lowered = key.lower()
        if lowered in {"system", "discipline", "type", "file"}:
            return value, key.capitalize()
        return raw, ""

    def _icon_for_by_file_node(self, node: ObjectTreeNode) -> QtGui.QIcon:
        node_id = str(node.id or "")
        style = self.style()
        if node_id.startswith("by-file:file:") or node_id.startswith("by-file:scope:") or node_id.startswith("by-file:type:"):
            return style.standardIcon(QtWidgets.QStyle.SP_DirClosedIcon)
        if node_id.startswith("by-file:element:"):
            return style.standardIcon(QtWidgets.QStyle.SP_FileIcon)
        return QtGui.QIcon()

    def _on_by_file_search_changed(self, text: str) -> None:
        self.by_file_tree.set_filter(str(text or ""))

    def _on_by_file_smart_sort_toggled(self, checked: bool) -> None:
        if not hasattr(self, "by_file_tree"):
            return
        self.by_file_tree.set_smart_sort_enabled(bool(checked))
        self._sync_by_file_actions_menu_state()

    def _on_by_file_sort_preset(self, column: int, direction: int) -> None:
        if not hasattr(self, "by_file_tree"):
            return
        self.by_file_tree.set_sort_state(column=int(column), direction=int(direction), emit_signal=True)
        self._sync_by_file_actions_menu_state()

    def _on_by_file_reset_sorting(self) -> None:
        if not hasattr(self, "by_file_tree"):
            return
        self.by_file_tree.set_sort_state(column=-1, direction=0, emit_signal=True)
        self._sync_by_file_actions_menu_state()

    def _on_by_file_group_folders_first_toggled(self, checked: bool) -> None:
        if not hasattr(self, "by_file_tree"):
            return
        self.by_file_tree.set_group_folders_first(bool(checked))

    def _sync_by_file_actions_menu_state(self) -> None:
        if not hasattr(self, "by_file_tree"):
            return
        smart_enabled = bool(self.by_file_tree.smart_sort_enabled())
        if hasattr(self, "by_file_smart_sort_action"):
            action = self.by_file_smart_sort_action
            old = action.blockSignals(True)
            action.setChecked(smart_enabled)
            action.blockSignals(old)
        col, direction = self.by_file_tree.sort_state()
        active_col = int(col)
        active_dir = int(direction)
        for action, preset_col, preset_dir in list(getattr(self, "_by_file_sort_actions", [])):
            wanted = bool(active_col == int(preset_col) and active_dir == int(preset_dir) and active_dir != 0)
            old = action.blockSignals(True)
            action.setChecked(wanted)
            action.setEnabled(not smart_enabled)
            action.blockSignals(old)
        if hasattr(self, "by_file_group_folders_first_action"):
            action = self.by_file_group_folders_first_action
            old = action.blockSignals(True)
            action.setChecked(bool(self.by_file_tree.group_folders_first()))
            action.blockSignals(old)
        if hasattr(self, "by_file_reset_sort_action"):
            self.by_file_reset_sort_action.setEnabled(bool((active_dir != 0) and (not smart_enabled)))

    def _set_by_file_expansion_depth(self, levels: int) -> None:
        self._with_preserved_tree_scroll(lambda: self.by_file_tree.set_expansion_depth(int(levels)))

    def _expand_by_file_tree_all(self) -> None:
        # Safe default to avoid expensive rendering spikes in very large trees.
        self._with_preserved_tree_scroll(lambda: self.by_file_tree.set_expansion_depth(2))

    def _expand_by_file_tree_fully(self) -> None:
        total = int(len(self._by_file_index or {}))
        if total > int(self._EXPAND_FULL_CONFIRM_THRESHOLD):
            result = QtWidgets.QMessageBox.question(
                self,
                "Expand fully",
                (
                    f"This model has {total} elements. "
                    "Expanding the entire tree can be slow.\n\nContinue?"
                ),
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No,
            )
            if result != QtWidgets.QMessageBox.Yes:
                return
        self._with_preserved_tree_scroll(lambda: self.by_file_tree.set_expansion_depth(999))

    def _expand_by_file_tree_selection_path(self) -> None:
        self._with_preserved_tree_scroll(self.by_file_tree.expand_selection_path)

    def _collapse_by_file_tree(self) -> None:
        self._with_preserved_tree_scroll(self.by_file_tree.collapse_all)

    def _with_preserved_tree_scroll(self, callback) -> None:
        previous = int(self.by_file_tree.scroll_value())
        callback()
        self.by_file_tree.set_scroll_value(previous)

    def _object_tree_scope_type(self, node_id: str) -> str:
        key = str(node_id or "").strip()
        if key.startswith("by-file:file:"):
            return "file"
        if key.startswith("by-file:scope:"):
            return "system"
        if key.startswith("by-file:type:"):
            return "group"
        if ":element:" in key:
            return "element"
        return "group"

    def _node_leaf_element_ids(self, node: object) -> List[str]:
        if node is None:
            return []
        out: List[str] = []
        seen: Set[str] = set()

        def append_guid(value: object) -> None:
            guid = str(value or "").strip()
            if not guid or guid in seen:
                return
            seen.add(guid)
            out.append(guid)

        stack = [node]
        while stack:
            current = stack.pop()
            children = list(getattr(current, "children", []) or [])
            if children:
                for child in reversed(children):
                    stack.append(child)
                continue
            for value in list(getattr(current, "element_ids", ()) or ()):
                append_guid(value)
        return out

    def _node_descendant_element_ids(self, node: object) -> List[str]:
        if node is None:
            return []
        children = list(getattr(node, "children", []) or [])
        if not children:
            return []
        out: List[str] = []
        seen: Set[str] = set()
        stack = list(children)
        while stack:
            current = stack.pop()
            current_children = list(getattr(current, "children", []) or [])
            if current_children:
                stack.extend(current_children)
                continue
            for value in list(getattr(current, "element_ids", ()) or ()):
                guid = str(value or "").strip()
                if not guid or guid in seen:
                    continue
                seen.add(guid)
                out.append(guid)
        return out

    def _on_by_file_selection_changed(self) -> None:
        if self._suppress_by_file_selection:
            return
        host = self._resolve_host()
        if host is not None and hasattr(host, "setFindObjectsScopeSelectionNodes"):
            payload: List[Dict[str, object]] = []
            for node in self.by_file_tree.selected_nodes():
                node_id = str(getattr(node, "node_id", "") or "").strip()
                if not node_id:
                    continue
                scope_type = self._object_tree_scope_type(node_id)
                node_element_ids = self._node_leaf_element_ids(node)
                descendant_element_ids = self._node_descendant_element_ids(node)
                payload.append(
                    {
                        "id": node_id,
                        "kind": scope_type,
                        "type": scope_type,
                        "label": str((node.columns[0] if node.columns else "") or "").strip(),
                        "elementIds": list(node_element_ids),
                        "descendantElementIds": list(descendant_element_ids),
                    }
                )
            host.setFindObjectsScopeSelectionNodes(payload, source="tree")
        guids = self._normalize_by_file_guid_list(self.by_file_tree.selected_element_ids())
        # Preserve current tree-row highlight for tree-originated selections.
        self._last_by_file_synced_selection = tuple(guids)
        self._select_guids(guids)

    def _on_by_file_context_menu(self, pos: QtCore.QPoint) -> None:
        host = self._resolve_host()
        if host is None:
            return
        adapter = self._resolve_viewer_visibility_adapter(host)
        if adapter is None:
            return

        target_guids = self.by_file_tree.element_ids_at(pos)
        if not target_guids:
            target_guids = self.by_file_tree.selected_element_ids()

        menu = ContextMenu(self.by_file_tree)
        hide_action = menu.addAction("Hide")
        isolate_action = menu.addAction("Show only (Isolate)")
        show_all_action = menu.addAction("Show all")
        transparency_menu = menu.addMenu("Transparency")
        focus_action = menu.addAction("Focus (Frame)")

        has_targets = bool(target_guids)
        hide_action.setEnabled(has_targets)
        isolate_action.setEnabled(has_targets)
        focus_action.setEnabled(has_targets)
        transparency_menu.setEnabled(has_targets)

        for pct in (25, 50, 75, 100):
            action = transparency_menu.addAction(f"{pct}%")
            action.triggered.connect(lambda _checked=False, value=pct, ids=list(target_guids): adapter.setTransparency(ids, value))

        hide_action.triggered.connect(lambda: adapter.hide(list(target_guids)))
        isolate_action.triggered.connect(lambda: adapter.showOnly(list(target_guids)))
        show_all_action.triggered.connect(adapter.showAll)
        focus_action.triggered.connect(lambda: adapter.focus(list(target_guids)))

        menu.exec(self.by_file_tree.viewport().mapToGlobal(pos))

    def _on_by_file_quick_action(self, action: str, element_ids: object) -> None:
        host = self._resolve_host()
        if host is None:
            return
        adapter = self._resolve_viewer_visibility_adapter(host)
        if adapter is None:
            return
        ids: List[str] = []
        for value in list(element_ids or []):
            guid = str(value or "").strip()
            if not guid or guid in ids:
                continue
            ids.append(guid)
        if not ids:
            return
        kind = str(action or "").strip().lower()
        if kind == "hide":
            adapter.hide(ids)
            return
        if kind == "isolate":
            adapter.showOnly(ids)

    def _resolve_viewer_visibility_adapter(self, host) -> Optional[ViewerVisibilityAdapter]:
        adapter = getattr(host, "viewer_visibility_adapter", None)
        if adapter is not None:
            return adapter
        viewer = getattr(host, "viewer", None)
        if viewer is None:
            return None
        focus_cb = getattr(host, "_context_fit_selection", None)
        show_all_cb = getattr(host, "_context_show_all", None)
        adapter = ViewerVisibilityAdapter(
            viewer,
            focus_callback=focus_cb if callable(focus_cb) else None,
            show_all_callback=show_all_cb if callable(show_all_cb) else None,
        )
        try:
            setattr(host, "viewer_visibility_adapter", adapter)
        except Exception:
            pass
        return adapter

    def sync_selection_from_store(self, guids: List[str], *, scroll_to_first: bool) -> None:
        normalized = self._normalize_by_file_guid_list(guids)
        signature = tuple(normalized)
        if signature == self._last_by_file_synced_selection and not scroll_to_first:
            return
        self._last_by_file_synced_selection = signature

        self._suppress_by_file_selection = True
        try:
            self.by_file_tree.sync_selected_guids(normalized, scroll_to_first=bool(scroll_to_first))
        finally:
            self._suppress_by_file_selection = False

    def _normalize_by_file_guid_list(self, guids: List[str]) -> List[str]:
        normalized: List[str] = []
        for guid in list(guids or []):
            current = str(guid or "").strip()
            if not current or current in normalized:
                continue
            if current not in self._by_file_index:
                continue
            normalized.append(current)
        return normalized

    def _select_guids(self, guids: List[str]) -> None:
        host = self._resolve_host()
        if host is None:
            return
        state = getattr(host, "state", None)
        if state is None:
            return
        ifc_index = getattr(state, "ifc_index", {}) or {}
        unique: List[str] = []
        for guid in guids:
            current = str(guid or "").strip()
            if not current or current in unique:
                continue
            if current not in ifc_index:
                continue
            unique.append(current)
        if not unique:
            if hasattr(host, "_apply_selection_contract"):
                host._apply_selection_contract(
                    [],
                    source="tree",
                    sync_viewer=True,
                    scroll_tree=False,
                )
            else:
                state.selected_elements = []
                viewer = getattr(host, "viewer", None)
                if viewer is not None and hasattr(viewer, "select_by_guids"):
                    viewer.select_by_guids([])
                if hasattr(host, "_sync_selection_views"):
                    host._sync_selection_views()
            return

        if hasattr(host, "_apply_selection_contract"):
            host._apply_selection_contract(
                list(unique),
                source="tree",
                sync_viewer=True,
                scroll_tree=False,
            )
        elif len(unique) == 1 and hasattr(host, "_context_show_properties"):
            host._context_show_properties(unique[0])
        else:
            state.selected_elements = list(unique)
            viewer = getattr(host, "viewer", None)
            if viewer is not None and hasattr(viewer, "select_by_guids"):
                viewer.select_by_guids(list(unique))
            if hasattr(host, "_sync_selection_views"):
                host._sync_selection_views()

    def _card_by_id(self, card_id: str) -> Optional[AiViewCard]:
        for card in self._ai_views_model.cards:
            if card.id == card_id:
                return card
        return None

    def _on_ai_primary_action(self, card_id: str) -> None:
        if card_id == "clashing":
            self._open_clashes()
            return

        if card_id == "unclassified":
            self._run_classification_flow()
            return

        if card_id == "high_risk":
            self._focus_high_risk()
            return

        if card_id == "recent":
            self.ai_views_panel.scroll_to_card("recent", expand=True)

    def _on_ai_secondary_action(self, card_id: str) -> None:
        if card_id in {"clashing", "unclassified"}:
            card = self._card_by_id(card_id)
            if card and card.element_ids:
                self._select_guids(list(card.element_ids))
            return

        if card_id == "high_risk":
            self.ai_views_panel.scroll_to_card("high_risk", expand=True)
            return

        if card_id == "recent":
            host = self._resolve_host()
            state = getattr(host, "state", None) if host is not None else None
            current_selection = tuple(
                str(guid)
                for guid in list(getattr(state, "selected_elements", []) or [])
                if str(guid).strip()
            )
            self._recent_selected = []
            self._last_selected_signature = current_selection
            self._last_ai_signature = None
            if host is not None:
                self._rebuild_ai_views(host)

    def _on_ai_row_selected(self, _card_id: str, element_ids_obj: object) -> None:
        if not isinstance(element_ids_obj, list):
            return
        self._select_guids([str(value) for value in element_ids_obj if str(value).strip()])

    def _on_ai_health_bullet(self, card_id: str) -> None:
        if not card_id:
            return
        self.ai_views_panel.scroll_to_card(card_id, expand=True)

    def _on_ai_workflow_action(self, action_id: str) -> None:
        action = str(action_id or "").strip()
        host = self._resolve_host()
        if not action or action == "done":
            self._show_status("No pending workflow action.")
            return

        if action == "quickStartRestart":
            if host is not None:
                self._reset_quick_start_state(host)
                self._last_ai_signature = None
                self._rebuild_ai_views(host)
            return

        if action == "classify":
            self._run_classification_flow()
            self._complete_quick_start_step(action)
            if host is not None:
                self._last_ai_signature = None
                self._rebuild_ai_views(host)
            return
        if action == "runClash":
            self._open_clash_setup(focus_run=True)
            self._complete_quick_start_step(action)
            if host is not None:
                self._last_ai_signature = None
                self._rebuild_ai_views(host)
            return
        if action == "reviewClashes":
            self._open_clashes()
            self._complete_quick_start_step(action)
            if host is not None:
                self._last_ai_signature = None
                self._rebuild_ai_views(host)
            return
        if action == "highRisk":
            self._focus_high_risk()
            self._complete_quick_start_step(action)
            if host is not None:
                self._last_ai_signature = None
                self._rebuild_ai_views(host)
            return
        if action == "goModel":
            self._go_to_model_panel()
            return

    def _run_classification_flow(self) -> None:
        card = self._card_by_id("unclassified")
        if card is None or not card.element_ids:
            self._show_status("All elements are classified.")
            return

        host = self._resolve_host()
        if host is not None and hasattr(host, "workspace_layout"):
            host.workspace_layout.show_panel("objectTree")
        self.show_tree_tab()

        selected = []
        state = getattr(host, "state", None) if host is not None else None
        if state is not None:
            selected = [str(g) for g in list(getattr(state, "selected_elements", []) or []) if str(g).strip()]
        unclassified_ids = [str(g) for g in list(card.element_ids or ()) if str(g).strip()]
        target_guid = ""
        if selected and selected[0] in unclassified_ids:
            target_guid = selected[0]
        elif unclassified_ids:
            target_guid = unclassified_ids[0]

        if not target_guid:
            self._show_status("Select an element first.", 3000)
            return

        if (not selected) or (selected[0] != target_guid):
            self._select_guids([target_guid])

        if host is not None and hasattr(host, "_set_mode"):
            host._set_mode("Inspect")
        if host is not None and hasattr(host, "enableClassificationMode"):
            host.enableClassificationMode(source="aiViewsGo", focusElementId=target_guid)
        self._refresh_classification_mode(host)
        self._show_status("Classification mode enabled. Apply a suggestion to continue.", 3500)

    def _on_class_mode_apply(self) -> None:
        host = self._resolve_host()
        if host is None:
            return
        mode = self._classification_mode_state(host)
        if not bool(mode.get("enabled")):
            self._show_status("Enable classification mode first.", 3000)
            return
        guid = self._classification_target_guid(host, preferred=str(mode.get("focusElementId") or ""))
        if not guid:
            self._show_status("Select an element first.", 3000)
            return
        label = str(self._class_mode_selected_label or "").strip()
        if not label:
            self._show_status("Pick a classification suggestion first.", 3000)
            return

        self.class_mode_apply_btn.setEnabled(False)
        QtWidgets.QApplication.processEvents()
        try:
            source = "manual"
            if self._class_mode_selected_source in {"ai", "heuristic"}:
                source = "ai"
            if hasattr(host, "setElementClassification"):
                host.setElementClassification(
                    guid,
                    {
                        "classification": label,
                        "source": source,
                    },
                )
            else:
                raise RuntimeError("Classification API is unavailable.")
            self._show_status(f"Classified as {label}.", 3000)
        except Exception as exc:
            self._show_status(f"Classification failed: {exc}", 4000)
            self.class_mode_apply_btn.setEnabled(True)
            return

        self.class_mode_apply_btn.setEnabled(True)
        if not self._select_next_unclassified(guid):
            if hasattr(host, "disableClassificationMode"):
                host.disableClassificationMode()
            self._refresh_classification_mode(host)
            self._show_status("All unclassified elements are resolved.", 3500)

    def _on_class_mode_next(self) -> None:
        host = self._resolve_host()
        if host is None:
            return
        mode = self._classification_mode_state(host)
        current = self._classification_target_guid(host, preferred=str(mode.get("focusElementId") or ""))
        if not self._select_next_unclassified(current):
            self._show_status("No unclassified elements left.", 3000)
            if hasattr(host, "disableClassificationMode"):
                host.disableClassificationMode()
            self._refresh_classification_mode(host)

    def _on_class_mode_exit(self) -> None:
        host = self._resolve_host()
        if host is not None and hasattr(host, "disableClassificationMode"):
            host.disableClassificationMode()
        self.class_mode_frame.setVisible(False)
        self._show_status("Classification mode disabled.", 2500)

    def _select_next_unclassified(self, current_guid: str) -> bool:
        host = self._resolve_host()
        if host is None:
            return False
        ids = self._unclassified_ids()
        if not ids:
            return False
        next_guid = ids[0]
        if current_guid in ids:
            idx = ids.index(current_guid) + 1
            if idx < len(ids):
                next_guid = ids[idx]
            else:
                next_guid = ids[0]
        self._select_guids([next_guid])
        if hasattr(host, "enableClassificationMode"):
            host.enableClassificationMode(source="aiViewsGo", focusElementId=next_guid)
        self._refresh_classification_mode(host)
        return True

    def _focus_high_risk(self) -> None:
        card = self._card_by_id("high_risk")
        if card is None or not card.rows:
            self._show_status("No high-risk systems found.")
            return
        top = card.rows[0]
        if not top.element_ids:
            self._show_status("No high-risk systems found.")
            return
        self._select_guids(list(top.element_ids))
        self.ai_views_panel.scroll_to_card("high_risk", expand=True)

    def _open_clash_setup(self, *, focus_run: bool = False) -> None:
        host = self._resolve_host()
        if host is None:
            return
        if hasattr(host, "workspace_layout"):
            host.workspace_layout.show_panel("clash")
        if hasattr(host, "_load_or_create_active_clash_test"):
            host._load_or_create_active_clash_test()
        if hasattr(host, "_clash_workflow_state"):
            host._clash_workflow_state.activeStep = "setup"
        if hasattr(host, "_sync_clash_workflow_panel"):
            host._sync_clash_workflow_panel()

        if focus_run and hasattr(host, "clash_detection_panel"):
            panel = getattr(host, "clash_detection_panel", None)
            setup = getattr(panel, "setup_step", None)
            run_btn = getattr(setup, "primary_btn", None)
            if run_btn is not None:
                run_btn.setFocus(QtCore.Qt.OtherFocusReason)

        if getattr(host, "_active_clash_test", None) is None:
            self._show_status("Create a clash test in Setup before running.", 3500)
        else:
            self._show_status("Clash setup opened. Press Run clash test.", 2500)

    def _go_to_model_panel(self) -> None:
        host = self._resolve_host()
        if host is not None and hasattr(host, "workspace_layout"):
            host.workspace_layout.show_panel("objectTree")
        self.view_tabs.setCurrentIndex(1)
        self.show_tree_tab()
        if host is not None and hasattr(host, "_set_mode"):
            host._set_mode("Inspect")
        self._show_status("Model browser opened. Import IFC from Project > Import IFC.", 3500)

    def _open_clashes(self) -> None:
        clashing_card = self._card_by_id("clashing")
        if clashing_card is not None and not clashing_card.element_ids:
            reason = str(clashing_card.primary_disabled_reason or "No clashes yet. Run a clash test first.")
            self._show_status(reason, 3000)
            return
        host = self._resolve_host()
        if host is None:
            return
        if hasattr(host, "workspace_layout"):
            host.workspace_layout.show_panel("clash")
        if hasattr(host, "_clash_workflow_state"):
            host._clash_workflow_state.activeStep = "results"
        if hasattr(host, "_sync_clash_workflow_panel"):
            host._sync_clash_workflow_panel()
        self._show_status("Clash results opened.", 2500)

    def _show_status(self, message: str, timeout_ms: int = 2500) -> None:
        host = self._resolve_host()
        if host is None:
            return
        if hasattr(host, "statusBar") and callable(getattr(host, "statusBar")):
            status = host.statusBar()
            if status is not None:
                status.showMessage(str(message or ""), int(timeout_ms))
