from __future__ import annotations

import time
from typing import Dict, List, Optional, Sequence, Tuple

from PySide6 import QtCore, QtWidgets

from clash_tests.models import (
    GROUP_ELEMENT_A,
    GROUP_LEVEL,
    GROUP_PROXIMITY,
    IGNORE_IFCTYPE_IN,
    IGNORE_NAME_PATTERN,
    IGNORE_SAME_ELEMENT,
    IGNORE_SAME_FILE,
    IGNORE_SAME_SYSTEM,
    ClashTest,
    ClashType,
    IgnoreRule,
)
from ui.clash_workflow_state import ClashWorkflowState
from .base_panel import BasePanel


class ClashSetupStep(QtWidgets.QWidget):
    runRequested = QtCore.Signal()
    advancedRequested = QtCore.Signal()
    testChanged = QtCore.Signal(object)

    def __init__(self, advanced_widget: Optional[QtWidgets.QWidget] = None, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self._syncing = False
        self._search_sets: List[Tuple[str, str]] = []
        self._test: Optional[ClashTest] = None

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        self.empty_label = QtWidgets.QLabel("Load a model to create tests")
        self.empty_label.setWordWrap(True)
        self.empty_label.setObjectName("SecondaryText")
        root.addWidget(self.empty_label, 0)

        self.form_wrap = QtWidgets.QWidget(self)
        form_layout = QtWidgets.QVBoxLayout(self.form_wrap)
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setSpacing(8)

        sets_row = QtWidgets.QHBoxLayout()
        sets_row.setContentsMargins(0, 0, 0, 0)
        sets_row.setSpacing(8)
        self.sets_a_group = QtWidgets.QGroupBox("Search sets A")
        sets_a_layout = QtWidgets.QVBoxLayout(self.sets_a_group)
        sets_a_layout.setContentsMargins(8, 8, 8, 8)
        self.sets_a_list = QtWidgets.QListWidget(self.sets_a_group)
        self.sets_a_list.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.sets_a_list.setMinimumHeight(96)
        sets_a_layout.addWidget(self.sets_a_list, 1)
        sets_row.addWidget(self.sets_a_group, 1)

        self.sets_b_group = QtWidgets.QGroupBox("Search sets B")
        sets_b_layout = QtWidgets.QVBoxLayout(self.sets_b_group)
        sets_b_layout.setContentsMargins(8, 8, 8, 8)
        self.sets_b_list = QtWidgets.QListWidget(self.sets_b_group)
        self.sets_b_list.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.sets_b_list.setMinimumHeight(96)
        sets_b_layout.addWidget(self.sets_b_list, 1)
        sets_row.addWidget(self.sets_b_group, 1)
        form_layout.addLayout(sets_row, 0)

        type_row = QtWidgets.QHBoxLayout()
        type_row.setContentsMargins(0, 0, 0, 0)
        type_row.setSpacing(8)
        self.clash_type_combo = QtWidgets.QComboBox(self.form_wrap)
        self.clash_type_combo.addItem("Hard clash", ClashType.HARD.value)
        self.clash_type_combo.addItem("Clearance", ClashType.CLEARANCE.value)
        self.clash_type_combo.addItem("Tolerance", ClashType.TOLERANCE.value)
        type_row.addWidget(QtWidgets.QLabel("Clash type"), 0)
        type_row.addWidget(self.clash_type_combo, 1)
        form_layout.addLayout(type_row, 0)

        threshold_row = QtWidgets.QHBoxLayout()
        threshold_row.setContentsMargins(0, 0, 0, 0)
        threshold_row.setSpacing(6)
        threshold_row.addWidget(QtWidgets.QLabel("Threshold (mm)"), 0)
        self.threshold_minus_btn = QtWidgets.QToolButton(self.form_wrap)
        self.threshold_minus_btn.setText("-")
        self.threshold_plus_btn = QtWidgets.QToolButton(self.form_wrap)
        self.threshold_plus_btn.setText("+")
        self.threshold_spin = QtWidgets.QDoubleSpinBox(self.form_wrap)
        self.threshold_spin.setRange(0.0, 10000.0)
        self.threshold_spin.setDecimals(1)
        self.threshold_spin.setSingleStep(5.0)
        threshold_row.addWidget(self.threshold_minus_btn, 0)
        threshold_row.addWidget(self.threshold_spin, 1)
        threshold_row.addWidget(self.threshold_plus_btn, 0)
        form_layout.addLayout(threshold_row, 0)

        grouping_box = QtWidgets.QGroupBox("Grouping")
        grouping_layout = QtWidgets.QVBoxLayout(grouping_box)
        grouping_layout.setContentsMargins(8, 8, 8, 8)
        grouping_row = QtWidgets.QHBoxLayout()
        grouping_row.setContentsMargins(0, 0, 0, 0)
        grouping_row.setSpacing(6)
        self.grouping_list = QtWidgets.QListWidget(grouping_box)
        self.grouping_list.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.grouping_list.setMinimumHeight(88)
        grouping_row.addWidget(self.grouping_list, 1)
        grouping_btn_col = QtWidgets.QVBoxLayout()
        grouping_btn_col.setContentsMargins(0, 0, 0, 0)
        grouping_btn_col.setSpacing(4)
        self.grouping_up_btn = QtWidgets.QToolButton(grouping_box)
        self.grouping_up_btn.setText("Up")
        self.grouping_down_btn = QtWidgets.QToolButton(grouping_box)
        self.grouping_down_btn.setText("Down")
        grouping_btn_col.addWidget(self.grouping_up_btn, 0)
        grouping_btn_col.addWidget(self.grouping_down_btn, 0)
        grouping_btn_col.addStretch(1)
        grouping_row.addLayout(grouping_btn_col, 0)
        grouping_layout.addLayout(grouping_row, 0)
        proximity_row = QtWidgets.QHBoxLayout()
        proximity_row.setContentsMargins(0, 0, 0, 0)
        proximity_row.setSpacing(6)
        proximity_row.addWidget(QtWidgets.QLabel("Proximity (m)"), 0)
        self.proximity_spin = QtWidgets.QDoubleSpinBox(grouping_box)
        self.proximity_spin.setRange(0.1, 200.0)
        self.proximity_spin.setDecimals(1)
        self.proximity_spin.setSingleStep(0.5)
        self.proximity_spin.setValue(6.0)
        proximity_row.addWidget(self.proximity_spin, 1)
        grouping_layout.addLayout(proximity_row, 0)
        form_layout.addWidget(grouping_box, 0)

        ignore_box = QtWidgets.QGroupBox("Ignore rules")
        ignore_layout = QtWidgets.QVBoxLayout(ignore_box)
        ignore_layout.setContentsMargins(8, 8, 8, 8)
        ignore_layout.setSpacing(4)
        self.ignore_same_element = QtWidgets.QCheckBox("Ignore if same element")
        self.ignore_same_system = QtWidgets.QCheckBox("Ignore if same system")
        self.ignore_same_file = QtWidgets.QCheckBox("Ignore if same model/file")
        self.ignore_name_pattern = QtWidgets.QCheckBox("Exclude if name contains")
        self.ignore_name_pattern_edit = QtWidgets.QLineEdit(ignore_box)
        self.ignore_name_pattern_edit.setPlaceholderText("Comma-separated patterns (e.g. temp, old, demo)")
        self.ignore_ifctype_in = QtWidgets.QCheckBox("Exclude if ifcType in list")
        self.ignore_ifctype_in_edit = QtWidgets.QLineEdit(ignore_box)
        self.ignore_ifctype_in_edit.setPlaceholderText("Comma-separated ifcTypes (e.g. IfcSpace, IfcWall)")
        ignore_layout.addWidget(self.ignore_same_element, 0)
        ignore_layout.addWidget(self.ignore_same_system, 0)
        ignore_layout.addWidget(self.ignore_same_file, 0)
        ignore_layout.addWidget(self.ignore_name_pattern, 0)
        ignore_layout.addWidget(self.ignore_name_pattern_edit, 0)
        ignore_layout.addWidget(self.ignore_ifctype_in, 0)
        ignore_layout.addWidget(self.ignore_ifctype_in_edit, 0)
        form_layout.addWidget(ignore_box, 0)

        actions_row = QtWidgets.QHBoxLayout()
        actions_row.setContentsMargins(0, 0, 0, 0)
        actions_row.setSpacing(6)
        self.primary_btn = QtWidgets.QPushButton("Run clash test")
        self.primary_btn.setObjectName("WorkflowPrimaryCta")
        self.advanced_toggle = QtWidgets.QToolButton(self.form_wrap)
        self.advanced_toggle.setText("Advanced...")
        self.advanced_toggle.setCheckable(True)
        self.advanced_toggle.setArrowType(QtCore.Qt.RightArrow)
        actions_row.addWidget(self.primary_btn, 1)
        actions_row.addWidget(self.advanced_toggle, 0)
        form_layout.addLayout(actions_row, 0)

        self.advanced_wrap = QtWidgets.QWidget(self.form_wrap)
        advanced_layout = QtWidgets.QVBoxLayout(self.advanced_wrap)
        advanced_layout.setContentsMargins(0, 0, 0, 0)
        advanced_layout.setSpacing(6)
        self.auto_viewpoint_toggle = QtWidgets.QCheckBox("Auto-generate viewpoint")
        self.auto_screenshot_toggle = QtWidgets.QCheckBox("Auto screenshot (if available)")
        self.open_advanced_btn = QtWidgets.QPushButton("Open advanced settings")
        advanced_layout.addWidget(self.auto_viewpoint_toggle, 0)
        advanced_layout.addWidget(self.auto_screenshot_toggle, 0)
        if advanced_widget is not None:
            advanced_widget.setParent(self.advanced_wrap)
            advanced_widget.setVisible(True)
            advanced_layout.addWidget(advanced_widget, 0)
        advanced_layout.addWidget(self.open_advanced_btn, 0, QtCore.Qt.AlignLeft)
        self.advanced_wrap.setVisible(False)
        form_layout.addWidget(self.advanced_wrap, 0)

        root.addWidget(self.form_wrap, 1)

        self.threshold_minus_btn.clicked.connect(lambda: self.threshold_spin.setValue(self.threshold_spin.value() - 5.0))
        self.threshold_plus_btn.clicked.connect(lambda: self.threshold_spin.setValue(self.threshold_spin.value() + 5.0))
        self.grouping_up_btn.clicked.connect(lambda: self._move_grouping_item(-1))
        self.grouping_down_btn.clicked.connect(lambda: self._move_grouping_item(+1))
        self.primary_btn.clicked.connect(self._on_run_clicked)
        self.advanced_toggle.toggled.connect(self._on_advanced_toggled)
        self.open_advanced_btn.clicked.connect(self.advancedRequested.emit)

        self.sets_a_list.itemChanged.connect(lambda _item: self._emit_test_changed())
        self.sets_b_list.itemChanged.connect(lambda _item: self._emit_test_changed())
        self.clash_type_combo.currentIndexChanged.connect(lambda _idx: self._on_clash_type_changed())
        self.threshold_spin.valueChanged.connect(lambda _v: self._emit_test_changed())
        self.grouping_list.itemChanged.connect(lambda _item: self._emit_test_changed())
        self.grouping_list.currentRowChanged.connect(lambda _row: self._emit_test_changed())
        self.proximity_spin.valueChanged.connect(lambda _v: self._emit_test_changed())
        self.ignore_same_element.toggled.connect(lambda _checked: self._emit_test_changed())
        self.ignore_same_system.toggled.connect(lambda _checked: self._emit_test_changed())
        self.ignore_same_file.toggled.connect(lambda _checked: self._emit_test_changed())
        self.ignore_name_pattern.toggled.connect(self._on_ignore_name_toggled)
        self.ignore_name_pattern_edit.textChanged.connect(lambda _text: self._emit_test_changed())
        self.ignore_ifctype_in.toggled.connect(self._on_ignore_ifctype_toggled)
        self.ignore_ifctype_in_edit.textChanged.connect(lambda _text: self._emit_test_changed())
        self.auto_viewpoint_toggle.toggled.connect(lambda _checked: self._emit_test_changed())
        self.auto_screenshot_toggle.toggled.connect(lambda _checked: self._emit_test_changed())

        self._ensure_grouping_items()
        self._on_clash_type_changed()
        self.set_model_loaded(False)

    def set_model_loaded(self, loaded: bool) -> None:
        is_loaded = bool(loaded)
        self.empty_label.setVisible(not is_loaded)
        self.form_wrap.setVisible(is_loaded)
        self.form_wrap.setEnabled(is_loaded)

    def set_available_search_sets(self, search_sets: Sequence[Tuple[str, str]]) -> None:
        selected_a = set(self._checked_ids(self.sets_a_list))
        selected_b = set(self._checked_ids(self.sets_b_list))
        self._search_sets = [(str(sid), str(name)) for sid, name in list(search_sets or [])]
        self._populate_search_set_list(self.sets_a_list, selected_a)
        self._populate_search_set_list(self.sets_b_list, selected_b)

    def set_test(self, test: ClashTest) -> None:
        self._syncing = True
        try:
            self._test = test
            set_a = set(str(v) for v in list(test.search_set_ids_a or []))
            set_b = set(str(v) for v in list(test.search_set_ids_b or []))
            self._populate_search_set_list(self.sets_a_list, set_a)
            self._populate_search_set_list(self.sets_b_list, set_b)
            clash_type = str(getattr(test.clash_type, "value", test.clash_type) or ClashType.HARD.value)
            idx = self.clash_type_combo.findData(clash_type)
            self.clash_type_combo.setCurrentIndex(max(0, idx))
            self.threshold_spin.setValue(float(test.threshold_mm or 0.0))
            self._apply_grouping_order(list(test.grouping_order or []))
            self.proximity_spin.setValue(float(test.proximity_meters or 6.0))
            ignore_map = {str(rule.key): bool(rule.enabled) for rule in list(test.ignore_rules or [])}
            ignore_params = {str(rule.key): dict(rule.params or {}) for rule in list(test.ignore_rules or [])}
            self.ignore_same_element.setChecked(bool(ignore_map.get(IGNORE_SAME_ELEMENT, True)))
            self.ignore_same_system.setChecked(bool(ignore_map.get(IGNORE_SAME_SYSTEM, False)))
            self.ignore_same_file.setChecked(bool(ignore_map.get(IGNORE_SAME_FILE, False)))
            self.ignore_name_pattern.setChecked(bool(ignore_map.get(IGNORE_NAME_PATTERN, False)))
            pattern_values = self._split_csv_values(ignore_params.get(IGNORE_NAME_PATTERN, {}).get("patterns", []))
            self.ignore_name_pattern_edit.setText(", ".join(pattern_values))
            self.ignore_ifctype_in.setChecked(bool(ignore_map.get(IGNORE_IFCTYPE_IN, False)))
            type_values = self._split_csv_values(ignore_params.get(IGNORE_IFCTYPE_IN, {}).get("types", []))
            self.ignore_ifctype_in_edit.setText(", ".join(type_values))
            self.ignore_name_pattern_edit.setEnabled(bool(self.ignore_name_pattern.isChecked()))
            self.ignore_ifctype_in_edit.setEnabled(bool(self.ignore_ifctype_in.isChecked()))
            self.auto_viewpoint_toggle.setChecked(bool(test.auto_viewpoint))
            self.auto_screenshot_toggle.setChecked(bool(test.auto_screenshot))
            self._on_clash_type_changed()
        finally:
            self._syncing = False

    def build_test(self, base_test: Optional[ClashTest]) -> ClashTest:
        source = base_test or self._test
        if source is None:
            source = ClashTest(id="default", name="Default Clash Test")
        clash_type_raw = str(self.clash_type_combo.currentData() or ClashType.HARD.value)
        try:
            clash_type = ClashType(clash_type_raw)
        except Exception:
            clash_type = ClashType.HARD
        grouping_order = self._selected_grouping_order()
        ignore_rules = [
            IgnoreRule(key=IGNORE_SAME_ELEMENT, enabled=bool(self.ignore_same_element.isChecked())),
            IgnoreRule(key=IGNORE_SAME_SYSTEM, enabled=bool(self.ignore_same_system.isChecked())),
            IgnoreRule(key=IGNORE_SAME_FILE, enabled=bool(self.ignore_same_file.isChecked())),
            IgnoreRule(
                key=IGNORE_NAME_PATTERN,
                enabled=bool(self.ignore_name_pattern.isChecked()),
                params={"patterns": self._split_csv_values(self.ignore_name_pattern_edit.text())},
            ),
            IgnoreRule(
                key=IGNORE_IFCTYPE_IN,
                enabled=bool(self.ignore_ifctype_in.isChecked()),
                params={"types": self._split_csv_values(self.ignore_ifctype_in_edit.text())},
            ),
        ]
        return ClashTest(
            id=str(source.id),
            name=str(source.name),
            search_set_ids_a=self._checked_ids(self.sets_a_list),
            search_set_ids_b=self._checked_ids(self.sets_b_list),
            clash_type=clash_type,
            threshold_mm=float(self.threshold_spin.value()),
            ignore_rules=ignore_rules,
            grouping_order=grouping_order,
            proximity_meters=float(self.proximity_spin.value()),
            auto_viewpoint=bool(self.auto_viewpoint_toggle.isChecked()),
            auto_screenshot=bool(self.auto_screenshot_toggle.isChecked()),
            created_ts=float(source.created_ts or time.time()),
            updated_ts=float(time.time()),
        )

    def _on_advanced_toggled(self, checked: bool) -> None:
        self.advanced_wrap.setVisible(bool(checked))
        self.advanced_toggle.setArrowType(QtCore.Qt.DownArrow if checked else QtCore.Qt.RightArrow)

    def _on_run_clicked(self) -> None:
        self._emit_test_changed()
        self.runRequested.emit()

    def _on_clash_type_changed(self) -> None:
        clash_type = str(self.clash_type_combo.currentData() or ClashType.HARD.value)
        show_threshold = clash_type in (ClashType.CLEARANCE.value, ClashType.TOLERANCE.value)
        self.threshold_spin.setEnabled(show_threshold)
        self.threshold_minus_btn.setEnabled(show_threshold)
        self.threshold_plus_btn.setEnabled(show_threshold)
        if not show_threshold:
            self.threshold_spin.setValue(0.0)
        self._emit_test_changed()

    def _populate_search_set_list(self, target: QtWidgets.QListWidget, selected_ids: Sequence[str]) -> None:
        selected = set(str(v) for v in list(selected_ids or []))
        target.blockSignals(True)
        target.clear()
        for sid, name in list(self._search_sets or []):
            item = QtWidgets.QListWidgetItem(str(name))
            item.setData(QtCore.Qt.UserRole, str(sid))
            item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
            item.setCheckState(QtCore.Qt.Checked if sid in selected else QtCore.Qt.Unchecked)
            target.addItem(item)
        target.blockSignals(False)

    def _checked_ids(self, widget: QtWidgets.QListWidget) -> List[str]:
        ids: List[str] = []
        for idx in range(widget.count()):
            item = widget.item(idx)
            if item is not None and item.checkState() == QtCore.Qt.Checked:
                ids.append(str(item.data(QtCore.Qt.UserRole) or ""))
        return [value for value in ids if value]

    def _ensure_grouping_items(self) -> None:
        if self.grouping_list.count() > 0:
            return
        rows = [
            (GROUP_ELEMENT_A, "Element A", True),
            (GROUP_PROXIMITY, "Proximity", True),
            (GROUP_LEVEL, "Level", True),
        ]
        for key, label, checked in rows:
            item = QtWidgets.QListWidgetItem(label)
            item.setData(QtCore.Qt.UserRole, key)
            item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            item.setCheckState(QtCore.Qt.Checked if checked else QtCore.Qt.Unchecked)
            self.grouping_list.addItem(item)
        if self.grouping_list.count() > 0:
            self.grouping_list.setCurrentRow(0)

    def _selected_grouping_order(self) -> List[str]:
        order: List[str] = []
        for idx in range(self.grouping_list.count()):
            item = self.grouping_list.item(idx)
            if item is None:
                continue
            if item.checkState() != QtCore.Qt.Checked:
                continue
            key = str(item.data(QtCore.Qt.UserRole) or "")
            if key:
                order.append(key)
        if not order:
            order = [GROUP_ELEMENT_A, GROUP_PROXIMITY]
        return order

    def _apply_grouping_order(self, grouping_order: Sequence[str]) -> None:
        wanted = [str(v) for v in list(grouping_order or []) if str(v).strip()]
        if not wanted:
            wanted = [GROUP_ELEMENT_A, GROUP_PROXIMITY]
        label_by_key: Dict[str, str] = {
            GROUP_ELEMENT_A: "Element A",
            GROUP_PROXIMITY: "Proximity",
            GROUP_LEVEL: "Level",
        }
        selected = set(wanted)
        keys = list(wanted)
        for key in (GROUP_ELEMENT_A, GROUP_PROXIMITY, GROUP_LEVEL):
            if key not in keys:
                keys.append(key)
        self.grouping_list.blockSignals(True)
        self.grouping_list.clear()
        for key in keys:
            item = QtWidgets.QListWidgetItem(label_by_key.get(key, key))
            item.setData(QtCore.Qt.UserRole, key)
            item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            item.setCheckState(QtCore.Qt.Checked if key in selected else QtCore.Qt.Unchecked)
            self.grouping_list.addItem(item)
        self.grouping_list.blockSignals(False)
        if self.grouping_list.count() > 0:
            self.grouping_list.setCurrentRow(0)

    def _move_grouping_item(self, delta: int) -> None:
        row = self.grouping_list.currentRow()
        if row < 0:
            return
        target = row + int(delta)
        if target < 0 or target >= self.grouping_list.count():
            return
        item = self.grouping_list.takeItem(row)
        self.grouping_list.insertItem(target, item)
        self.grouping_list.setCurrentRow(target)
        self._emit_test_changed()

    def _on_ignore_name_toggled(self, checked: bool) -> None:
        self.ignore_name_pattern_edit.setEnabled(bool(checked))
        self._emit_test_changed()

    def _on_ignore_ifctype_toggled(self, checked: bool) -> None:
        self.ignore_ifctype_in_edit.setEnabled(bool(checked))
        self._emit_test_changed()

    @staticmethod
    def _split_csv_values(raw: object) -> List[str]:
        if isinstance(raw, str):
            parts = [v.strip() for v in raw.split(",")]
        elif isinstance(raw, (list, tuple, set)):
            parts = [str(v).strip() for v in raw]
        else:
            parts = []
        out: List[str] = []
        seen = set()
        for value in parts:
            token = str(value or "").strip()
            if not token:
                continue
            lowered = token.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            out.append(token)
        return out

    def _emit_test_changed(self) -> None:
        if self._syncing:
            return
        self.testChanged.emit(self.build_test(self._test))


class ClashResultsStep(QtWidgets.QWidget):
    reviewRequested = QtCore.Signal()
    rerunRequested = QtCore.Signal()

    def __init__(self, results_widget: QtWidgets.QWidget, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        summary_row = QtWidgets.QHBoxLayout()
        summary_row.setContentsMargins(0, 0, 0, 0)
        summary_row.setSpacing(8)
        self.summary_label = QtWidgets.QLabel("Run a test to see results")
        self.summary_label.setObjectName("SecondaryText")
        self.sort_combo = QtWidgets.QComboBox(self)
        self.sort_combo.addItem("Sort: Severity", "severity")
        self.sort_combo.addItem("Sort: Count", "count")
        summary_row.addWidget(self.summary_label, 1)
        summary_row.addWidget(self.sort_combo, 0)
        root.addLayout(summary_row, 0)

        self.empty_label = QtWidgets.QLabel("Run a test to see results")
        self.empty_label.setWordWrap(True)
        self.empty_label.setObjectName("SecondaryText")
        root.addWidget(self.empty_label, 0)

        results_widget.setParent(self)
        self.results_widget = results_widget
        root.addWidget(self.results_widget, 1)

        actions_row = QtWidgets.QHBoxLayout()
        actions_row.setContentsMargins(0, 0, 0, 0)
        actions_row.setSpacing(6)
        self.primary_btn = QtWidgets.QPushButton("Review clashes")
        self.primary_btn.setObjectName("WorkflowPrimaryCta")
        self.secondary_btn = QtWidgets.QToolButton(self)
        self.secondary_btn.setText("Re-run test")
        self.secondary_btn.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)
        actions_row.addWidget(self.primary_btn, 1)
        actions_row.addWidget(self.secondary_btn, 0)
        root.addLayout(actions_row, 0)

        self.primary_btn.clicked.connect(self.reviewRequested.emit)
        self.secondary_btn.clicked.connect(self.rerunRequested.emit)

    def set_results_state(
        self,
        *,
        has_run: bool,
        results_count: int,
        active_test_name: str,
        last_run_text: str,
        has_selection: bool,
    ) -> None:
        if not has_run:
            self.summary_label.setText("Run a test to see results")
            self.empty_label.setText("Run a test to see results")
            self.empty_label.setVisible(True)
            self.results_widget.setEnabled(False)
            self.primary_btn.setEnabled(False)
            self.secondary_btn.setEnabled(False)
            self.primary_btn.setText("Review clashes")
            return
        self.summary_label.setText(
            f"{int(results_count)} clashes found · Last run: {last_run_text} · Active test: {active_test_name or '-'}"
        )
        self.empty_label.setVisible(False)
        self.results_widget.setEnabled(True)
        self.primary_btn.setEnabled(int(results_count) > 0)
        self.secondary_btn.setEnabled(True)
        self.primary_btn.setText("Open next clash" if has_selection else "Review clashes")


class ClashFixStep(QtWidgets.QWidget):
    primaryRequested = QtCore.Signal()
    goToClashRequested = QtCore.Signal()
    showAlternativesRequested = QtCore.Signal()
    markApprovedRequested = QtCore.Signal()
    assignRequested = QtCore.Signal()
    explainRequested = QtCore.Signal()

    def __init__(self, issue_widget: QtWidgets.QWidget, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        self.empty_label = QtWidgets.QLabel("Run a test to see results")
        self.empty_label.setWordWrap(True)
        self.empty_label.setObjectName("SecondaryText")
        root.addWidget(self.empty_label, 0)

        self.ai_summary = QtWidgets.QLabel("AI summary will appear when a clash is selected.")
        self.ai_summary.setWordWrap(True)
        self.ai_summary.setObjectName("SecondaryText")
        root.addWidget(self.ai_summary, 0)

        issue_widget.setParent(self)
        self.issue_widget = issue_widget
        self.issue_widget.setVisible(True)
        root.addWidget(self.issue_widget, 1)

        actions_row = QtWidgets.QHBoxLayout()
        actions_row.setContentsMargins(0, 0, 0, 0)
        actions_row.setSpacing(6)
        self.primary_btn = QtWidgets.QPushButton("Generate fixes")
        self.primary_btn.setObjectName("WorkflowPrimaryCta")
        self.go_to_clash_btn = QtWidgets.QToolButton(self)
        self.go_to_clash_btn.setText("Go to clash")
        self.go_to_clash_btn.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)
        self.alternatives_btn = QtWidgets.QToolButton(self)
        self.alternatives_btn.setText("Show alternatives")
        self.alternatives_btn.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)
        self.approve_btn = QtWidgets.QToolButton(self)
        self.approve_btn.setText("Mark as approved")
        self.approve_btn.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)
        self.assign_btn = QtWidgets.QToolButton(self)
        self.assign_btn.setText("Assign")
        self.assign_btn.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)
        self.explain_btn = QtWidgets.QToolButton(self)
        self.explain_btn.setText("Explain / Suggest fix")
        self.explain_btn.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)
        actions_row.addWidget(self.primary_btn, 1)
        actions_row.addWidget(self.go_to_clash_btn, 0)
        actions_row.addWidget(self.alternatives_btn, 0)
        actions_row.addWidget(self.approve_btn, 0)
        actions_row.addWidget(self.assign_btn, 0)
        actions_row.addWidget(self.explain_btn, 0)
        root.addLayout(actions_row, 0)

        self.primary_btn.clicked.connect(self.primaryRequested.emit)
        self.go_to_clash_btn.clicked.connect(self.goToClashRequested.emit)
        self.alternatives_btn.clicked.connect(self.showAlternativesRequested.emit)
        self.approve_btn.clicked.connect(self.markApprovedRequested.emit)
        self.assign_btn.clicked.connect(self.assignRequested.emit)
        self.explain_btn.clicked.connect(self.explainRequested.emit)

    def set_ai_summary(self, text: str) -> None:
        self.ai_summary.setText(str(text or "AI summary will appear when a clash is selected."))

    def set_fix_state(self, *, has_run: bool, clash_selected: bool, has_suggested_fix: bool) -> None:
        if not has_run:
            self.empty_label.setText("Run a test to see results")
            self.empty_label.setVisible(True)
            self.issue_widget.setEnabled(False)
            self.primary_btn.setEnabled(False)
            self.primary_btn.setText("Generate fixes")
            self.go_to_clash_btn.setEnabled(False)
            for btn in (self.alternatives_btn, self.approve_btn, self.assign_btn, self.explain_btn):
                btn.setEnabled(False)
            return
        if not clash_selected:
            self.empty_label.setText("Select a clash in Results")
            self.empty_label.setVisible(True)
            self.issue_widget.setEnabled(False)
            self.primary_btn.setEnabled(False)
            self.primary_btn.setText("Generate fixes")
            self.go_to_clash_btn.setEnabled(False)
            for btn in (self.alternatives_btn, self.approve_btn, self.assign_btn, self.explain_btn):
                btn.setEnabled(False)
            return
        self.empty_label.setVisible(False)
        self.issue_widget.setEnabled(True)
        if has_suggested_fix:
            self.primary_btn.setText("Apply suggested fix")
        else:
            self.primary_btn.setText("Generate fixes")
        self.primary_btn.setEnabled(True)
        self.go_to_clash_btn.setEnabled(True)
        for btn in (self.alternatives_btn, self.approve_btn, self.assign_btn, self.explain_btn):
            btn.setEnabled(True)


