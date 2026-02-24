from __future__ import annotations

from typing import Optional

from PySide6 import QtCore, QtWidgets

from .base_panel import BasePanel
from .issue_list_panel import IssueListPanel


class IssuesPanel(BasePanel):
    issueActivated = QtCore.Signal(object)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__("Issues", parent)
        self.setObjectName("IssuesPanel")
        self.issue_list_panel = IssueListPanel(self)
        self.issue_list_panel.issueActivated.connect(self.issueActivated.emit)
        self.add_tab("issues", "Issue Tracker", self.issue_list_panel)

    def set_issue_rows(self, rows) -> None:
        self.issue_list_panel.set_issue_rows(list(rows or []))

    def set_selected_issue(self, issue: object) -> None:
        self.issue_list_panel.set_selected_issue(issue)
