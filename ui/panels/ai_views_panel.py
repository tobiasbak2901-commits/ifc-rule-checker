from __future__ import annotations

from typing import Dict, Optional

from PySide6 import QtCore, QtGui, QtWidgets

from .ai_views_model import AiCardRow, AiViewsModel, AiViewsWorkflowState, AiViewCard
from .base_panel import BasePanel
from ui.theme import DARK_THEME, normalize_stylesheet


class AiViewCardWidget(QtWidgets.QFrame):
    _ROLE_ELEMENT_IDS = int(QtCore.Qt.UserRole) + 1

    primaryActionRequested = QtCore.Signal(str)
    secondaryActionRequested = QtCore.Signal(str)
    rowSelectRequested = QtCore.Signal(str, object)
    expandToggled = QtCore.Signal(str, bool)

    def __init__(self, card: AiViewCard, expanded: bool = False, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self.card = card
        self.setObjectName("AiViewCard")
        self.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        header = QtWidgets.QHBoxLayout()
        header.setSpacing(8)
        icon = QtWidgets.QLabel(str(card.icon or ""), self)
        icon.setObjectName("AiViewCardIcon")
        title = QtWidgets.QLabel(str(card.title or ""), self)
        title.setObjectName("AiViewCardTitle")
        title.setProperty("weight", "600")
        self.badge = QtWidgets.QLabel(str(int(card.count)), self)
        self.badge.setObjectName("AiViewCardBadge")

        self.expand_btn = QtWidgets.QToolButton(self)
        self.expand_btn.setObjectName("AiViewCardExpand")
        self.expand_btn.setText("Details")
        self.expand_btn.setCheckable(True)
        self.expand_btn.setChecked(bool(expanded))
        self.expand_btn.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.expand_btn.setArrowType(QtCore.Qt.DownArrow if expanded else QtCore.Qt.RightArrow)
        self.expand_btn.toggled.connect(self._on_expand_toggled)

        header.addWidget(icon, 0)
        header.addWidget(title, 1)
        header.addWidget(self.badge, 0)
        header.addWidget(self.expand_btn, 0)
        root.addLayout(header)

        self.description_label = QtWidgets.QLabel(str(card.description or ""), self)
        self.description_label.setWordWrap(True)
        self.description_label.setObjectName("AiViewCardDescription")
        root.addWidget(self.description_label, 0)

        actions = QtWidgets.QHBoxLayout()
        actions.setSpacing(6)
        self.primary_btn = QtWidgets.QPushButton(str(card.primary_label or "Primary"), self)
        self.primary_btn.setObjectName("AiViewPrimaryBtn")
        self.primary_btn.setProperty("role", "primary")
        self.primary_btn.setEnabled(bool(card.primary_enabled))
        self.primary_btn.setToolTip(self._disabled_tooltip(primary=True))
        self.primary_btn.clicked.connect(lambda: self.primaryActionRequested.emit(self.card.id))

        self.secondary_btn = QtWidgets.QPushButton(str(card.secondary_label or "Secondary"), self)
        self.secondary_btn.setObjectName("AiViewSecondaryBtn")
        self.secondary_btn.setFlat(False)
        self.secondary_btn.setEnabled(bool(card.secondary_enabled))
        self.secondary_btn.setToolTip(self._disabled_tooltip(primary=False))
        self.secondary_btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.secondary_btn.clicked.connect(lambda: self.secondaryActionRequested.emit(self.card.id))

        actions.addWidget(self.primary_btn, 0)
        actions.addWidget(self.secondary_btn, 0)
        actions.addStretch(1)
        root.addLayout(actions)

        self.details_tree = QtWidgets.QTreeWidget(self)
        self.details_tree.setObjectName("AiViewCardDetails")
        self.details_tree.setHeaderHidden(True)
        self.details_tree.setUniformRowHeights(True)
        self.details_tree.setRootIsDecorated(False)
        self.details_tree.setAlternatingRowColors(True)
        self.details_tree.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.details_tree.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.details_tree.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.details_tree.setMaximumHeight(240)
        self.details_tree.itemClicked.connect(self._on_row_clicked)
        self.details_tree.itemActivated.connect(self._on_row_clicked)
        self._populate_rows(card.rows)
        root.addWidget(self.details_tree, 1)
        self.details_tree.setVisible(bool(expanded))

    def matches_filter(self, pattern: str) -> bool:
        needle = str(pattern or "").strip().lower()
        if not needle:
            return True
        if needle in str(self.card.title or "").lower():
            return True
        if needle in str(self.card.description or "").lower():
            return True
        for row_idx in range(self.details_tree.topLevelItemCount()):
            row = self.details_tree.topLevelItem(row_idx)
            if needle in str(row.text(0) or "").lower():
                return True
        return False

    def set_expanded(self, expanded: bool) -> None:
        self.expand_btn.setChecked(bool(expanded))

    def _on_expand_toggled(self, expanded: bool) -> None:
        self.details_tree.setVisible(bool(expanded))
        self.expand_btn.setArrowType(QtCore.Qt.DownArrow if expanded else QtCore.Qt.RightArrow)
        self.expandToggled.emit(self.card.id, bool(expanded))

    def _populate_rows(self, rows: tuple[AiCardRow, ...]) -> None:
        self.details_tree.clear()
        if not rows:
            self.details_tree.addTopLevelItem(QtWidgets.QTreeWidgetItem(["(no details)"]))
            return
        for row in rows:
            text = str(row.label or "")
            if int(row.count) > 0:
                text = f"{text} ({int(row.count)})"
            if row.subtitle:
                text = f"{text} - {row.subtitle}"
            if float(row.risk_score) > 0.0:
                text = f"{text} [score {float(row.risk_score):.1f}]"
            item = QtWidgets.QTreeWidgetItem([text])
            item.setData(0, self._ROLE_ELEMENT_IDS, list(row.element_ids or ()))
            self.details_tree.addTopLevelItem(item)

    def _on_row_clicked(self, item: QtWidgets.QTreeWidgetItem, _column: int) -> None:
        element_ids = item.data(0, self._ROLE_ELEMENT_IDS)
        if isinstance(element_ids, list) and element_ids:
            self.rowSelectRequested.emit(self.card.id, list(element_ids))

    def _disabled_tooltip(self, primary: bool) -> str:
        if primary and not bool(self.card.primary_enabled):
            if self.card.primary_disabled_reason:
                return str(self.card.primary_disabled_reason)
            if self.card.id == "clashing":
                return "Run a clash test first."
            if self.card.id == "unclassified":
                return "All elements are classified."
            if self.card.id == "high_risk":
                return "No high-risk systems found."
        if (not primary) and (not bool(self.card.secondary_enabled)):
            if self.card.secondary_disabled_reason:
                return str(self.card.secondary_disabled_reason)
            if self.card.id == "clashing":
                return "No clashing elements to select."
            if self.card.id == "unclassified":
                return "No unclassified elements to select."
        return ""


class AiViewsPanel(BasePanel):
    primaryActionRequested = QtCore.Signal(str)
    secondaryActionRequested = QtCore.Signal(str)
    rowSelectRequested = QtCore.Signal(str, object)
    healthBulletRequested = QtCore.Signal(str)
    workflowActionRequested = QtCore.Signal(str)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__("AI Views", parent)
        self.setObjectName("AiViewsPanel")
        self._model = AiViewsModel(empty_message="", health=None, cards=tuple())
        self._card_widgets: Dict[str, AiViewCardWidget] = {}
        self._filter_text = ""
        self._next_banner_action = ""
        self._workflow_complete_action = ""
        self._settings = QtCore.QSettings()
        colors = DARK_THEME.colors
        self._theme = {
            "panel_bg": colors.background,
            "surface_1": colors.panel,
            "surface_2": colors.panel_alt,
            "text_1": colors.text_primary,
            "text_2": colors.text_secondary,
            "text_inactive": colors.text_muted,
            "border": colors.border,
            "accent": colors.accent,
            "accent_hover": colors.accent_hover,
        }

        body_widget = QtWidgets.QWidget(self)
        body_widget.setObjectName("AiViewsBodyWrap")
        root = QtWidgets.QVBoxLayout(body_widget)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        self.empty_wrap = QtWidgets.QWidget(self)
        self.empty_wrap.setObjectName("AiViewsEmptyWrap")
        empty_layout = QtWidgets.QVBoxLayout(self.empty_wrap)
        empty_layout.setContentsMargins(0, 8, 0, 8)
        empty_layout.setSpacing(10)

        self.empty_label = QtWidgets.QLabel("", self.empty_wrap)
        self.empty_label.setObjectName("AiViewsEmpty")
        self.empty_label.setAlignment(QtCore.Qt.AlignCenter)
        self.empty_label.setWordWrap(True)
        empty_layout.addWidget(self.empty_label, 0)

        self.empty_action_btn = QtWidgets.QPushButton("Go to Model", self.empty_wrap)
        self.empty_action_btn.setObjectName("AiViewsEmptyAction")
        self.empty_action_btn.setProperty("role", "primary")
        self.empty_action_btn.clicked.connect(lambda: self.workflowActionRequested.emit("goModel"))
        self.empty_action_btn.setVisible(False)
        empty_layout.addWidget(self.empty_action_btn, 0, QtCore.Qt.AlignHCenter)
        empty_layout.addStretch(1)

        root.addWidget(self.empty_wrap, 1)

        self.scroll = QtWidgets.QScrollArea(self)
        self.scroll.setObjectName("AiViewsScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.scroll.viewport().setAutoFillBackground(True)

        self.body = QtWidgets.QWidget(self.scroll)
        self.body.setObjectName("AiViewsBody")
        self.body_layout = QtWidgets.QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(8)

        self.health_frame = QtWidgets.QFrame(self.body)
        self.health_frame.setObjectName("AiViewsHealth")
        self.health_frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        health_layout = QtWidgets.QVBoxLayout(self.health_frame)
        health_layout.setContentsMargins(10, 10, 10, 10)
        health_layout.setSpacing(6)

        health_header = QtWidgets.QHBoxLayout()
        self.health_status_label = QtWidgets.QLabel("Model health", self.health_frame)
        self.health_status_label.setObjectName("AiViewsHealthStatus")
        self.health_score_label = QtWidgets.QLabel("100", self.health_frame)
        self.health_score_label.setObjectName("AiViewsHealthScore")
        health_header.addWidget(self.health_status_label, 1)
        health_header.addWidget(self.health_score_label, 0)
        health_layout.addLayout(health_header)

        self.health_bullets_wrap = QtWidgets.QWidget(self.health_frame)
        self.health_bullets_wrap.setObjectName("AiViewsHealthBulletsWrap")
        self.health_bullets_layout = QtWidgets.QVBoxLayout(self.health_bullets_wrap)
        self.health_bullets_layout.setContentsMargins(0, 0, 0, 0)
        self.health_bullets_layout.setSpacing(2)
        health_layout.addWidget(self.health_bullets_wrap, 0)

        self.workflow_frame = QtWidgets.QFrame(self.body)
        self.workflow_frame.setObjectName("AiViewsWorkflow")
        self.workflow_frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        workflow_layout = QtWidgets.QVBoxLayout(self.workflow_frame)
        workflow_layout.setContentsMargins(10, 10, 10, 10)
        workflow_layout.setSpacing(8)

        self.workflow_title = QtWidgets.QLabel("Quick start", self.workflow_frame)
        self.workflow_title.setObjectName("AiViewsWorkflowTitle")
        workflow_layout.addWidget(self.workflow_title, 0)

        self.workflow_steps_wrap = QtWidgets.QWidget(self.workflow_frame)
        self.workflow_steps_wrap.setObjectName("AiViewsWorkflowSteps")
        self.workflow_steps_layout = QtWidgets.QVBoxLayout(self.workflow_steps_wrap)
        self.workflow_steps_layout.setContentsMargins(0, 0, 0, 0)
        self.workflow_steps_layout.setSpacing(6)
        workflow_layout.addWidget(self.workflow_steps_wrap, 0)

        self.workflow_complete_wrap = QtWidgets.QWidget(self.workflow_frame)
        self.workflow_complete_layout = QtWidgets.QVBoxLayout(self.workflow_complete_wrap)
        self.workflow_complete_layout.setContentsMargins(0, 0, 0, 0)
        self.workflow_complete_layout.setSpacing(6)
        self.workflow_complete_label = QtWidgets.QLabel("Quick start complete", self.workflow_complete_wrap)
        self.workflow_complete_label.setObjectName("AiViewsWorkflowComplete")
        self.workflow_complete_label.setWordWrap(True)
        self.workflow_complete_action_btn = QtWidgets.QPushButton("Run again", self.workflow_complete_wrap)
        self.workflow_complete_action_btn.setObjectName("AiViewsWorkflowGo")
        self.workflow_complete_action_btn.setProperty("role", "primary")
        self.workflow_complete_action_btn.clicked.connect(self._on_workflow_complete_action_clicked)
        self.workflow_complete_layout.addWidget(self.workflow_complete_label, 0)
        self.workflow_complete_layout.addWidget(self.workflow_complete_action_btn, 0, QtCore.Qt.AlignLeft)
        self.workflow_complete_wrap.setVisible(False)
        workflow_layout.addWidget(self.workflow_complete_wrap, 0)

        self.next_banner_btn = QtWidgets.QPushButton("", self.workflow_frame)
        self.next_banner_btn.setObjectName("AiViewsNextBanner")
        self.next_banner_btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.next_banner_btn.clicked.connect(self._on_next_banner_clicked)
        workflow_layout.addWidget(self.next_banner_btn, 0)

        self.cards_wrap = QtWidgets.QWidget(self.body)
        self.cards_wrap.setObjectName("AiViewsCardsWrap")
        self.cards_layout = QtWidgets.QVBoxLayout(self.cards_wrap)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(8)

        self.body_layout.addWidget(self.health_frame, 0)
        self.body_layout.addWidget(self.workflow_frame, 0)
        self.body_layout.addWidget(self.cards_wrap, 1)

        self.scroll.setWidget(self.body)
        root.addWidget(self.scroll, 1)
        self.add_tab("ai_views", "AI Views", body_widget)

        self.set_theme()
        self._set_empty_state("Load a model to use AI Views")

    def set_theme(self, theme: Optional[Dict[str, str]] = None) -> None:
        if theme:
            self._theme.update({str(k): str(v) for k, v in theme.items() if v})
        t = self._theme
        stylesheet = f"""
            QWidget#AiViewsPanel {{
                background: {t['panel_bg']};
                color: {t['text_1']};
            }}
            QWidget#AiViewsEmptyWrap {{
                background: {t['panel_bg']};
            }}
            QLabel#AiViewsEmpty {{
                background: {t['panel_bg']};
                color: {t['text_2']};
                border: 1px dashed {t['border']};
                border-radius: 10px;
                padding: 14px;
            }}
            QPushButton#AiViewsEmptyAction {{
                min-height: 28px;
            }}
            QScrollArea#AiViewsScroll,
            QScrollArea#AiViewsScroll > QWidget > QWidget,
            QWidget#AiViewsBody,
            QWidget#AiViewsCardsWrap {{
                background: {t['panel_bg']};
            }}
            QFrame#AiViewsHealth {{
                background: {t['surface_1']};
                border: 1px solid {t['border']};
                border-radius: 10px;
            }}
            QFrame#AiViewsWorkflow {{
                background: {t['surface_1']};
                border: 1px solid {t['border']};
                border-radius: 10px;
            }}
            QLabel#AiViewsWorkflowTitle {{
                color: {t['text_1']};
                font-weight: 600;
            }}
            QLabel#AiViewsWorkflowComplete {{
                color: {t['text_1']};
                font-weight: 600;
            }}
            QFrame#AiViewsWorkflowRow {{
                background: {t['surface_2']};
                border: 1px solid {t['border']};
                border-radius: 8px;
            }}
            QLabel#AiViewsStepStatus {{
                border-radius: 8px;
                padding: 1px 7px;
                border: 1px solid {t['border']};
                background: rgba(148, 163, 184, 0.12);
                color: {t['text_2']};
                font-weight: 600;
            }}
            QLabel#AiViewsStepStatus[state="done"] {{
                color: {t['text_1']};
                background: rgba(34, 197, 94, 0.16);
            }}
            QLabel#AiViewsStepStatus[state="next"] {{
                color: {t['text_1']};
                background: rgba(255, 46, 136, 0.22);
            }}
            QLabel#AiViewsStepStatus[state="blocked"] {{
                color: {t['text_inactive']};
                background: rgba(15, 23, 38, 0.95);
            }}
            QLabel#AiViewsStepTitle {{
                color: {t['text_1']};
                font-weight: 600;
            }}
            QLabel#AiViewsStepDescription {{
                color: {t['text_2']};
            }}
            QPushButton#AiViewsWorkflowGo {{
                min-height: 26px;
            }}
            QPushButton#AiViewsWorkflowGo:disabled {{
                color: {t['text_inactive']};
                background: rgba(15, 23, 38, 0.95);
                border: 1px solid {t['border']};
            }}
            QPushButton#AiViewsNextBanner {{
                min-height: 30px;
                text-align: left;
                padding: 4px 10px;
                border-radius: 8px;
                border: 1px solid rgba(255, 46, 136, 0.36);
                background: rgba(255, 46, 136, 0.12);
                color: {t['text_1']};
            }}
            QPushButton#AiViewsNextBanner:hover {{
                border: 1px solid rgba(255, 46, 136, 0.52);
                background: rgba(255, 46, 136, 0.18);
            }}
            QPushButton#AiViewsNextBanner:disabled {{
                color: {t['text_2']};
                border: 1px solid {t['border']};
                background: rgba(15, 23, 38, 0.8);
            }}
            QLabel#AiViewsHealthStatus {{
                color: {t['text_1']};
                font-weight: 600;
            }}
            QLabel#AiViewsHealthScore,
            QLabel#AiViewCardBadge {{
                background: rgba(148, 163, 184, 0.14);
                color: {t['text_1']};
                border: 1px solid {t['border']};
                border-radius: 10px;
                padding: 2px 8px;
                font-weight: 700;
            }}
            QFrame#AiViewCard {{
                background: {t['surface_2']};
                border: 1px solid {t['border']};
                border-radius: 10px;
            }}
            QFrame#AiViewCard:hover {{
                border: 1px solid rgba(255, 46, 136, 0.42);
            }}
            QLabel#AiViewCardTitle {{
                color: {t['text_1']};
                font-weight: 600;
            }}
            QLabel#AiViewCardIcon {{
                color: {t['text_2']};
            }}
            QLabel#AiViewCardDescription {{
                color: {t['text_2']};
            }}
            QToolButton#AiViewCardExpand {{
                background: transparent;
                color: {t['text_2']};
                border: 1px solid transparent;
                border-radius: 6px;
                padding: 2px 6px;
            }}
            QToolButton#AiViewCardExpand:hover {{
                color: {t['text_1']};
                background: rgba(148, 163, 184, 0.14);
                border: 1px solid {t['border']};
            }}
            QPushButton#AiViewPrimaryBtn {{
                min-height: 28px;
            }}
            QPushButton#AiViewSecondaryBtn {{
                min-height: 28px;
                background: transparent;
                color: {t['text_2']};
                border: 1px solid {t['border']};
                border-radius: 8px;
                padding: 4px 10px;
            }}
            QPushButton#AiViewSecondaryBtn:hover {{
                color: {t['text_1']};
                border: 1px solid rgba(255, 46, 136, 0.42);
                background: rgba(255, 46, 136, 0.10);
            }}
            QPushButton#AiViewSecondaryBtn:disabled,
            QPushButton#AiViewPrimaryBtn:disabled {{
                color: {t['text_inactive']};
                background: rgba(15, 23, 38, 0.95);
                border: 1px solid {t['border']};
            }}
            QWidget#AiViewsHealthBulletsWrap QPushButton {{
                background: transparent;
                color: {t['text_2']};
                border: none;
                text-align: left;
                padding: 1px 0;
            }}
            QWidget#AiViewsHealthBulletsWrap QPushButton:hover {{
                color: {t['text_1']};
                text-decoration: underline;
            }}
            QTreeWidget#AiViewCardDetails {{
                background: rgba(15, 23, 38, 0.82);
                color: {t['text_1']};
                border: 1px solid {t['border']};
                border-radius: 8px;
                alternate-background-color: rgba(148, 163, 184, 0.05);
                selection-background-color: rgba(255, 46, 136, 0.24);
                selection-color: {t['text_1']};
                outline: none;
            }}
            QTreeWidget#AiViewCardDetails::item {{
                padding: 4px 6px;
            }}
            QTreeWidget#AiViewCardDetails::item:hover {{
                background: rgba(255, 46, 136, 0.12);
            }}
            QTreeWidget#AiViewCardDetails::item:selected {{
                background: rgba(255, 46, 136, 0.22);
            }}
            """
        self.setStyleSheet(normalize_stylesheet(stylesheet))

    def set_model(self, model: AiViewsModel) -> None:
        self._model = model
        if model.empty_message:
            self._set_empty_state(str(model.empty_message))
            return

        self.empty_wrap.setVisible(False)
        self.scroll.setVisible(True)

        self._rebuild_health(model)
        self._rebuild_workflow(model.workflow)
        self._rebuild_cards(model)
        self.set_filter(self._filter_text)

    def set_filter(self, text: str) -> None:
        self._filter_text = str(text or "")
        pattern = self._filter_text.strip().lower()
        for card in self._card_widgets.values():
            card.setVisible(card.matches_filter(pattern))

    def scroll_to_card(self, card_id: str, *, expand: bool = True) -> None:
        widget = self._card_widgets.get(str(card_id or ""))
        if widget is None:
            return
        if expand:
            widget.set_expanded(True)
        self.scroll.ensureWidgetVisible(widget, 0, 20)

    def expand_card(self, card_id: str, expanded: bool = True) -> None:
        widget = self._card_widgets.get(str(card_id or ""))
        if widget is None:
            return
        widget.set_expanded(bool(expanded))

    def _set_empty_state(self, message: str) -> None:
        self.empty_label.setText(str(message or ""))
        lowered = str(message or "").lower()
        self.empty_action_btn.setVisible("load a model" in lowered)
        self.empty_wrap.setVisible(True)
        self.scroll.setVisible(False)

    def _rebuild_health(self, model: AiViewsModel) -> None:
        summary = model.health
        if summary is None:
            self.health_status_label.setText("Model health")
            self.health_score_label.setText("-")
            self._clear_layout(self.health_bullets_layout)
            return

        self.health_status_label.setText(f"Model health: {summary.status}")
        self.health_score_label.setText(str(int(summary.score)))

        self._clear_layout(self.health_bullets_layout)
        for bullet in summary.bullets:
            btn = QtWidgets.QPushButton(str(bullet.text or ""), self.health_bullets_wrap)
            btn.setObjectName("AiViewsHealthBullet")
            btn.setFlat(True)
            btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
            target = str(bullet.target_card_id or "")
            btn.clicked.connect(lambda _checked=False, card_id=target: self._on_health_bullet_clicked(card_id))
            self.health_bullets_layout.addWidget(btn, 0)

    def _rebuild_workflow(self, workflow: Optional[AiViewsWorkflowState]) -> None:
        if workflow is None:
            self.workflow_frame.setVisible(False)
            self._next_banner_action = ""
            self._workflow_complete_action = ""
            return

        self.workflow_frame.setVisible(True)
        self._clear_layout(self.workflow_steps_layout)
        self._workflow_complete_action = ""
        self.workflow_complete_wrap.setVisible(False)
        self.workflow_steps_wrap.setVisible(True)
        if bool(getattr(workflow, "is_complete", False)):
            self.workflow_steps_wrap.setVisible(False)
            self.workflow_complete_wrap.setVisible(True)
            self.workflow_complete_label.setText(str(getattr(workflow, "complete_message", "") or "Quick start complete"))
            self._workflow_complete_action = str(getattr(workflow, "complete_action_id", "") or "")
            self.workflow_complete_action_btn.setText(str(getattr(workflow, "complete_action_label", "") or "Run again"))
            self.workflow_complete_action_btn.setVisible(bool(self._workflow_complete_action))
            self.next_banner_btn.setVisible(False)
            self._next_banner_action = ""
            return
        if not workflow.steps:
            self.workflow_frame.setVisible(False)
            self._next_banner_action = ""
            self._workflow_complete_action = ""
            return

        for step in workflow.steps:
            row = QtWidgets.QFrame(self.workflow_steps_wrap)
            row.setObjectName("AiViewsWorkflowRow")
            row_layout = QtWidgets.QHBoxLayout(row)
            row_layout.setContentsMargins(8, 6, 8, 6)
            row_layout.setSpacing(8)

            left = QtWidgets.QVBoxLayout()
            left.setContentsMargins(0, 0, 0, 0)
            left.setSpacing(2)

            title_label = QtWidgets.QLabel(f"{int(step.number)}. {step.title}", row)
            title_label.setObjectName("AiViewsStepTitle")
            left.addWidget(title_label, 0)

            description = QtWidgets.QLabel(str(step.description or ""), row)
            description.setObjectName("AiViewsStepDescription")
            description.setWordWrap(True)
            left.addWidget(description, 0)
            row_layout.addLayout(left, 1)

            go_btn = QtWidgets.QPushButton(str(step.action_label or "Go"), row)
            go_btn.setObjectName("AiViewsWorkflowGo")
            go_btn.setProperty("role", "primary")
            go_btn.setEnabled(bool(step.action_enabled))
            go_btn.setToolTip("")
            go_btn.clicked.connect(
                lambda _checked=False, action_id=str(step.action_id): self.workflowActionRequested.emit(action_id)
            )
            row_layout.addWidget(go_btn, 0, QtCore.Qt.AlignTop)
            self.workflow_steps_layout.addWidget(row, 0)

        self.next_banner_btn.setVisible(False)
        self._next_banner_action = ""

    def _on_next_banner_clicked(self) -> None:
        if self._next_banner_action:
            self.workflowActionRequested.emit(str(self._next_banner_action))

    def _on_workflow_complete_action_clicked(self) -> None:
        if self._workflow_complete_action:
            self.workflowActionRequested.emit(str(self._workflow_complete_action))

    def _rebuild_cards(self, model: AiViewsModel) -> None:
        self._card_widgets.clear()
        self._clear_layout(self.cards_layout)

        for card in model.cards:
            expanded = self._expand_state(card.id, default=(card.id == "clashing" and card.count > 0))
            widget = AiViewCardWidget(card, expanded=expanded, parent=self.cards_wrap)
            widget.primaryActionRequested.connect(self.primaryActionRequested)
            widget.secondaryActionRequested.connect(self.secondaryActionRequested)
            widget.rowSelectRequested.connect(self.rowSelectRequested)
            widget.expandToggled.connect(self._on_card_expand_toggled)
            self.cards_layout.addWidget(widget, 0)
            self._card_widgets[card.id] = widget

        self.cards_layout.addStretch(1)

    def _on_health_bullet_clicked(self, card_id: str) -> None:
        if card_id:
            self.scroll_to_card(card_id, expand=True)
            self.healthBulletRequested.emit(card_id)

    def _on_card_expand_toggled(self, card_id: str, expanded: bool) -> None:
        self._settings.setValue(f"objectTree/aiViews/expanded/{card_id}", bool(expanded))

    def _expand_state(self, card_id: str, default: bool = False) -> bool:
        value = self._settings.value(f"objectTree/aiViews/expanded/{card_id}", default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in {"1", "true", "yes", "on"}
        return bool(value)

    def _clear_layout(self, layout: QtWidgets.QLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
