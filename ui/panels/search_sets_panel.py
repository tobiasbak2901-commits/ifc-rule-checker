from __future__ import annotations

from typing import Optional

from PySide6 import QtWidgets

from .base_panel import BasePanel


class SearchSetsPanel(BasePanel):
    def __init__(
        self,
        content_widget: QtWidgets.QWidget,
        parent: Optional[QtWidgets.QWidget] = None,
    ):
        super().__init__("Search Sets", parent)
        self.setObjectName("SearchSetsPanel")
        self.add_tab("search_sets", "Search Sets", content_widget)
