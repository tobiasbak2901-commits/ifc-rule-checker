from __future__ import annotations

from dataclasses import replace
import time
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from PySide6 import QtCore, QtWidgets

from clash_tests.models import (
    ClashTest,
    ClashType,
    GROUP_ELEMENT_A,
    GROUP_LEVEL,
    GROUP_PROXIMITY,
    IGNORE_IFCTYPE_IN,
    IGNORE_NAME_PATTERN,
    IGNORE_SAME_ELEMENT,
    IGNORE_SAME_FILE,
    IGNORE_SAME_SYSTEM,
    IgnoreRule,
)


_IGNORE_LABELS = {
    IGNORE_SAME_ELEMENT: "Ignore if same element",
    IGNORE_SAME_SYSTEM: "Ignore if same system",
    IGNORE_SAME_FILE: "Ignore if same file/model",
    IGNORE_NAME_PATTERN: "Exclude if name contains pattern",
    IGNORE_IFCTYPE_IN: "Exclude if ifcType in list",
}

_GROUP_LABELS = {
    GROUP_ELEMENT_A: "Element A",
    GROUP_PROXIMITY: "Proximity",
    GROUP_LEVEL: "Level",
}


class ClashTestSettingsDialog(QtWidgets.QDialog):
    def __init__(
        self,
        *,
        parent: Optional[QtWidgets.QWidget],
        clash_test: ClashTest,
        search_sets: Sequence[Tuple[str, str]],
        level_available: bool,
    ):
        super().__init__(parent)
        self.setWindowTitle("Clash test settings")
        self.setModal(True)
        self.resize(760, 660)
        self._source = clash_test
        self._search_sets = [(str(sid), str(name)) for sid, name in list(search_sets or []) if sid]
        self._level_available = bool(level_available)

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        form = QtWidgets.QFormLayout()
        form.setLabelAlignment(QtCore.Qt.AlignLeft)
        form.setFormAlignment(QtCore.Qt.AlignTop)
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(10)

        self.name_edit = QtWidgets.QLineEdit(clash_test.name)
        form.addRow("Name", self.name_edit)

        self.type_combo = QtWidgets.QComboBox()
        self.type_combo.addItem("Hard clash (intersection)", ClashType.HARD.value)
        self.type_combo.addItem("Tolerance (allow overlap up to tolerance_mm)", ClashType.TOLERANCE.value)
        self.type_combo.addItem("Clearance (clash if min distance < clearance_mm)", ClashType.CLEARANCE.value)
        self._set_combo_data(self.type_combo, clash_test.clash_type.value)
        form.addRow("Clashing type", self.type_combo)

        self.threshold_spin = QtWidgets.QDoubleSpinBox()
        self.threshold_spin.setDecimals(1)
        self.threshold_spin.setRange(0.0, 5000.0)
        self.threshold_spin.setSingleStep(5.0)
        self.threshold_spin.setSuffix(" mm")
        self.threshold_spin.setValue(float(clash_test.threshold_mm or 0.0))
        form.addRow("Type value", self.threshold_spin)

        root.addLayout(form)

        sets_group = QtWidgets.QGroupBox("Search sets")
        sets_layout = QtWidgets.QHBoxLayout(sets_group)
        sets_layout.setContentsMargins(10, 10, 10, 10)
        sets_layout.setSpacing(12)
        self.sets_a_list = QtWidgets.QListWidget()
        self.sets_b_list = QtWidgets.QListWidget()
        self.sets_a_list.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.sets_b_list.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.sets_a_list.setMinimumHeight(140)
        self.sets_b_list.setMinimumHeight(140)

        a_wrap = QtWidgets.QVBoxLayout()
        a_wrap.addWidget(QtWidgets.QLabel("Search sets A"), 0)
        a_wrap.addWidget(self.sets_a_list, 1)
        b_wrap = QtWidgets.QVBoxLayout()
        b_wrap.addWidget(QtWidgets.QLabel("Search sets B"), 0)
        b_wrap.addWidget(self.sets_b_list, 1)

        sets_layout.addLayout(a_wrap, 1)
        sets_layout.addLayout(b_wrap, 1)
        root.addWidget(sets_group, 0)

        self._populate_sets(self.sets_a_list, clash_test.search_set_ids_a)
        self._populate_sets(self.sets_b_list, clash_test.search_set_ids_b)

        ignore_group = QtWidgets.QGroupBox("Ignore rules")
        ignore_layout = QtWidgets.QVBoxLayout(ignore_group)
        ignore_layout.setContentsMargins(10, 10, 10, 10)
        ignore_layout.setSpacing(8)
        self.ignore_rules_list = QtWidgets.QListWidget()
        self.ignore_rules_list.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.ignore_rules_list.setMinimumHeight(120)
        ignore_layout.addWidget(self.ignore_rules_list, 1)

        row = QtWidgets.QHBoxLayout()
        self.ignore_add_combo = QtWidgets.QComboBox()
        self.ignore_add_btn = QtWidgets.QPushButton("Add")
        self.ignore_remove_btn = QtWidgets.QPushButton("Remove")
        row.addWidget(self.ignore_add_combo, 1)
        row.addWidget(self.ignore_add_btn, 0)
        row.addWidget(self.ignore_remove_btn, 0)
        ignore_layout.addLayout(row, 0)
        root.addWidget(ignore_group, 0)

        self._populate_ignore_rules(clash_test.ignore_rules)
        self.ignore_add_btn.clicked.connect(self._on_add_ignore_rule)
        self.ignore_remove_btn.clicked.connect(self._on_remove_ignore_rule)

        grouping_group = QtWidgets.QGroupBox("Grouping")
        grouping_layout = QtWidgets.QVBoxLayout(grouping_group)
        grouping_layout.setContentsMargins(10, 10, 10, 10)
        grouping_layout.setSpacing(8)

        self.grouping_list = QtWidgets.QListWidget()
        self.grouping_list.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.grouping_list.setDragDropMode(QtWidgets.QAbstractItemView.NoDragDrop)
        self.grouping_list.setMinimumHeight(120)

        controls = QtWidgets.QHBoxLayout()
        self.group_up_btn = QtWidgets.QPushButton("Move up")
        self.group_down_btn = QtWidgets.QPushButton("Move down")
        controls.addWidget(self.group_up_btn, 0)
        controls.addWidget(self.group_down_btn, 0)
        controls.addStretch(1)

        proximity_row = QtWidgets.QHBoxLayout()
        proximity_row.addWidget(QtWidgets.QLabel("Proximity cell size"), 0)
        self.proximity_spin = QtWidgets.QDoubleSpinBox()
        self.proximity_spin.setDecimals(2)
        self.proximity_spin.setRange(0.25, 250.0)
        self.proximity_spin.setSingleStep(0.5)
        self.proximity_spin.setSuffix(" m")
        self.proximity_spin.setValue(float(clash_test.proximity_meters or 6.0))
        proximity_row.addWidget(self.proximity_spin, 0)
        proximity_row.addStretch(1)

        grouping_layout.addWidget(self.grouping_list, 1)
        grouping_layout.addLayout(controls)
        grouping_layout.addLayout(proximity_row)
        root.addWidget(grouping_group, 0)

        self._populate_grouping(clash_test.grouping_order)
        self.group_up_btn.clicked.connect(lambda: self._move_group_item(-1))
        self.group_down_btn.clicked.connect(lambda: self._move_group_item(1))

        view_group = QtWidgets.QGroupBox("View & screenshot")
        view_layout = QtWidgets.QVBoxLayout(view_group)
        view_layout.setContentsMargins(10, 10, 10, 10)
        self.auto_viewpoint_cb = QtWidgets.QCheckBox("Auto-generate viewpoint for each clash")
        self.auto_viewpoint_cb.setChecked(bool(clash_test.auto_viewpoint))
        self.auto_screenshot_cb = QtWidgets.QCheckBox("Auto-screenshot (stores metadata; image capture is currently TODO)")
        self.auto_screenshot_cb.setChecked(bool(clash_test.auto_screenshot))
        view_layout.addWidget(self.auto_viewpoint_cb, 0)
        view_layout.addWidget(self.auto_screenshot_cb, 0)
        root.addWidget(view_group, 0)

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons, 0)

        self.type_combo.currentIndexChanged.connect(self._update_threshold_enabled)
        self.grouping_list.itemChanged.connect(self._update_proximity_enabled)
        self._update_threshold_enabled()
        self._update_proximity_enabled()

    def build_test(self) -> ClashTest:
        test = replace(self._source)
        test.name = str(self.name_edit.text() or "").strip() or "Clash Test"
        type_raw = str(self.type_combo.currentData() or ClashType.HARD.value)
        try:
            test.clash_type = ClashType(type_raw)
        except Exception:
            test.clash_type = ClashType.HARD
        test.threshold_mm = float(self.threshold_spin.value())
        test.search_set_ids_a = self._checked_set_ids(self.sets_a_list)
        test.search_set_ids_b = self._checked_set_ids(self.sets_b_list)
        test.ignore_rules = self._current_ignore_rules()
        test.grouping_order = self._current_grouping_order()
        test.proximity_meters = float(self.proximity_spin.value())
        test.auto_viewpoint = bool(self.auto_viewpoint_cb.isChecked())
        test.auto_screenshot = bool(self.auto_screenshot_cb.isChecked())
        test.updated_ts = float(time.time())
        if not test.created_ts:
            test.created_ts = test.updated_ts
        return test

    def _populate_sets(self, target: QtWidgets.QListWidget, selected_ids: Sequence[str]) -> None:
        selected = {str(v) for v in list(selected_ids or [])}
        target.clear()
        for set_id, name in self._search_sets:
            item = QtWidgets.QListWidgetItem(str(name))
            item.setData(QtCore.Qt.UserRole, str(set_id))
            item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
            item.setCheckState(QtCore.Qt.Checked if set_id in selected else QtCore.Qt.Unchecked)
            target.addItem(item)

    def _checked_set_ids(self, target: QtWidgets.QListWidget) -> List[str]:
        selected: List[str] = []
        for row in range(target.count()):
            item = target.item(row)
            if item and item.checkState() == QtCore.Qt.Checked:
                selected.append(str(item.data(QtCore.Qt.UserRole) or ""))
        return [v for v in selected if v]

    def _populate_ignore_rules(self, rules: Sequence[IgnoreRule]) -> None:
        self.ignore_rules_list.clear()
        by_key: Dict[str, IgnoreRule] = {str(rule.key): rule for rule in list(rules or [])}
        for key in (IGNORE_SAME_ELEMENT, IGNORE_SAME_SYSTEM, IGNORE_SAME_FILE, IGNORE_NAME_PATTERN, IGNORE_IFCTYPE_IN):
            if key not in by_key:
                continue
            self._add_ignore_item(by_key[key])
        self._refresh_ignore_add_combo()

    def _add_ignore_item(self, rule: IgnoreRule) -> None:
        label = _IGNORE_LABELS.get(str(rule.key), str(rule.key))
        item = QtWidgets.QListWidgetItem(label)
        item.setData(QtCore.Qt.UserRole, str(rule.key))
        item.setData(QtCore.Qt.UserRole + 1, dict(rule.params or {}))
        item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
        item.setCheckState(QtCore.Qt.Checked if rule.enabled else QtCore.Qt.Unchecked)
        self.ignore_rules_list.addItem(item)

    def _refresh_ignore_add_combo(self) -> None:
        current = {
            str(self.ignore_rules_list.item(row).data(QtCore.Qt.UserRole) or "")
            for row in range(self.ignore_rules_list.count())
        }
        self.ignore_add_combo.clear()
        for key in (IGNORE_SAME_ELEMENT, IGNORE_SAME_SYSTEM, IGNORE_SAME_FILE, IGNORE_NAME_PATTERN, IGNORE_IFCTYPE_IN):
            if key in current:
                continue
            self.ignore_add_combo.addItem(_IGNORE_LABELS.get(key, key), key)
        self.ignore_add_btn.setEnabled(self.ignore_add_combo.count() > 0)
        self.ignore_remove_btn.setEnabled(self.ignore_rules_list.count() > 0)

    def _on_add_ignore_rule(self) -> None:
        key = str(self.ignore_add_combo.currentData() or "")
        if not key:
            return
        self._add_ignore_item(IgnoreRule(key=key, enabled=True))
        self._refresh_ignore_add_combo()

    def _on_remove_ignore_rule(self) -> None:
        row = self.ignore_rules_list.currentRow()
        if row < 0:
            return
        self.ignore_rules_list.takeItem(row)
        self._refresh_ignore_add_combo()

    def _current_ignore_rules(self) -> List[IgnoreRule]:
        rules: List[IgnoreRule] = []
        for row in range(self.ignore_rules_list.count()):
            item = self.ignore_rules_list.item(row)
            if not item:
                continue
            key = str(item.data(QtCore.Qt.UserRole) or "")
            if not key:
                continue
            params = item.data(QtCore.Qt.UserRole + 1)
            rules.append(
                IgnoreRule(
                    key=key,
                    enabled=item.checkState() == QtCore.Qt.Checked,
                    params=dict(params or {}),
                )
            )
        return rules

    def _populate_grouping(self, order: Sequence[str]) -> None:
        self.grouping_list.clear()
        enabled = [str(v) for v in list(order or []) if str(v).strip()]
        if not enabled:
            enabled = [GROUP_ELEMENT_A, GROUP_PROXIMITY]
            if self._level_available:
                enabled.append(GROUP_LEVEL)

        for key in (GROUP_ELEMENT_A, GROUP_PROXIMITY, GROUP_LEVEL):
            item = QtWidgets.QListWidgetItem(_GROUP_LABELS.get(key, key))
            item.setData(QtCore.Qt.UserRole, key)
            item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
            item.setCheckState(QtCore.Qt.Checked if key in enabled else QtCore.Qt.Unchecked)
            if key == GROUP_LEVEL and not self._level_available:
                item.setCheckState(QtCore.Qt.Unchecked)
                item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEnabled)
                item.setToolTip("No level data found. Falls back to UnknownLevel during detection.")
            self.grouping_list.addItem(item)

        if self.grouping_list.count() > 0:
            self.grouping_list.setCurrentRow(0)

        self._reorder_grouping(enabled)

    def _reorder_grouping(self, enabled_order: Sequence[str]) -> None:
        wanted = [str(v) for v in list(enabled_order or [])]
        for key in reversed(wanted):
            for row in range(self.grouping_list.count()):
                item = self.grouping_list.item(row)
                if str(item.data(QtCore.Qt.UserRole) or "") != key:
                    continue
                cloned = self.grouping_list.takeItem(row)
                self.grouping_list.insertItem(0, cloned)
                break

    def _move_group_item(self, direction: int) -> None:
        row = self.grouping_list.currentRow()
        if row < 0:
            return
        target = row + int(direction)
        if target < 0 or target >= self.grouping_list.count():
            return
        item = self.grouping_list.takeItem(row)
        self.grouping_list.insertItem(target, item)
        self.grouping_list.setCurrentRow(target)

    def _current_grouping_order(self) -> List[str]:
        order: List[str] = []
        for row in range(self.grouping_list.count()):
            item = self.grouping_list.item(row)
            if not item or item.checkState() != QtCore.Qt.Checked:
                continue
            key = str(item.data(QtCore.Qt.UserRole) or "")
            if key:
                order.append(key)
        return order

    def _update_threshold_enabled(self) -> None:
        mode = str(self.type_combo.currentData() or ClashType.HARD.value)
        is_hard = mode == ClashType.HARD.value
        self.threshold_spin.setEnabled(not is_hard)
        if is_hard:
            self.threshold_spin.setToolTip("Hard clash ignores threshold value.")
        elif mode == ClashType.TOLERANCE.value:
            self.threshold_spin.setToolTip("Tolerance in mm for allowed overlap.")
        else:
            self.threshold_spin.setToolTip("Required minimum clearance in mm.")

    def _update_proximity_enabled(self) -> None:
        enabled = False
        for row in range(self.grouping_list.count()):
            item = self.grouping_list.item(row)
            if str(item.data(QtCore.Qt.UserRole) or "") == GROUP_PROXIMITY:
                enabled = item.checkState() == QtCore.Qt.Checked
                break
        self.proximity_spin.setEnabled(enabled)

    @staticmethod
    def _set_combo_data(combo: QtWidgets.QComboBox, data_value: str) -> None:
        wanted = str(data_value or "")
        for idx in range(combo.count()):
            if str(combo.itemData(idx) or "") == wanted:
                combo.setCurrentIndex(idx)
                return
        combo.setCurrentIndex(0)
