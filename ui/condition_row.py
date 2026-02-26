from __future__ import annotations

from typing import Callable, Dict, List, Mapping, Optional, Sequence

from PySide6 import QtCore, QtGui, QtWidgets
from ui.searchable_dropdown import SearchableDropdown
from ui.value_picker import MultiValuePickerEditor


class ConditionRow(QtWidgets.QFrame):
    changed = QtCore.Signal()
    removeRequested = QtCore.Signal(object)
    _PROGRESSIVE_STEP_ITEM = 1
    _PROGRESSIVE_STEP_PROPERTY = 2
    _PROGRESSIVE_STEP_OPERATION = 3
    _PROGRESSIVE_STEP_VALUE = 4
    _PROGRESSIVE_PLACEHOLDER_CATEGORY = "__find_objects_choose_item__"
    _PROGRESSIVE_PLACEHOLDER_PROPERTY = "__find_objects_choose_property__"
    _PROGRESSIVE_PLACEHOLDER_OPERATOR = "__find_objects_choose_operation__"
    _PROGRESSIVE_PLACEHOLDER_VALUE = "__find_objects_choose_value__"

    _OPERATORS: tuple[tuple[str, str], ...] = (
        ("equals", "equals"),
        ("in list", "in_list"),
        ("contains", "contains"),
        ("starts with", "starts_with"),
        ("ends with", "ends_with"),
        ("exists", "exists"),
        ("greater than", "greater_than"),
        ("less than", "less_than"),
    )
    _PROPERTY_SPECS: Dict[str, Dict[str, object]] = {
        "name": {"category": "item", "kind": "enum_dynamic"},
        "type": {"category": "item", "kind": "enum_dynamic"},
        "system": {"category": "item", "kind": "string"},
        "layer": {"category": "ifc", "kind": "enum_dynamic"},
        "global_id": {"category": "item", "kind": "string"},
        "source_file": {"category": "item", "kind": "string"},
        "diameter_mm": {"category": "constraints", "kind": "number", "unit": "mm"},
        "length_m": {"category": "constraints", "kind": "number", "unit": "m"},
        "is_classified": {"category": "ifc", "kind": "boolean"},
        "classification": {"category": "ifc", "kind": "string"},
        "discipline": {
            "category": "ifc",
            "kind": "enum",
            "choices": ["Plumbing", "HVAC", "Electrical", "Fire", "Architecture", "Structure"],
        },
        "ai_status": {
            "category": "ai",
            "kind": "enum",
            "choices": ["ok", "warning", "critical", "unknown"],
        },
        "risk_level": {
            "category": "ai",
            "kind": "enum",
            "choices": ["low", "medium", "high"],
        },
        "constraint": {
            "category": "constraints",
            "kind": "enum",
            "choices": ["clearance", "diameter", "slope", "classification"],
        },
    }
    _CATEGORY_LABELS: Dict[str, str] = {
        "item": "Item",
        "ifc": "IFC",
        "ai": "AI",
        "constraints": "Constraints",
    }
    # Operator keys shown per property kind — subset of _OPERATORS keys.
    _OPERATORS_FOR_KIND: Dict[str, List[str]] = {
        "number":       ["equals", "greater_than", "less_than", "exists"],
        "string":       ["contains", "starts_with", "ends_with", "equals", "in_list", "exists"],
        "boolean":      ["equals", "exists"],
        "enum":         ["equals", "in_list", "exists"],
        "enum_dynamic": ["equals", "contains", "starts_with", "ends_with", "in_list", "exists"],
    }

    def __init__(
        self,
        property_options: Sequence[tuple[str, str]] | Sequence[Mapping[str, object]],
        parent: Optional[QtWidgets.QWidget] = None,
        *,
        distinct_values_provider: Optional[Callable[[str], Sequence[str]]] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("FindObjectsConditionRow")
        self.setMinimumHeight(34)
        self.setMaximumHeight(40)
        self._label_to_key: Dict[str, str] = {}
        self._property_catalog: List[Dict[str, str]] = []
        self._updating_value_editor = False
        self._suppress_interaction_events = True
        self._has_user_interaction = False
        self._default_property_key = ""
        self._default_operator_key = ""
        self._default_category_key = ""
        self._progressive_enabled = True
        self._progressive_step = self._PROGRESSIVE_STEP_ITEM
        self._progressive_reset_operator = False
        self._progressive_collapsed = False
        self._number_validator = QtGui.QDoubleValidator(self)
        self._number_validator.setNotation(QtGui.QDoubleValidator.StandardNotation)
        self._distinct_values_provider = distinct_values_provider

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.category_combo = SearchableDropdown(self)
        self.category_combo.setObjectName("FindObjectsCategoryCombo")
        self.category_combo.view().setObjectName("FindObjectsComboPopup")
        self.category_combo.view().setProperty("themeScope", "app")
        self.category_combo.set_popup_titles(recent="Recent", all_items="Categories")
        self.category_combo.set_search_placeholder("Search categories")
        self.category_combo.set_recent_settings_key("findObjects/recent/categories")
        self.category_combo.setMinimumHeight(32)
        self.category_combo.setMinimumWidth(96)
        layout.addWidget(self.category_combo, 1)

        self.item_chip_frame = QtWidgets.QFrame(self)
        self.item_chip_frame.setObjectName("FindObjectsConditionStepChipFrame")
        item_chip_layout = QtWidgets.QHBoxLayout(self.item_chip_frame)
        item_chip_layout.setContentsMargins(8, 2, 8, 2)
        item_chip_layout.setSpacing(6)
        self.item_chip_label = QtWidgets.QLabel("", self.item_chip_frame)
        self.item_chip_label.setObjectName("FindObjectsConditionStepChipLabel")
        self.item_chip_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.item_chip_edit_btn = QtWidgets.QToolButton(self.item_chip_frame)
        self.item_chip_edit_btn.setObjectName("FindObjectsConditionStepChipEditBtn")
        self.item_chip_edit_btn.setText("✎")
        self.item_chip_edit_btn.setAutoRaise(True)
        self.item_chip_edit_btn.setToolTip("Edit item")
        item_chip_layout.addWidget(self.item_chip_label, 1)
        item_chip_layout.addWidget(self.item_chip_edit_btn, 0, QtCore.Qt.AlignVCenter)
        self.item_chip_frame.setVisible(False)
        layout.addWidget(self.item_chip_frame, 1)

        self.property_combo = SearchableDropdown(self)
        self.property_combo.setObjectName("FindObjectsPropertyCombo")
        self._property_catalog = self._normalize_property_options(property_options)
        self._rebuild_category_items()
        self.property_combo.view().setObjectName("FindObjectsComboPopup")
        self.property_combo.view().setProperty("themeScope", "app")
        self.property_combo.set_popup_titles(recent="Recent", all_items="Properties")
        self.property_combo.set_search_placeholder("Search properties")
        self.property_combo.set_recent_settings_key("findObjects/recent/properties")
        self.property_combo.setMinimumHeight(32)
        layout.addWidget(self.property_combo, 2)

        self.property_chip_frame = QtWidgets.QFrame(self)
        self.property_chip_frame.setObjectName("FindObjectsConditionStepChipFrame")
        property_chip_layout = QtWidgets.QHBoxLayout(self.property_chip_frame)
        property_chip_layout.setContentsMargins(8, 2, 8, 2)
        property_chip_layout.setSpacing(6)
        self.property_chip_label = QtWidgets.QLabel("", self.property_chip_frame)
        self.property_chip_label.setObjectName("FindObjectsConditionStepChipLabel")
        self.property_chip_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.property_chip_edit_btn = QtWidgets.QToolButton(self.property_chip_frame)
        self.property_chip_edit_btn.setObjectName("FindObjectsConditionStepChipEditBtn")
        self.property_chip_edit_btn.setText("✎")
        self.property_chip_edit_btn.setAutoRaise(True)
        self.property_chip_edit_btn.setToolTip("Edit property")
        property_chip_layout.addWidget(self.property_chip_label, 1)
        property_chip_layout.addWidget(self.property_chip_edit_btn, 0, QtCore.Qt.AlignVCenter)
        self.property_chip_frame.setVisible(False)
        layout.addWidget(self.property_chip_frame, 2)

        self.operator_combo = QtWidgets.QComboBox(self)
        self.operator_combo.setObjectName("FindObjectsOperatorCombo")
        for label, value in self._OPERATORS:
            self.operator_combo.addItem(label, value)
        self.operator_combo.view().setObjectName("FindObjectsComboPopup")
        self.operator_combo.view().setProperty("themeScope", "app")
        self.operator_combo.setMinimumHeight(32)
        layout.addWidget(self.operator_combo, 1)

        self.operator_chip_frame = QtWidgets.QFrame(self)
        self.operator_chip_frame.setObjectName("FindObjectsConditionStepChipFrame")
        operator_chip_layout = QtWidgets.QHBoxLayout(self.operator_chip_frame)
        operator_chip_layout.setContentsMargins(8, 2, 8, 2)
        operator_chip_layout.setSpacing(6)
        self.operator_chip_label = QtWidgets.QLabel("", self.operator_chip_frame)
        self.operator_chip_label.setObjectName("FindObjectsConditionStepChipLabel")
        self.operator_chip_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.operator_chip_edit_btn = QtWidgets.QToolButton(self.operator_chip_frame)
        self.operator_chip_edit_btn.setObjectName("FindObjectsConditionStepChipEditBtn")
        self.operator_chip_edit_btn.setText("✎")
        self.operator_chip_edit_btn.setAutoRaise(True)
        self.operator_chip_edit_btn.setToolTip("Edit operation")
        operator_chip_layout.addWidget(self.operator_chip_label, 1)
        operator_chip_layout.addWidget(self.operator_chip_edit_btn, 0, QtCore.Qt.AlignVCenter)
        self.operator_chip_frame.setVisible(False)
        layout.addWidget(self.operator_chip_frame, 1)

        self.value_input = QtWidgets.QLineEdit(self)
        self.value_input.setObjectName("FindObjectsValueInput")
        self.value_input.setPlaceholderText("Value")
        self.value_input.setMinimumHeight(32)

        self.value_enum_combo = SearchableDropdown(self)
        self.value_enum_combo.setObjectName("FindObjectsValueEnumCombo")
        self.value_enum_combo.view().setObjectName("FindObjectsComboPopup")
        self.value_enum_combo.view().setProperty("themeScope", "app")
        self.value_enum_combo.set_popup_titles(recent="Recent", all_items="Values")
        self.value_enum_combo.set_search_placeholder("Search values")
        self.value_enum_combo.set_recent_settings_key("findObjects/recent/values")
        self.value_enum_combo.setMinimumHeight(32)

        self.value_choice_combo = QtWidgets.QComboBox(self)
        self.value_choice_combo.setObjectName("FindObjectsValueChoice")
        self.value_choice_combo.view().setObjectName("FindObjectsComboPopup")
        self.value_choice_combo.view().setProperty("themeScope", "app")
        self.value_choice_combo.setMinimumHeight(32)

        self.value_bool_wrap = QtWidgets.QFrame(self)
        self.value_bool_wrap.setObjectName("FindObjectsValueBoolWrap")
        bool_layout = QtWidgets.QHBoxLayout(self.value_bool_wrap)
        bool_layout.setContentsMargins(0, 0, 0, 0)
        bool_layout.setSpacing(6)
        self.value_bool_true_btn = QtWidgets.QToolButton(self.value_bool_wrap)
        self.value_bool_true_btn.setObjectName("FindObjectsValueBoolTrueBtn")
        self.value_bool_true_btn.setText("True")
        self.value_bool_true_btn.setCheckable(True)
        self.value_bool_false_btn = QtWidgets.QToolButton(self.value_bool_wrap)
        self.value_bool_false_btn.setObjectName("FindObjectsValueBoolFalseBtn")
        self.value_bool_false_btn.setText("False")
        self.value_bool_false_btn.setCheckable(True)
        bool_layout.addWidget(self.value_bool_true_btn, 1)
        bool_layout.addWidget(self.value_bool_false_btn, 1)

        self.value_multi_picker = MultiValuePickerEditor(self)
        self.value_multi_picker.setObjectName("FindObjectsValuePicker")
        self.value_stack = QtWidgets.QStackedWidget(self)
        self.value_stack.addWidget(self.value_input)
        self.value_stack.addWidget(self.value_enum_combo)
        self.value_stack.addWidget(self.value_choice_combo)
        self.value_stack.addWidget(self.value_multi_picker)
        self.value_stack.addWidget(self.value_bool_wrap)
        self.value_stack.setCurrentWidget(self.value_input)
        self.value_unit_label = QtWidgets.QLabel("", self)
        self.value_unit_label.setObjectName("FindObjectsValueUnit")
        self.value_unit_label.setVisible(False)
        self.value_wrap = QtWidgets.QWidget(self)
        self.value_wrap.setObjectName("FindObjectsValueWrap")
        value_layout = QtWidgets.QHBoxLayout(self.value_wrap)
        value_layout.setContentsMargins(0, 0, 0, 0)
        value_layout.setSpacing(4)
        value_layout.addWidget(self.value_stack, 1)
        value_layout.addWidget(self.value_unit_label, 0, QtCore.Qt.AlignVCenter)
        layout.addWidget(self.value_wrap, 2)

        self.value_chip_frame = QtWidgets.QFrame(self)
        self.value_chip_frame.setObjectName("FindObjectsConditionStepChipFrame")
        value_chip_layout = QtWidgets.QHBoxLayout(self.value_chip_frame)
        value_chip_layout.setContentsMargins(8, 2, 8, 2)
        value_chip_layout.setSpacing(6)
        self.value_chip_label = QtWidgets.QLabel("", self.value_chip_frame)
        self.value_chip_label.setObjectName("FindObjectsConditionStepChipLabel")
        self.value_chip_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        value_chip_layout.addWidget(self.value_chip_label, 1)
        self.value_chip_frame.setVisible(False)
        layout.addWidget(self.value_chip_frame, 2)

        self.settings_btn = QtWidgets.QToolButton(self)
        self.settings_btn.setObjectName("FindObjectsConditionSettingsBtn")
        self.settings_btn.setText("...")
        self.settings_btn.setToolTip("Condition settings")
        self.settings_btn.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.settings_btn.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)
        self.settings_menu = QtWidgets.QMenu(self.settings_btn)
        self.settings_menu.setObjectName("FindObjectsConditionSettingsMenu")
        self.settings_menu.setProperty("themeScope", "app")
        self.settings_menu.setToolTipsVisible(True)
        self.settings_match_case_action = self.settings_menu.addAction("Match case")
        self.settings_match_case_action.setCheckable(True)
        self.settings_match_case_action.setEnabled(False)
        self.settings_match_case_action.setToolTip("Coming soon")
        self.settings_match_case_action.setStatusTip("Coming soon")
        self.settings_negate_action = self.settings_menu.addAction("Negate condition (NOT)")
        self.settings_negate_action.setCheckable(True)
        self.settings_negate_action.setEnabled(False)
        self.settings_negate_action.setToolTip("Coming soon")
        self.settings_negate_action.setStatusTip("Coming soon")
        self.settings_btn.setMenu(self.settings_menu)
        layout.addWidget(self.settings_btn, 0)

        self.row_edit_btn = QtWidgets.QToolButton(self)
        self.row_edit_btn.setObjectName("FindObjectsConditionRowEditBtn")
        self.row_edit_btn.setText("✎")
        self.row_edit_btn.setAutoRaise(True)
        self.row_edit_btn.setToolTip("Edit condition")
        self.row_edit_btn.setVisible(False)
        layout.addWidget(self.row_edit_btn, 0)

        self.remove_btn = QtWidgets.QToolButton(self)
        self.remove_btn.setObjectName("FindObjectsConditionRemoveBtn")
        self.remove_btn.setText("X")
        self.remove_btn.setAutoRaise(True)
        self.remove_btn.setToolTip("Remove condition")
        self.remove_btn.setMinimumWidth(22)
        layout.addWidget(self.remove_btn, 0)

        self._default_category_key = self.category_key()
        self._reload_properties_for_category(str(self.category_combo.currentData() or "").strip())
        self._default_property_key = self.property_key()
        self._progressive_reset_operator = True
        self._update_operator_items()
        self._default_operator_key = self.operator_key()

        self.category_combo.currentIndexChanged.connect(self._on_category_changed)
        self.property_combo.currentIndexChanged.connect(self._on_property_changed)
        self.property_combo.currentTextChanged.connect(self._on_property_text_changed)
        self.operator_combo.currentIndexChanged.connect(self._on_operator_changed)
        self.value_input.textChanged.connect(self._on_value_text_changed)
        self.value_choice_combo.currentIndexChanged.connect(self._on_value_choice_changed)
        self.value_enum_combo.currentIndexChanged.connect(self._on_value_enum_changed)
        self.value_multi_picker.valueChanged.connect(self._on_value_multi_picker_changed)
        self.value_bool_true_btn.clicked.connect(lambda: self._on_value_bool_clicked(True))
        self.value_bool_false_btn.clicked.connect(lambda: self._on_value_bool_clicked(False))
        self.remove_btn.clicked.connect(lambda: self.removeRequested.emit(self))
        self.item_chip_edit_btn.clicked.connect(lambda: self._edit_progressive_item())
        self.property_chip_edit_btn.clicked.connect(lambda: self._edit_progressive_property())
        self.operator_chip_edit_btn.clicked.connect(lambda: self._edit_progressive_operator())
        self.row_edit_btn.clicked.connect(self._edit_progressive_completed_row)
        self._configure_value_editor()
        self._apply_progressive_visibility()
        self._suppress_interaction_events = False

    def focus_first_step(self) -> None:
        if self._progressive_step == self._PROGRESSIVE_STEP_ITEM:
            self.category_combo.setFocus(QtCore.Qt.TabFocusReason)
            return
        if self._progressive_step == self._PROGRESSIVE_STEP_PROPERTY:
            self.property_combo.setFocus(QtCore.Qt.TabFocusReason)
            return
        if self._progressive_step == self._PROGRESSIVE_STEP_OPERATION:
            self.operator_combo.setFocus(QtCore.Qt.TabFocusReason)
            return
        self.value_stack.setFocus(QtCore.Qt.TabFocusReason)

    def set_progressive_step(self, step: int) -> None:
        if not self._progressive_enabled:
            return
        self._progressive_collapsed = False
        normalized = int(step or self._PROGRESSIVE_STEP_ITEM)
        self._progressive_step = max(self._PROGRESSIVE_STEP_ITEM, min(self._PROGRESSIVE_STEP_VALUE, normalized))
        self._apply_progressive_visibility()

    def _edit_progressive_item(self) -> None:
        self.set_progressive_step(self._PROGRESSIVE_STEP_ITEM)
        self.focus_first_step()

    def _edit_progressive_property(self) -> None:
        self.set_progressive_step(self._PROGRESSIVE_STEP_PROPERTY)
        self.focus_first_step()

    def _edit_progressive_operator(self) -> None:
        self.set_progressive_step(self._PROGRESSIVE_STEP_OPERATION)
        self.focus_first_step()

    def _edit_progressive_completed_row(self) -> None:
        self._progressive_collapsed = False
        self.set_progressive_step(self._PROGRESSIVE_STEP_VALUE)
        self.focus_first_step()

    def _sync_item_chip(self) -> None:
        key = self.category_key()
        if not key:
            self.item_chip_label.setText("")
            self.item_chip_frame.setToolTip("")
            return
        label = str(self._CATEGORY_LABELS.get(key) or key.title()).strip()
        text = f"Item: {label}"
        self.item_chip_label.setText(text)
        self.item_chip_frame.setToolTip(text)

    def _sync_property_chip(self) -> None:
        prop_key = self.property_key()
        if not prop_key:
            self.property_chip_label.setText("")
            self.property_chip_frame.setToolTip("")
            return
        label = str(self.property_combo.currentText() or "").strip()
        if not label:
            label = prop_key.replace("_", " ").title()
        text = f"Property: {label}"
        self.property_chip_label.setText(text)
        self.property_chip_frame.setToolTip(text)

    def _sync_operator_chip(self) -> None:
        op_key = self.operator_key()
        if not op_key:
            self.operator_chip_label.setText("")
            self.operator_chip_frame.setToolTip("")
            return
        label = str(self.operator_combo.currentText() or "").strip()
        if not label:
            label = op_key.replace("_", " ")
        text = f"Operation: {label}"
        self.operator_chip_label.setText(text)
        self.operator_chip_frame.setToolTip(text)

    def _sync_value_chip(self) -> None:
        op_key = self.operator_key()
        if op_key == "exists":
            self.value_chip_label.setText("")
            self.value_chip_frame.setToolTip("")
            return
        value = self.value_text()
        if not value:
            self.value_chip_label.setText("")
            self.value_chip_frame.setToolTip("")
            return
        shown = value
        if len(shown) > 40:
            shown = shown[:37].rstrip() + "..."
        text = f"Value: {shown}"
        self.value_chip_label.setText(text)
        self.value_chip_frame.setToolTip(value)

    def _progressive_is_complete(self) -> bool:
        if not self.property_key() or not self.operator_key():
            return False
        if self.operator_key() == "exists":
            return True
        return bool(self.value_text())

    def _maybe_collapse_progressive_row(self) -> None:
        if not self._progressive_enabled or self._progressive_collapsed:
            return
        if self._progressive_is_complete():
            self._progressive_collapsed = True
            self._apply_progressive_visibility()

    def _apply_progressive_visibility(self) -> None:
        if not self._progressive_enabled:
            return
        self._sync_item_chip()
        self._sync_property_chip()
        self._sync_operator_chip()
        self._sync_value_chip()
        if self._progressive_collapsed:
            self.category_combo.setVisible(False)
            self.property_combo.setVisible(False)
            self.operator_combo.setVisible(False)
            self.value_wrap.setVisible(False)
            self.item_chip_frame.setVisible(bool(self.category_key()))
            self.property_chip_frame.setVisible(bool(self.property_key()))
            self.operator_chip_frame.setVisible(bool(self.operator_key()))
            self.value_chip_frame.setVisible(bool(self.value_chip_label.text()))
            self.item_chip_edit_btn.setVisible(False)
            self.property_chip_edit_btn.setVisible(False)
            self.operator_chip_edit_btn.setVisible(False)
            self.row_edit_btn.setVisible(True)
            self.settings_btn.setVisible(False)
            return

        step = int(self._progressive_step or self._PROGRESSIVE_STEP_ITEM)
        self.category_combo.setVisible(step == self._PROGRESSIVE_STEP_ITEM)
        self.item_chip_frame.setVisible(step >= self._PROGRESSIVE_STEP_PROPERTY and bool(self.category_key()))
        self.property_combo.setVisible(step == self._PROGRESSIVE_STEP_PROPERTY)
        self.property_chip_frame.setVisible(step >= self._PROGRESSIVE_STEP_OPERATION and bool(self.property_key()))
        self.operator_combo.setVisible(step == self._PROGRESSIVE_STEP_OPERATION)
        self.operator_chip_frame.setVisible(step >= self._PROGRESSIVE_STEP_VALUE and bool(self.operator_key()))
        self.value_wrap.setVisible(step == self._PROGRESSIVE_STEP_VALUE)
        self.value_chip_frame.setVisible(False)
        self.item_chip_edit_btn.setVisible(step >= self._PROGRESSIVE_STEP_PROPERTY)
        self.property_chip_edit_btn.setVisible(step >= self._PROGRESSIVE_STEP_OPERATION)
        self.operator_chip_edit_btn.setVisible(step >= self._PROGRESSIVE_STEP_VALUE)
        self.row_edit_btn.setVisible(False)
        self.settings_btn.setVisible(False)

    def _normalize_property_options(
        self,
        property_options: Sequence[tuple[str, str]] | Sequence[Mapping[str, object]],
    ) -> List[Dict[str, str]]:
        out: List[Dict[str, str]] = []
        for row in list(property_options or []):
            label = ""
            key = ""
            category = ""
            if isinstance(row, Mapping):
                label = str(row.get("label") or "").strip()
                key = str(row.get("key") or "").strip()
                category = str(row.get("category") or "").strip().lower()
            elif isinstance(row, tuple) and len(row) >= 2:
                label = str(row[0] or "").strip()
                key = str(row[1] or "").strip()
            if not label or not key:
                continue
            if not category:
                category = str((self._PROPERTY_SPECS.get(key, {}) or {}).get("category") or "").strip().lower()
            if not category:
                category = "item"
            out.append(
                {
                    "label": label,
                    "key": key,
                    "category": category,
                }
            )
        return out

    def _rebuild_category_items(self) -> None:
        previous = str(self.category_combo.currentData() or "").strip().lower()
        choices: List[str] = []
        for row in self._property_catalog:
            category = str(row.get("category") or "").strip().lower()
            if not category or category in choices:
                continue
            choices.append(category)
        if not choices:
            choices = ["item"]
        options: List[tuple[str, str]] = []
        options.append(("Choose item…", self._PROGRESSIVE_PLACEHOLDER_CATEGORY))
        for category in choices:
            label = str(self._CATEGORY_LABELS.get(category) or category.title())
            options.append((label, category))
        self.category_combo.set_options(options, preserve_value=previous)

    def _reload_properties_for_category(self, category_key: str, *, preserve_property_key: str = "") -> None:
        wanted = str(category_key or "").strip().lower()
        if wanted == self._PROGRESSIVE_PLACEHOLDER_CATEGORY:
            wanted = ""
        property_rows: List[Dict[str, str]] = []
        if wanted:
            property_rows = [row for row in self._property_catalog if str(row.get("category") or "").strip().lower() == wanted]
        if not property_rows:
            property_rows = list(self._property_catalog)
        self._label_to_key = {}
        wanted_key = str(preserve_property_key or "").strip().lower()
        options: List[tuple[str, str]] = []
        preserve_value = ""
        options.append(("Choose property…", self._PROGRESSIVE_PLACEHOLDER_PROPERTY))
        for row in property_rows:
            display = str(row.get("label") or "").strip()
            value = str(row.get("key") or "").strip()
            if not display or not value:
                continue
            options.append((display, value))
            self._label_to_key[display.lower()] = value
            if wanted_key and value.lower() == wanted_key:
                preserve_value = value
        self.property_combo.blockSignals(True)
        self.property_combo.set_options(options, preserve_value=preserve_value)
        self.property_combo.blockSignals(False)

    def _update_operator_items(self) -> None:
        """Rebuild operator combo showing only operators appropriate for the current property kind."""
        spec = self._property_spec()
        kind = str(spec.get("kind") or "string").strip().lower()
        allowed = set(self._OPERATORS_FOR_KIND.get(kind, [key for _, key in self._OPERATORS]))
        current_op = self.operator_key()
        self.operator_combo.blockSignals(True)
        self.operator_combo.clear()
        self.operator_combo.addItem("Choose operation…", self._PROGRESSIVE_PLACEHOLDER_OPERATOR)
        for label, key in self._OPERATORS:
            if key in allowed:
                self.operator_combo.addItem(label, key)
        if self._progressive_reset_operator:
            self._progressive_reset_operator = False
            self.operator_combo.setCurrentIndex(0)
        else:
            idx = self.operator_combo.findData(current_op)
            if idx >= 0:
                self.operator_combo.setCurrentIndex(idx)
            elif self.operator_combo.count() > 0:
                self.operator_combo.setCurrentIndex(0)
        self.operator_combo.blockSignals(False)

    def _mark_user_interaction(self) -> None:
        if self._suppress_interaction_events:
            return
        self._has_user_interaction = True

    @staticmethod
    def _set_widget_invalid(widget: Optional[QtWidgets.QWidget], is_invalid: bool) -> None:
        if widget is None:
            return
        widget.setProperty("invalid", bool(is_invalid))
        style = widget.style()
        if style is not None:
            style.unpolish(widget)
            style.polish(widget)
        widget.update()

    def set_value_invalid(self, invalid: bool) -> None:
        is_invalid = bool(invalid and self.operator_key() != "exists")
        self._set_widget_invalid(self.value_input, is_invalid)
        self._set_widget_invalid(self.value_choice_combo, is_invalid)
        self._set_widget_invalid(self.value_enum_combo, is_invalid)
        self._set_widget_invalid(self.value_bool_true_btn, is_invalid)
        self._set_widget_invalid(self.value_bool_false_btn, is_invalid)
        self.value_multi_picker.set_invalid(is_invalid)
        tip = "Value is required for this operator." if is_invalid else ""
        self.value_input.setToolTip(tip)
        self.value_choice_combo.setToolTip(tip)
        self.value_enum_combo.setToolTip(tip)
        self.value_multi_picker.setToolTip(tip)

    def has_missing_required_value(self) -> bool:
        if not self.property_key() or not self.operator_key():
            return False
        if self.operator_key() == "exists":
            return False
        if self.value_text():
            return False
        if self._has_user_interaction:
            return True
        category_changed = self.category_key() != str(self._default_category_key or "")
        property_changed = self.property_key() != str(self._default_property_key or "")
        operator_changed = self.operator_key() != str(self._default_operator_key or "")
        return bool(category_changed or property_changed or operator_changed)

    def _on_category_changed(self, _index: int) -> None:
        self._mark_user_interaction()
        selected_property = self.property_key()
        if self._progressive_enabled:
            selected_property = ""
        self._reload_properties_for_category(self.category_key(), preserve_property_key=selected_property)
        self._update_operator_items()
        self._configure_value_editor()
        if self._progressive_enabled and self._progressive_step == self._PROGRESSIVE_STEP_ITEM and self.category_key():
            self.set_progressive_step(self._PROGRESSIVE_STEP_PROPERTY)
            self.focus_first_step()
        self.changed.emit()

    def _on_property_changed(self, _index: int) -> None:
        self._mark_user_interaction()
        if self._progressive_enabled:
            self._progressive_reset_operator = True
        self._update_operator_items()
        self._configure_value_editor()
        if self._progressive_enabled and self._progressive_step == self._PROGRESSIVE_STEP_PROPERTY and self.property_key():
            self.set_progressive_step(self._PROGRESSIVE_STEP_OPERATION)
            self.focus_first_step()
        self.changed.emit()

    def _on_property_text_changed(self, _text: str) -> None:
        self._mark_user_interaction()
        if self._progressive_enabled:
            self._progressive_reset_operator = True
        self._update_operator_items()
        self._configure_value_editor()
        if self._progressive_enabled and self._progressive_step == self._PROGRESSIVE_STEP_PROPERTY and self.property_key():
            self.set_progressive_step(self._PROGRESSIVE_STEP_OPERATION)
            self.focus_first_step()
        self.changed.emit()

    def _on_value_text_changed(self, _text: str) -> None:
        self._mark_user_interaction()
        self._maybe_collapse_progressive_row()
        self.changed.emit()

    def _on_value_choice_changed(self, _index: int) -> None:
        self._mark_user_interaction()
        self._maybe_collapse_progressive_row()
        self.changed.emit()

    def _on_value_enum_changed(self, _index: int) -> None:
        self._mark_user_interaction()
        self._maybe_collapse_progressive_row()
        self.changed.emit()

    def _on_value_bool_clicked(self, value: bool) -> None:
        self._mark_user_interaction()
        target = self.value_bool_true_btn if value else self.value_bool_false_btn
        other = self.value_bool_false_btn if value else self.value_bool_true_btn
        target.blockSignals(True)
        other.blockSignals(True)
        try:
            target.setChecked(True)
            other.setChecked(False)
        finally:
            target.blockSignals(False)
            other.blockSignals(False)
        self._maybe_collapse_progressive_row()
        self.changed.emit()

    def _on_value_multi_picker_changed(self) -> None:
        self._mark_user_interaction()
        if self.value_multi_picker.selected_count() > 1 and self.operator_key() != "in_list":
            idx = self.operator_combo.findData("in_list")
            if idx >= 0 and idx != self.operator_combo.currentIndex():
                self.operator_combo.setCurrentIndex(idx)
        self._maybe_collapse_progressive_row()
        self.changed.emit()

    def _set_choice_items(self, items: Sequence[tuple[str, str]], *, selected_value: str) -> None:
        current = str(selected_value or "").strip().lower()
        self.value_choice_combo.blockSignals(True)
        self.value_choice_combo.clear()
        target = -1
        for pair in list(items or []):
            label = str(pair[0] if len(pair) > 0 else "").strip()
            value = str(pair[1] if len(pair) > 1 else label).strip()
            if not label:
                continue
            self.value_choice_combo.addItem(label, value)
            if current and value.lower() == current:
                target = self.value_choice_combo.count() - 1
        if target >= 0:
            self.value_choice_combo.setCurrentIndex(target)
        elif self.value_choice_combo.count() > 0:
            self.value_choice_combo.setCurrentIndex(0)
        self.value_choice_combo.blockSignals(False)

    def _property_spec(self) -> Dict[str, object]:
        key = self.property_key()
        return dict(self._PROPERTY_SPECS.get(key, {}))

    @staticmethod
    def _split_csv_values(text: str) -> List[str]:
        return [str(token or "").strip() for token in str(text or "").split(",") if str(token or "").strip()]

    def _distinct_values_for_property(self, property_key: str) -> List[str]:
        key = str(property_key or "").strip()
        if not key:
            return []
        if callable(self._distinct_values_provider):
            try:
                rows = list(self._distinct_values_provider(key) or [])
            except Exception:
                rows = []
            return [str(value or "").strip() for value in rows if str(value or "").strip()]
        return []

    def _configure_value_editor(self) -> None:
        if self._updating_value_editor:
            return
        self._updating_value_editor = True
        try:
            current_value = self.value_text()
            op = self.operator_key()
            requires_value = op != "exists"
            self.value_stack.setEnabled(requires_value)
            self.value_input.setEnabled(requires_value)
            self.value_choice_combo.setEnabled(requires_value)
            self.value_enum_combo.setEnabled(requires_value)
            self.value_bool_true_btn.setEnabled(requires_value)
            self.value_bool_false_btn.setEnabled(requires_value)
            if not requires_value:
                self.value_input.setValidator(None)
                self.value_input.setText("")
                self.value_input.setPlaceholderText("Value")
                self.value_input.setToolTip("")
                self.value_choice_combo.setToolTip("")
                self.value_enum_combo.setToolTip("")
                self.value_unit_label.setVisible(False)
                self.set_value_invalid(False)
                return

            spec = self._property_spec()
            kind = str(spec.get("kind") or "string").strip().lower()
            if op == "in_list":
                if kind not in {"enum", "list", "enum_dynamic"}:
                    kind = "string"
                self.value_input.setPlaceholderText("a, b, c")
                self.value_input.setToolTip("Use comma-separated values")
                self.value_choice_combo.setToolTip("Use comma-separated values")
            else:
                self.value_input.setToolTip("")
                self.value_choice_combo.setToolTip("")
                self.value_enum_combo.setToolTip("")

            if kind == "boolean":
                self.value_stack.setCurrentWidget(self.value_bool_wrap)
                wanted = str(current_value or "").strip().lower()
                self.value_bool_true_btn.blockSignals(True)
                self.value_bool_false_btn.blockSignals(True)
                try:
                    self.value_bool_true_btn.setChecked(wanted == "true")
                    self.value_bool_false_btn.setChecked(wanted == "false")
                finally:
                    self.value_bool_true_btn.blockSignals(False)
                    self.value_bool_false_btn.blockSignals(False)
                self.value_unit_label.setVisible(False)
                return

            if kind in {"enum", "list"}:
                choices = [str(choice).strip() for choice in list(spec.get("choices") or []) if str(choice).strip()]
                if op == "in_list":
                    self.value_stack.setCurrentWidget(self.value_multi_picker)
                    self.value_multi_picker.set_values(choices, selected_csv=current_value)
                    self.value_unit_label.setVisible(False)
                    return
                options: List[tuple[str, str]] = [("Choose value…", self._PROGRESSIVE_PLACEHOLDER_VALUE)]
                options.extend((choice, choice) for choice in choices)
                self.value_stack.setCurrentWidget(self.value_enum_combo)
                self.value_enum_combo.set_options(options, preserve_value=current_value)
                self.value_unit_label.setVisible(False)
                return

            if kind == "enum_dynamic":
                dynamic_values = self._distinct_values_for_property(self.property_key())
                if dynamic_values:
                    if op == "in_list":
                        self.value_stack.setCurrentWidget(self.value_multi_picker)
                        self.value_multi_picker.set_values(dynamic_values, selected_csv=current_value)
                    else:
                        options = [("Choose value…", self._PROGRESSIVE_PLACEHOLDER_VALUE)]
                        options.extend((value, value) for value in dynamic_values)
                        self.value_stack.setCurrentWidget(self.value_enum_combo)
                        self.value_enum_combo.set_options(options, preserve_value=current_value)
                    self.value_unit_label.setVisible(False)
                    return
                self.value_stack.setCurrentWidget(self.value_input)
                self.value_input.setValidator(None)
                if op != "in_list":
                    self.value_input.setPlaceholderText("Value")
                self.value_unit_label.setVisible(False)
                if self.value_input.text() != current_value:
                    self.value_input.setText(current_value)
                return

            self.value_stack.setCurrentWidget(self.value_input)
            if kind == "number":
                self.value_input.setValidator(self._number_validator)
                self.value_input.setPlaceholderText("0.0")
                unit = str(spec.get("unit") or "").strip()
                self.value_unit_label.setText(unit)
                self.value_unit_label.setVisible(bool(unit))
            else:
                self.value_input.setValidator(None)
                if op != "in_list":
                    self.value_input.setPlaceholderText("Value")
                self.value_unit_label.setVisible(False)
            if self.value_input.text() != current_value:
                self.value_input.setText(current_value)
        finally:
            self._updating_value_editor = False

    def _on_operator_changed(self, _index: int) -> None:
        self._mark_user_interaction()
        self._configure_value_editor()
        if self._progressive_enabled and self._progressive_step == self._PROGRESSIVE_STEP_OPERATION and self.operator_key():
            if self.operator_key() == "exists":
                self._maybe_collapse_progressive_row()
            else:
                self.set_progressive_step(self._PROGRESSIVE_STEP_VALUE)
                self.focus_first_step()
        self.changed.emit()

    def property_key(self) -> str:
        data = str(self.property_combo.currentData() or "").strip()
        if data == self._PROGRESSIVE_PLACEHOLDER_PROPERTY:
            return ""
        if data:
            return data
        text = str(self.property_combo.currentText() or "").strip().lower()
        if not text:
            return ""
        return str(self._label_to_key.get(text, text))

    def category_key(self) -> str:
        current = str(self.category_combo.currentData() or "").strip().lower()
        if current == self._PROGRESSIVE_PLACEHOLDER_CATEGORY:
            return ""
        if current:
            return current
        key = self.property_key()
        if key:
            category = str((self._PROPERTY_SPECS.get(key, {}) or {}).get("category") or "").strip().lower()
            if category:
                return category
        return "item"

    def operator_key(self) -> str:
        current = str(self.operator_combo.currentData() or "").strip()
        if current == self._PROGRESSIVE_PLACEHOLDER_OPERATOR:
            return ""
        return current

    def value_text(self) -> str:
        if self.value_stack.currentWidget() is self.value_enum_combo:
            value = str(self.value_enum_combo.currentData() or "").strip()
            if value == self._PROGRESSIVE_PLACEHOLDER_VALUE:
                return ""
            return value
        if self.value_stack.currentWidget() is self.value_choice_combo:
            return str(self.value_choice_combo.currentData() or self.value_choice_combo.currentText() or "").strip()
        if self.value_stack.currentWidget() is self.value_multi_picker:
            return str(self.value_multi_picker.csv_text() or "").strip()
        if self.value_stack.currentWidget() is self.value_bool_wrap:
            if self.value_bool_true_btn.isChecked():
                return "true"
            if self.value_bool_false_btn.isChecked():
                return "false"
            return ""
        return str(self.value_input.text() or "").strip()

    def is_active(self) -> bool:
        prop = self.property_key()
        op = self.operator_key()
        if not prop or not op:
            return False
        if op == "exists":
            return True
        return bool(self.value_text())

    @staticmethod
    def _parse_numeric_shorthand(text: str) -> Optional[tuple[str, str]]:
        """Parse '<100', '<=200', '>50', '>=75' → (operator_key, numeric_value_str).

        Both strict and non-strict inequalities map to the available greater_than /
        less_than operators.  Returns None if the text does not start with a recognised
        prefix or if the numeric portion is not a valid number.
        """
        text = text.strip()
        for prefix, op in (("<=", "less_than"), ("<", "less_than"), (">=", "greater_than"), (">", "greater_than")):
            if text.startswith(prefix):
                rest = text[len(prefix):].strip()
                try:
                    float(rest)
                    return (op, rest)
                except ValueError:
                    return None
        return None

    def descriptor(self) -> Dict[str, str]:
        prop = self.property_key()
        op = self.operator_key()
        value = self.value_text()
        spec = self._property_spec()
        kind = str(spec.get("kind") or "string").strip().lower()
        if kind == "number" and value:
            parsed = self._parse_numeric_shorthand(value)
            if parsed is not None:
                op, value = parsed
        return {
            "category": self.category_key(),
            "property": prop,
            "operator": op,
            "value": value,
        }

    def chip_text(self) -> str:
        details = self.descriptor()
        prop = str(details.get("property") or "").replace("_", " ").title()
        op = str(details.get("operator") or "").replace("_", " ")
        value = str(details.get("value") or "")
        if op == "exists":
            return f"{prop} exists"
        return f"{prop} {op} {value}".strip()
