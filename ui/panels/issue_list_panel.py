from __future__ import annotations

from typing import List, Mapping, Optional, Sequence

from PySide6 import QtCore, QtWidgets

from .issue_card import IssueCard


class IssueListPanel(QtWidgets.QWidget):
    issueActivated = QtCore.Signal(object)

    _UNASSIGNED = "__unassigned__"

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self.setObjectName("IssueListPanel")
        self._rows: List[Mapping[str, object]] = []
        self._cards: List[IssueCard] = []
        self._selected_issue = None

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        filters_wrap = QtWidgets.QWidget(self)
        filters_layout = QtWidgets.QGridLayout(filters_wrap)
        filters_layout.setContentsMargins(0, 0, 0, 0)
        filters_layout.setHorizontalSpacing(8)
        filters_layout.setVerticalSpacing(6)

        self.search_edit = QtWidgets.QLineEdit(filters_wrap)
        self.search_edit.setPlaceholderText("Search issues...")
        self.status_combo = QtWidgets.QComboBox(filters_wrap)
        self.discipline_combo = QtWidgets.QComboBox(filters_wrap)
        self.assignee_combo = QtWidgets.QComboBox(filters_wrap)

        filters_layout.addWidget(QtWidgets.QLabel("Search"), 0, 0)
        filters_layout.addWidget(self.search_edit, 0, 1, 1, 3)
        filters_layout.addWidget(QtWidgets.QLabel("Status"), 1, 0)
        filters_layout.addWidget(self.status_combo, 1, 1)
        filters_layout.addWidget(QtWidgets.QLabel("Discipline"), 1, 2)
        filters_layout.addWidget(self.discipline_combo, 1, 3)
        filters_layout.addWidget(QtWidgets.QLabel("Assigned"), 2, 0)
        filters_layout.addWidget(self.assignee_combo, 2, 1)
        self.summary_label = QtWidgets.QLabel("0 issues", filters_wrap)
        self.summary_label.setObjectName("SecondaryText")
        filters_layout.addWidget(self.summary_label, 2, 3, QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        root.addWidget(filters_wrap, 0)

        self.scroll = QtWidgets.QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.cards_host = QtWidgets.QWidget(self.scroll)
        self.cards_layout = QtWidgets.QVBoxLayout(self.cards_host)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(8)
        self.cards_layout.addStretch(1)
        self.scroll.setWidget(self.cards_host)
        root.addWidget(self.scroll, 1)

        self.empty_label = QtWidgets.QLabel("No issues", self)
        self.empty_label.setAlignment(QtCore.Qt.AlignCenter)
        self.empty_label.setObjectName("SecondaryText")
        root.addWidget(self.empty_label, 0)

        self.search_edit.textChanged.connect(self._apply_filters)
        self.status_combo.currentIndexChanged.connect(self._apply_filters)
        self.discipline_combo.currentIndexChanged.connect(self._apply_filters)
        self.assignee_combo.currentIndexChanged.connect(self._apply_filters)

        self._populate_filter_values([], [], [])
        self._apply_filters()

    def set_issue_rows(self, rows: Sequence[Mapping[str, object]]) -> None:
        self._rows = [dict(row or {}) for row in list(rows or [])]
        statuses = sorted(
            {str(row.get("status") or "").strip() for row in self._rows if str(row.get("status") or "").strip()},
            key=lambda value: value.lower(),
        )
        disciplines = sorted(
            {str(row.get("discipline") or "").strip() for row in self._rows if str(row.get("discipline") or "").strip()},
            key=lambda value: value.lower(),
        )
        assignees = sorted(
            {str(row.get("assignee") or "").strip() for row in self._rows if str(row.get("assignee") or "").strip()},
            key=lambda value: value.lower(),
        )
        self._populate_filter_values(statuses, disciplines, assignees)
        self._apply_filters()

    def set_selected_issue(self, issue: object) -> None:
        self._selected_issue = issue
        self._sync_selection_state()

    def _populate_filter_values(
        self,
        statuses: Sequence[str],
        disciplines: Sequence[str],
        assignees: Sequence[str],
    ) -> None:
        self._reset_combo(self.status_combo, "All statuses", [str(v) for v in list(statuses or [])])
        self._reset_combo(self.discipline_combo, "All disciplines", [str(v) for v in list(disciplines or [])])
        existing = [str(v) for v in list(assignees or [])]
        options = [("All users", ""), ("Unassigned", self._UNASSIGNED)] + [(value, value) for value in existing]
        current = self.assignee_combo.currentData() if self.assignee_combo.count() else ""
        self.assignee_combo.blockSignals(True)
        self.assignee_combo.clear()
        for label, value in options:
            self.assignee_combo.addItem(label, value)
        idx = self.assignee_combo.findData(current)
        self.assignee_combo.setCurrentIndex(max(0, idx))
        self.assignee_combo.blockSignals(False)

    def _reset_combo(self, combo: QtWidgets.QComboBox, all_label: str, values: Sequence[str]) -> None:
        current = combo.currentData() if combo.count() else ""
        combo.blockSignals(True)
        combo.clear()
        combo.addItem(all_label, "")
        for value in list(values or []):
            text = str(value or "").strip()
            if not text:
                continue
            combo.addItem(text, text)
        idx = combo.findData(current)
        combo.setCurrentIndex(max(0, idx))
        combo.blockSignals(False)

    def _apply_filters(self) -> None:
        rows = self._filtered_rows()
        self._rebuild_cards(rows)
        total = len(self._rows)
        shown = len(rows)
        self.summary_label.setText(f"{shown}/{total} issues")
        has_rows = shown > 0
        self.scroll.setVisible(has_rows)
        self.empty_label.setVisible(not has_rows)
        if not has_rows:
            self.empty_label.setText("No issues match current filters.")

    def _filtered_rows(self) -> List[Mapping[str, object]]:
        search = str(self.search_edit.text() or "").strip().lower()
        wanted_status = str(self.status_combo.currentData() or "").strip().lower()
        wanted_discipline = str(self.discipline_combo.currentData() or "").strip().lower()
        wanted_assignee = str(self.assignee_combo.currentData() or "").strip()
        filtered: List[Mapping[str, object]] = []
        for row in self._rows:
            status = str(row.get("status") or "").strip()
            discipline = str(row.get("discipline") or "").strip()
            assignee = str(row.get("assignee") or "").strip()
            text = str(row.get("search") or "").strip().lower()
            if wanted_status and status.lower() != wanted_status:
                continue
            if wanted_discipline and discipline.lower() != wanted_discipline:
                continue
            if wanted_assignee == self._UNASSIGNED:
                if assignee:
                    continue
            elif wanted_assignee and assignee.lower() != wanted_assignee.lower():
                continue
            if search and search not in text:
                continue
            filtered.append(row)
        return filtered

    def _rebuild_cards(self, rows: Sequence[Mapping[str, object]]) -> None:
        for card in list(self._cards):
            card.setParent(None)
            card.deleteLater()
        self._cards = []
        while self.cards_layout.count() > 0:
            item = self.cards_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        for row in list(rows or []):
            card = IssueCard(row, self.cards_host)
            card.clicked.connect(self._on_card_clicked)
            self.cards_layout.addWidget(card, 0)
            self._cards.append(card)
        self.cards_layout.addStretch(1)
        self._sync_selection_state()

    def _on_card_clicked(self, issue: object) -> None:
        self._selected_issue = issue
        self._sync_selection_state()
        self.issueActivated.emit(issue)

    def _sync_selection_state(self) -> None:
        selected = self._selected_issue
        selected_key = self._issue_key(selected)
        for card in self._cards:
            issue = card.issue
            card_key = self._issue_key(issue)
            is_selected = bool(issue is selected or (selected_key and card_key and selected_key == card_key))
            card.set_selected(is_selected)

    @staticmethod
    def _issue_key(issue: object) -> str:
        if issue is None:
            return ""
        issue_id = str(getattr(issue, "issue_id", "") or "").strip()
        if issue_id:
            return issue_id
        guid_a = str(getattr(issue, "guid_a", "") or "").strip()
        guid_b = str(getattr(issue, "guid_b", "") or "").strip()
        if guid_a or guid_b:
            return f"{guid_a}|{guid_b}"
        return ""
