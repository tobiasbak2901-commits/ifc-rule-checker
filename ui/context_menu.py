from __future__ import annotations

from typing import Optional

from PySide6 import QtCore, QtWidgets


class ContextMenu(QtWidgets.QMenu):
    """Minimal popup context menu.

    In Qt this popup behavior is equivalent to a portal/overlay menu and
    automatically closes on outside-click and Escape.
    """

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self.setWindowFlag(QtCore.Qt.Popup, True)

