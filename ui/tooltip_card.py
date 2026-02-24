from __future__ import annotations

from typing import Optional

from PySide6 import QtCore, QtWidgets

from ui.theme import DARK_THEME, normalize_stylesheet, rgba as theme_rgba


class ToolTooltipCard(QtWidgets.QFrame):
    """Shared tooltip card for toolbar tools."""

    _instance: Optional["ToolTooltipCard"] = None

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent, QtCore.Qt.ToolTip | QtCore.Qt.FramelessWindowHint)
        self.setObjectName("ToolTooltipCard")
        self.setAttribute(QtCore.Qt.WA_ShowWithoutActivating)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self._title = QtWidgets.QLabel("")
        self._title.setObjectName("ToolTooltipTitle")
        self._shortcut = QtWidgets.QLabel("")
        self._shortcut.setObjectName("ToolTooltipShortcut")
        self._desc = QtWidgets.QLabel("")
        self._desc.setObjectName("ToolTooltipDesc")
        self._desc.setWordWrap(True)

        header = QtWidgets.QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)
        header.addWidget(self._title, 1)
        header.addWidget(self._shortcut, 0, QtCore.Qt.AlignRight)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(10, 9, 10, 9)
        layout.setSpacing(4)
        layout.addLayout(header)
        layout.addWidget(self._desc, 0)
        self.setMinimumWidth(220)

        colors = DARK_THEME.colors
        stylesheet = f"""
            QFrame#ToolTooltipCard {
                background: {colors.panel_overlay};
                border: 1px solid {theme_rgba(colors.text_primary, 34)};
                border-radius: 10px;
            }
            QLabel#ToolTooltipTitle {
                color: {colors.text_inverse};
                font-weight: 700;
                font-size: 12px;
            }
            QLabel#ToolTooltipShortcut {
                color: {colors.text_inverse};
                font-size: 10px;
                background: {theme_rgba(colors.accent, 0.26)};
                border: 1px solid {theme_rgba(colors.accent, 0.65)};
                border-radius: 7px;
                padding: 1px 5px;
            }
            QLabel#ToolTooltipDesc {
                color: {colors.text_secondary};
                font-size: 11px;
            }
            """
        self.setStyleSheet(normalize_stylesheet(stylesheet))

    @classmethod
    def instance(cls, parent: Optional[QtWidgets.QWidget] = None) -> "ToolTooltipCard":
        if cls._instance is None:
            cls._instance = ToolTooltipCard(parent)
        return cls._instance

    def show_tooltip(self, title: str, shortcut: str, desc: str, global_pos: QtCore.QPoint):
        self._title.setText(str(title or "Tool"))
        shortcut_text = str(shortcut or "").strip()
        self._shortcut.setText(shortcut_text)
        self._shortcut.setVisible(bool(shortcut_text))
        self._desc.setText(str(desc or ""))
        self.adjustSize()
        offset = QtCore.QPoint(16, 16)
        self.move(global_pos + offset)
        self.show()

    def move_near(self, global_pos: QtCore.QPoint):
        if not self.isVisible():
            return
        self.move(global_pos + QtCore.QPoint(16, 16))
