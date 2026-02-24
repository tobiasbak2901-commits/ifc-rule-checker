from __future__ import annotations

from typing import Optional

from PySide6 import QtWidgets

from .base_panel import BasePanel


class FindObjectsPanel(BasePanel):
    def __init__(
        self,
        content_widget: QtWidgets.QWidget,
        parent: Optional[QtWidgets.QWidget] = None,
    ):
        super().__init__("Find Objects", parent)
        self.setObjectName("FindObjectsPanel")
        self.add_tab("find_objects", "Find Objects", content_widget)
