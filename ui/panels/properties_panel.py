from __future__ import annotations

from typing import Optional

from PySide6 import QtWidgets

from .base_panel import BasePanel


class PropertiesPanel(BasePanel):
    def __init__(
        self,
        content_widget: QtWidgets.QWidget,
        parent: Optional[QtWidgets.QWidget] = None,
    ):
        super().__init__("Properties", parent)
        self.setObjectName("PropertiesPanel")
        self.add_tab("properties", "Properties", content_widget)
