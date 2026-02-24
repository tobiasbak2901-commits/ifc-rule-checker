from __future__ import annotations

from typing import Mapping, Optional

from PySide6 import QtCore, QtGui, QtWidgets

from ui.theme import DARK_THEME, normalize_stylesheet, rgba as theme_rgba


class IssueCard(QtWidgets.QFrame):
    clicked = QtCore.Signal(object)

    def __init__(
        self,
        payload: Mapping[str, object],
        parent: Optional[QtWidgets.QWidget] = None,
    ):
        super().__init__(parent)
        self.setObjectName("IssueCard")
        self.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self._payload = dict(payload or {})
        self._selected = False

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        self.title_label = QtWidgets.QLabel(str(self._payload.get("title") or "-"), self)
        self.title_label.setWordWrap(True)
        self.title_label.setObjectName("IssueCardTitle")
        self.title_label.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.title_label, 0)

        meta_row = QtWidgets.QHBoxLayout()
        meta_row.setContentsMargins(0, 0, 0, 0)
        meta_row.setSpacing(8)
        self.status_label = QtWidgets.QLabel(f"Status: {str(self._payload.get('status') or '-')}", self)
        self.priority_label = QtWidgets.QLabel(f"Priority: {str(self._payload.get('priority') or '-')}", self)
        self.status_label.setObjectName("IssueCardMeta")
        self.priority_label.setObjectName("IssueCardMeta")
        self.status_label.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        self.priority_label.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        meta_row.addWidget(self.status_label, 0)
        meta_row.addWidget(self.priority_label, 0)
        meta_row.addStretch(1)
        layout.addLayout(meta_row, 0)

        detail_row = QtWidgets.QHBoxLayout()
        detail_row.setContentsMargins(0, 0, 0, 0)
        detail_row.setSpacing(8)
        assignee = str(self._payload.get("assignee") or "Unassigned").strip() or "Unassigned"
        discipline = str(self._payload.get("discipline") or "-").strip() or "-"
        self.assignee_label = QtWidgets.QLabel(f"Assigned: {assignee}", self)
        self.discipline_label = QtWidgets.QLabel(f"Discipline: {discipline}", self)
        self.assignee_label.setObjectName("IssueCardSubMeta")
        self.discipline_label.setObjectName("IssueCardSubMeta")
        self.assignee_label.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        self.discipline_label.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        detail_row.addWidget(self.assignee_label, 1)
        detail_row.addWidget(self.discipline_label, 1)
        layout.addLayout(detail_row, 0)

        self._apply_style()

    @property
    def payload(self) -> Mapping[str, object]:
        return dict(self._payload)

    @property
    def issue(self) -> object:
        return self._payload.get("issue")

    def set_selected(self, selected: bool) -> None:
        flag = bool(selected)
        if self._selected == flag:
            return
        self._selected = flag
        self._apply_style()

    def mousePressEvent(self, event) -> None:
        if event.button() == QtCore.Qt.LeftButton:
            self.clicked.emit(self.issue)
            event.accept()
            return
        super().mousePressEvent(event)

    def _apply_style(self) -> None:
        colors = DARK_THEME.colors
        if self._selected:
            stylesheet = f"""
                QFrame#IssueCard {
                    background: {theme_rgba(colors.accent, 0.14)};
                    border: 1px solid {theme_rgba(colors.accent, 0.72)};
                    border-radius: 10px;
                }
                """
        else:
            stylesheet = f"""
                QFrame#IssueCard {
                    background: {theme_rgba(colors.panel, 0.92)};
                    border: 1px solid {theme_rgba(colors.text_primary, 0.12)};
                    border-radius: 10px;
                }
                QFrame#IssueCard:hover {
                    border: 1px solid {theme_rgba(colors.text_primary, 0.28)};
                }
                """
        self.setStyleSheet(normalize_stylesheet(stylesheet))
