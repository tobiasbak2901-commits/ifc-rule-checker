from __future__ import annotations

from typing import Callable, Dict, List, Mapping, Optional, Sequence

from PySide6 import QtCore, QtGui, QtWidgets
from ui.searchable_dropdown import SearchableDropdown
from ui.value_picker import MultiValuePickerEditor


class ConditionRow(QtWidgets.QFrame):
    changed = QtCore.Signal()
    removeRequested = QtCore.Signal(object)

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

        self.operator_combo = QtWidgets.QComboBox(self)
        self.operator_combo.setObjectName("FindObjectsOperatorCombo")
        for label, value in self._OPERATORS:
            self.operator_combo.addItem(label, value)
        self.operator_combo.view().setObjectName("FindObjectsComboPopup")
        self.operator_combo.view().setProperty("themeScope", "app")
        self.operator_combo.setMinimumHeight(32)
        layout.addWidget(self.operator_combo, 1)

        self.value_input = QtWidgets.QLineEdit(self)
        self.value_input.setObjectName("FindObjectsValueInput")
        self.value_input.setPlaceholderText("Value")
        self.value_input.setMinimumHeight(32)
        self.value_choice_combo = QtWidgets.QComboBox(self)
        self.value_choice_combo.setObjectName("FindObjectsValueChoice")
        self.value_choice_combo.view().setObjectName("FindObjectsComboPopup")
        self.value_choice_combo.view().setProperty("themeScope", "app")
        self.value_choice_combo.setMinimumHeight(32)
        self.value_multi_picker = MultiValuePickerEditor(self)
        self.value_multi_picker.setObjectName("FindObjectsValuePicker")
        self.value_stack = QtWidgets.QStackedWidget(self)
        self.value_stack.addWidget(self.value_input)
        self.value_stack.addWidget(self.value_choice_combo)
        self.value_stack.addWidget(self.value_multi_picker)
        self.value_stack.setCurrentWidget(self.value_input)
        self.value_unit_label = QtWidgets.QLabel("", self)
        self.value_unit_label.setObjectName("FindObjectsValueUnit")
        self.value_unit_label.setVisible(False)
        value_wrap = QtWidgets.QWidget(self)
        value_wrap.setObjectName("FindObjectsValueWrap")
        value_layout = QtWidgets.QHBoxLayout(value_wrap)
        value_layout.setContentsMargins(0, 0, 0, 0)
        value_layout.setSpacing(4)
        value_layout.addWidget(self.value_stack, 1)
        value_layout.addWidget(self.value_unit_label, 0, QtCore.Qt.AlignVCenter)
        layout.addWidget(value_wrap, 2)

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

        self.remove_btn = QtWidgets.QToolButton(self)
        self.remove_btn.setObjectName("FindObjectsConditionRemoveBtn")
        self.remove_btn.setText("X")
        self.remove_btn.setAutoRaise(True)
        self.remove_btn.setToolTip("Remove condition")
        self.remove_btn.setMinimumWidth(22)
        layout.addWidget(self.remove_btn, 0)

        self._default_category_key = str(self.category_combo.itemData(0) or "").strip()
        self._reload_properties_for_category(self._default_category_key)
        self._default_property_key = str(self.property_combo.itemData(0) or "").strip()
        self._update_operator_items()
        self._default_operator_key = str(self.operator_combo.itemData(0) or "").strip()

        self.category_combo.currentIndexChanged.connect(self._on_category_changed)
        self.property_combo.currentIndexChanged.connect(self._on_property_changed)
        self.property_combo.currentTextChanged.connect(self._on_property_text_changed)
        self.operator_combo.currentIndexChanged.connect(self._on_operator_changed)
        self.value_input.textChanged.connect(self._on_value_text_changed)
        self.value_choice_combo.currentIndexChanged.connect(self._on_value_choice_changed)
        self.value_multi_picker.valueChanged.connect(self._on_value_multi_picker_changed)
        self.remove_btn.clicked.connect(lambda: self.removeRequested.emit(self))
        self._configure_value_editor()
        self._suppress_interaction_events = False

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
        previous = self.category_key()
        choices: List[str] = []
        for row in self._property_catalog:
            category = str(row.get("category") or "").strip().lower()
            if not category or category in choices:
                continue
            choices.append(category)
        if not choices:
            choices = ["item"]
        options: List[tuple[str, str]] = []
        for category in choices:
            label = str(self._CATEGORY_LABELS.get(category) or category.title())
            options.append((label, category))
        self.category_combo.set_options(options, preserve_value=previous)

    def _reload_properties_for_category(self, category_key: str, *, preserve_property_key: str = "") -> None:
        wanted = str(category_key or "").strip().lower()
        if not wanted:
            wanted = "item"
        property_rows = [row for row in self._property_catalog if str(row.get("category") or "").strip().lower() == wanted]
        if not property_rows:
            property_rows = list(self._property_catalog)
        self._label_to_key = {}
        wanted_key = str(preserve_property_key or "").strip().lower()
        options: List[tuple[str, str]] = []
        preserve_value = ""
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
        for label, key in self._OPERATORS:
            if key in allowed:
                self.operator_combo.addItem(label, key)
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
        self.value_multi_picker.set_invalid(is_invalid)
        tip = "Value is required for this operator." if is_invalid else ""
        self.value_input.setToolTip(tip)
        self.value_choice_combo.setToolTip(tip)
        self.value_multi_picker.setToolTip(tip)

    def has_missing_required_value(self) -> bool:
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
        self._reload_properties_for_category(self.category_key(), preserve_property_key=selected_property)
        self._update_operator_items()
        self._configure_value_editor()
        self.changed.emit()

    def _on_property_changed(self, _index: int) -> None:
        self._mark_user_interaction()
        self._update_operator_items()
        self._configure_value_editor()
        self.changed.emit()

    def _on_property_text_changed(self, _text: str) -> None:
        self._mark_user_interaction()
        self._update_operator_items()
        self._configure_value_editor()
        self.changed.emit()

    def _on_value_text_changed(self, _text: str) -> None:
        self._mark_user_interaction()
        self.changed.emit()

    def _on_value_choice_changed(self, _index: int) -> None:
        self._mark_user_interaction()
        self.changed.emit()

    def _on_value_multi_picker_changed(self) -> None:
        self._mark_user_interaction()
        if self.value_multi_picker.selected_count() > 1 and self.operator_key() != "in_list":
            idx = self.operator_combo.findData("in_list")
            if idx >= 0 and idx != self.operator_combo.currentIndex():
                self.operator_combo.setCurrentIndex(idx)
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
            if not requires_value:
                self.value_input.setValidator(None)
                self.value_input.setText("")
                self.value_input.setPlaceholderText("Value")
                self.value_input.setToolTip("")
                self.value_choice_combo.setToolTip("")
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

            if kind == "boolean":
                self.value_stack.setCurrentWidget(self.value_choice_combo)
                self._set_choice_items([("true", "true"), ("false", "false")], selected_value=current_value)
                self.value_unit_label.setVisible(False)
                return

            if kind in {"enum", "list"}:
                choices = [str(choice).strip() for choice in list(spec.get("choices") or []) if str(choice).strip()]
                if len(choices) >= 12 or op == "in_list":
                    self.value_stack.setCurrentWidget(self.value_multi_picker)
                    self.value_multi_picker.set_values(choices, selected_csv=current_value)
                    self.value_unit_label.setVisible(False)
                    return
                items = [(choice, choice) for choice in choices] if choices else [("Select...", "")]
                self.value_stack.setCurrentWidget(self.value_choice_combo)
                self._set_choice_items(items, selected_value=current_value)
                self.value_unit_label.setVisible(False)
                return

            if kind == "enum_dynamic":
                dynamic_values = self._distinct_values_for_property(self.property_key())
                if dynamic_values:
                    self.value_stack.setCurrentWidget(self.value_multi_picker)
                    self.value_multi_picker.set_values(dynamic_values, selected_csv=current_value)
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
        self.changed.emit()

    def property_key(self) -> str:
        data = str(self.property_combo.currentData() or "").strip()
        if data:
            return data
        text = str(self.property_combo.currentText() or "").strip().lower()
        if not text:
            return ""
        return str(self._label_to_key.get(text, text))

    def category_key(self) -> str:
        current = str(self.category_combo.currentData() or "").strip().lower()
        if current:
            return current
        key = self.property_key()
        if key:
            category = str((self._PROPERTY_SPECS.get(key, {}) or {}).get("category") or "").strip().lower()
            if category:
                return category
        return "item"

    def operator_key(self) -> str:
        return str(self.operator_combo.currentData() or "").strip()

    def value_text(self) -> str:
        if self.value_stack.currentWidget() is self.value_choice_combo:
            return str(self.value_choice_combo.currentData() or self.value_choice_combo.currentText() or "").strip()
        if self.value_stack.currentWidget() is self.value_multi_picker:
            return str(self.value_multi_picker.csv_text() or "").strip()
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