class ClashDetectionPanel(BasePanel):
    stepChanged = QtCore.Signal(str)
    testUpdated = QtCore.Signal(object)
    runRequested = QtCore.Signal()
    reviewRequested = QtCore.Signal()
    rerunRequested = QtCore.Signal()
    generateFixesRequested = QtCore.Signal()
    applySuggestedFixRequested = QtCore.Signal()
    goToClashRequested = QtCore.Signal()
    showAlternativesRequested = QtCore.Signal()
    markApprovedRequested = QtCore.Signal()
    assignRequested = QtCore.Signal()
    explainRequested = QtCore.Signal()
    advancedRequested = QtCore.Signal()

    def __init__(
        self,
        tests_widget: QtWidgets.QWidget,
        results_widget: QtWidgets.QWidget,
        issue_widget: QtWidgets.QWidget,
        parent: Optional[QtWidgets.QWidget] = None,
    ):
        super().__init__("Clash Detection", parent)
        self.setObjectName("ClashDetectionPanel")
        self._state = ClashWorkflowState(activeStep="setup")
        self._active_test: Optional[ClashTest] = None
        self._model_loaded = False
        self._has_suggested_fix = False
        self._has_clash_selection = False

        body = QtWidgets.QWidget(self)
        root = QtWidgets.QVBoxLayout(body)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        self.header = QtWidgets.QLabel("Clash Detection")
        self.header.setObjectName("ClashPanelHeader")
        root.addWidget(self.header, 0)

        # Keep BasePanel.tabs for top-level panel tabs; use a dedicated name
        # for the workflow tabs to avoid parent/child cycles during add_tab().
        self.workflow_tabs = QtWidgets.QTabWidget(body)
        self.workflow_tabs.setObjectName("ClashWorkflowTabs")
        root.addWidget(self.workflow_tabs, 1)

        self.setup_step = ClashSetupStep(advanced_widget=tests_widget, parent=self.workflow_tabs)
        self.results_step = ClashResultsStep(results_widget=results_widget, parent=self.workflow_tabs)
        self.fix_step = ClashFixStep(issue_widget=issue_widget, parent=self.workflow_tabs)
        self.workflow_tabs.addTab(self.setup_step, "Setup")
        self.workflow_tabs.addTab(self.results_step, "Results")
        self.workflow_tabs.addTab(self.fix_step, "Fix")

        self.setup_step.testChanged.connect(self.testUpdated.emit)
        self.setup_step.runRequested.connect(self.runRequested.emit)
        self.setup_step.advancedRequested.connect(self.advancedRequested.emit)
        self.results_step.reviewRequested.connect(self.reviewRequested.emit)
        self.results_step.rerunRequested.connect(self.rerunRequested.emit)
        self.fix_step.showAlternativesRequested.connect(self.showAlternativesRequested.emit)
        self.fix_step.markApprovedRequested.connect(self.markApprovedRequested.emit)
        self.fix_step.assignRequested.connect(self.assignRequested.emit)
        self.fix_step.explainRequested.connect(self.explainRequested.emit)
        self.fix_step.goToClashRequested.connect(self.goToClashRequested.emit)
        self.fix_step.primaryRequested.connect(self._on_fix_primary_clicked)
        self.workflow_tabs.currentChanged.connect(self._on_tab_changed)
        self._sync_ui()
        self.add_tab("clash_workflow", "Clash", body)

    def set_model_loaded(self, loaded: bool) -> None:
        self._model_loaded = bool(loaded)
        self.setup_step.set_model_loaded(self._model_loaded)
        self._sync_ui()

    def set_available_search_sets(self, search_sets: Sequence[Tuple[str, str]]) -> None:
        self.setup_step.set_available_search_sets(search_sets)

    def set_active_test(self, test: Optional[ClashTest]) -> None:
        self._active_test = test
        if test is not None:
            self.setup_step.set_test(test)
        self._sync_ui()

    def set_workflow_state(self, state: ClashWorkflowState) -> None:
        self._state = state
        self._sync_ui()

    def set_has_suggested_fix(self, has_fix: bool) -> None:
        self._has_suggested_fix = bool(has_fix)
        self._sync_ui()

    def set_clash_selected(self, has_selection: bool) -> None:
        self._has_clash_selection = bool(has_selection)
        self._sync_ui()

    def set_ai_summary(self, text: str) -> None:
        self.fix_step.set_ai_summary(text)

    def current_step(self) -> str:
        idx = self.workflow_tabs.currentIndex()
        if idx == 1:
            return "results"
        if idx == 2:
            return "fix"
        return "setup"

    def _on_fix_primary_clicked(self) -> None:
        if self._has_suggested_fix:
            self.applySuggestedFixRequested.emit()
        else:
            self.generateFixesRequested.emit()

    def _on_tab_changed(self, index: int) -> None:
        step = "setup"
        if index == 1:
            step = "results"
        elif index == 2:
            step = "fix"
        self.stepChanged.emit(step)

    def _sync_ui(self) -> None:
        has_run = bool(self._state.lastRun is not None)
        results_count = int(self._state.lastRun.results_count) if self._state.lastRun is not None else 0
        run_time = "-"
        if self._state.lastRun is not None and float(self._state.lastRun.time or 0.0) > 0.0:
            run_time = QtCore.QDateTime.fromSecsSinceEpoch(int(self._state.lastRun.time)).toString("yyyy-MM-dd HH:mm:ss")
        active_test_name = str(self._active_test.name if self._active_test is not None else "-")

        self.workflow_tabs.setTabEnabled(0, True)
        self.workflow_tabs.setTabEnabled(1, has_run)
        self.workflow_tabs.setTabEnabled(2, has_run)
        self.results_step.set_results_state(
            has_run=has_run,
            results_count=results_count,
            active_test_name=active_test_name,
            last_run_text=run_time,
            has_selection=self._has_clash_selection,
        )
        self.fix_step.set_fix_state(
            has_run=has_run,
            clash_selected=self._has_clash_selection,
            has_suggested_fix=self._has_suggested_fix,
        )

        wanted = str(self._state.activeStep or "setup").lower().strip()
        wanted_idx = 0
        if wanted == "results":
            wanted_idx = 1
        elif wanted == "fix":
            wanted_idx = 2
        if not self.workflow_tabs.isTabEnabled(wanted_idx):
            wanted_idx = 0
        if self.workflow_tabs.currentIndex() != wanted_idx:
            self.workflow_tabs.blockSignals(True)
            self.workflow_tabs.setCurrentIndex(wanted_idx)
            self.workflow_tabs.blockSignals(False)
