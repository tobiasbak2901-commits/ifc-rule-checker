from __future__ import annotations

from typing import Callable, Optional

from PySide6 import QtCore, QtWidgets
from PySide6.QtGui import QColor, QCursor, QHelpEvent, QIcon, QKeyEvent, QPainter, QPixmap

from ui.tooltip_card import ToolTooltipCard


class IconToolButton(QtWidgets.QToolButton):
    """Reusable icon-first tool button with rich tooltip and text fallback."""

    def __init__(
        self,
        icon: QIcon,
        tooltip_title: str,
        tooltip_shortcut: str,
        tooltip_hint: str,
        group_label: str = "",
        checked: bool = False,
        checkable: bool = False,
        on_click: Optional[Callable] = None,
        parent: Optional[QtWidgets.QWidget] = None,
    ):
        super().__init__(parent)
        self.setCheckable(bool(checkable))
        self.setChecked(bool(checked))
        self.setAutoRaise(True)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setIconSize(QtCore.QSize(24, 24))
        self.setMinimumSize(44, 44)
        self.setContentsMargins(0, 0, 0, 0)
        self.setAccessibleName(tooltip_title)
        self.setAccessibleDescription(tooltip_hint)
        self.setObjectName("TopIconToolButton")
        self.setProperty("toolbarIcon", True)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setText(tooltip_title)
        self._tooltip_title = str(tooltip_title or "Tool")
        self._tooltip_shortcut = str(tooltip_shortcut or "")
        self._tooltip_hint = str(tooltip_hint or "")
        self._group_label = str(group_label or "").strip()
        self._tooltip_html = self._build_tooltip(tooltip_title, tooltip_shortcut, tooltip_hint, self._group_label)
        self._icon_default: Optional[QIcon] = None
        self._icon_hover: Optional[QIcon] = None
        self._icon_active: Optional[QIcon] = None
        self._icon_disabled: Optional[QIcon] = None
        self._tooltip_delay_ms = 150
        self._tooltip_timer = QtCore.QTimer(self)
        self._tooltip_timer.setSingleShot(True)
        self._tooltip_timer.timeout.connect(self._show_delayed_tooltip)
        self.setMouseTracking(True)
        self._glow_effect = QtWidgets.QGraphicsDropShadowEffect(self)
        self._glow_effect.setBlurRadius(14)
        self._glow_effect.setOffset(0, 0)
        self._glow_effect.setColor(QColor(255, 61, 166, 46))
        self.setGraphicsEffect(None)

        if icon and not icon.isNull():
            self._icon_default = self._tint_icon(icon, QColor("#C9D1D9"))
            self._icon_hover = self._tint_icon(icon, QColor("#F3F6FA"))
            self._icon_active = self._tint_icon(icon, QColor("#FFFFFF"))
            self._icon_disabled = self._tint_icon(icon, QColor("#7B8595"))
            self.setIcon(self._icon_default)
            self.setToolButtonStyle(QtCore.Qt.ToolButtonIconOnly)
        else:
            # Accessibility fallback when icon is missing.
            self.setText(tooltip_title)
            self.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)

        self.setToolTip("")
        self.setToolTipDuration(10000)
        self.setStatusTip(f"{tooltip_title} ({tooltip_shortcut}) - {tooltip_hint}")

        if on_click is not None:
            self.clicked.connect(on_click)
        self.toggled.connect(lambda _checked: self._refresh_icon_state())

    @staticmethod
    def _build_tooltip(title: str, shortcut: str, hint: str, group_label: str = "") -> str:
        title_html = str(title or "Tool")
        shortcut_html = str(shortcut or "")
        hint_html = str(hint or "")
        group_html = f"<span style='opacity:0.8'>{group_label}</span><br>" if group_label else ""
        shortcut_row = f"<span>{shortcut_html}</span><br>" if shortcut_html else ""
        return (
            f"{group_html}<b>{title_html}</b><br>"
            f"{shortcut_row}"
            f"<span>{hint_html}</span>"
        )

    @staticmethod
    def _tint_icon(icon: QIcon, color: QColor) -> QIcon:
        base = icon.pixmap(64, 64)
        if base.isNull():
            return icon
        tinted = QPixmap(base.size())
        tinted.fill(QtCore.Qt.transparent)
        painter = QPainter(tinted)
        painter.drawPixmap(0, 0, base)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(tinted.rect(), color)
        painter.end()
        return QIcon(tinted)

    def _refresh_icon_state(self):
        if not self._icon_default:
            return
        if not self.isEnabled() and self._icon_disabled:
            self.setIcon(self._icon_disabled)
            return
        if self.isChecked() and self._icon_active:
            self.setIcon(self._icon_active)
            return
        if self.underMouse() and self._icon_hover:
            self.setIcon(self._icon_hover)
        else:
            self.setIcon(self._icon_default)
        self._refresh_glow_state()

    def _refresh_glow_state(self):
        if not self.isEnabled():
            self.setGraphicsEffect(None)
            return
        if self.isChecked():
            self._glow_effect.setColor(QColor(255, 61, 166, 66))
            self._glow_effect.setBlurRadius(16)
            self.setGraphicsEffect(self._glow_effect)
            return
        if self.underMouse():
            self._glow_effect.setColor(QColor(255, 61, 166, 40))
            self._glow_effect.setBlurRadius(13)
            self.setGraphicsEffect(self._glow_effect)
            return
        self.setGraphicsEffect(None)

    def _show_delayed_tooltip(self):
        if not self.underMouse():
            return
        card = ToolTooltipCard.instance(self.window())
        pos = QCursor.pos()
        card.show_tooltip(self._tooltip_title, self._tooltip_shortcut, self._tooltip_hint, pos)

    def enterEvent(self, event):
        super().enterEvent(event)
        self._tooltip_timer.start(self._tooltip_delay_ms)
        self._refresh_icon_state()

    def leaveEvent(self, event):
        self._tooltip_timer.stop()
        ToolTooltipCard.instance(self.window()).hide()
        super().leaveEvent(event)
        self._refresh_icon_state()

    def mouseMoveEvent(self, event):
        card = ToolTooltipCard.instance(self.window())
        if card.isVisible():
            card.move_near(event.globalPosition().toPoint())
        super().mouseMoveEvent(event)

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self._refresh_icon_state()

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self._refresh_icon_state()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter, QtCore.Qt.Key_Space):
            if self.isEnabled():
                self.click()
                event.accept()
                return
        super().keyPressEvent(event)

    def event(self, event):
        if event.type() == QtCore.QEvent.ToolTip:
            if isinstance(event, QHelpEvent):
                self._tooltip_timer.start(self._tooltip_delay_ms)
            return True
        if event.type() == QtCore.QEvent.EnabledChange:
            self._refresh_icon_state()
        return super().event(event)
