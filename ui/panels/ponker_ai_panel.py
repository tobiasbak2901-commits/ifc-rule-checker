from __future__ import annotations

from typing import Optional

from PySide6 import QtWidgets

from .base_panel import BasePanel


class PonkerAIPanel(BasePanel):
    def __init__(
        self,
        content_widget: QtWidgets.QWidget,
        parent: Optional[QtWidgets.QWidget] = None,
    ):
        super().__init__("Ponker AI", parent)
        self.setObjectName("PonkerAIPanel")
        content_widget.setVisible(True)
        self.add_tab("ponker_ai", "Ponker AI", content_widget)
