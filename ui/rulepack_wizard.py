from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6 import QtWidgets

from rulepack_generator import (
    build_rulepack_yaml,
    ensure_yaml_extension,
    validate_rulepack_input,
    validate_rulepack_output,
    write_rulepack_yaml,
)


class _ClassEditorDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, initial: Optional[Dict[str, Any]] = None):
        super().__init__(parent)
        self.setWindowTitle("Class")
        self._initial = initial or {}

        layout = QtWidgets.QVBoxLayout(self)
        form = QtWidgets.QFormLayout()

        self.id_edit = QtWidgets.QLineEdit(str(self._initial.get("id") or ""))
        self.name_edit = QtWidgets.QLineEdit(str(self._initial.get("name") or ""))
        self.keywords_edit = QtWidgets.QLineEdit(", ".join(self._initial.get("keywords") or []))
        self.paths_edit = QtWidgets.QLineEdit(", ".join(self._initial.get("path_candidates") or []))

        form.addRow("Class ID", self.id_edit)
        form.addRow("Class Name", self.name_edit)
        form.addRow("Keywords (comma-separated)", self.keywords_edit)
        form.addRow("Path candidates (comma-separated)", self.paths_edit)
        layout.addLayout(form)

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_accept(self):
        if not self.id_edit.text().strip():
            QtWidgets.QMessageBox.warning(self, "Class", "Class ID is required.")
            return
        if not self.name_edit.text().strip():
            QtWidgets.QMessageBox.warning(self, "Class", "Class name is required.")
            return
        if not self._split_csv(self.keywords_edit.text()):
            QtWidgets.QMessageBox.warning(self, "Class", "At least one keyword is required.")
            return
        if not self._split_csv(self.paths_edit.text()):
            QtWidgets.QMessageBox.warning(self, "Class", "At least one path candidate is required.")
            return
        self.accept()

    def value(self) -> Dict[str, Any]:
        return {
            "id": self.id_edit.text().strip(),
            "name": self.name_edit.text().strip(),
            "keywords": self._split_csv(self.keywords_edit.text()),
            "path_candidates": self._split_csv(self.paths_edit.text()),
        }

    @staticmethod
    def _split_csv(value: str) -> List[str]:
        return [part.strip() for part in value.split(",") if part.strip()]


class _RuleEditorDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, initial: Optional[Dict[str, Any]] = None):
        super().__init__(parent)
        self.setWindowTitle("Rule")
        self._initial = initial or {}

        layout = QtWidgets.QVBoxLayout(self)
        form = QtWidgets.QFormLayout()

        self.id_edit = QtWidgets.QLineEdit(str(self._initial.get("id") or ""))
        self.title_edit = QtWidgets.QLineEdit(str(self._initial.get("title") or ""))
        self.class_in_edit = QtWidgets.QLineEdit(", ".join(self._initial.get("class_in") or []))

        self.relation_combo = QtWidgets.QComboBox()
        self.relation_combo.setEditable(True)
        self.relation_combo.addItems(["parallel", "crossing", "any"])
        relation = str(self._initial.get("relation") or "parallel")
        self.relation_combo.setCurrentText(relation)

        self.check_type_combo = QtWidgets.QComboBox()
        self.check_type_combo.addItems(["min_clearance"])
        check = self._initial.get("check") or {}
        check_type = str(check.get("type") or "min_clearance")
        self.check_type_combo.setCurrentText(check_type)

        self.min_distance_spin = QtWidgets.QDoubleSpinBox()
        self.min_distance_spin.setRange(0.0, 10000.0)
        self.min_distance_spin.setDecimals(4)
        self.min_distance_spin.setValue(float(check.get("min_distance_m") or 0.0))

        self.severity_combo = QtWidgets.QComboBox()
        self.severity_combo.addItems(["error", "warning", "info"])
        severity = str(self._initial.get("severity") or "error")
        self.severity_combo.setCurrentText(severity)

        self.explain_edit = QtWidgets.QLineEdit(str(self._initial.get("explain_short") or ""))

        form.addRow("Rule ID", self.id_edit)
        form.addRow("Title", self.title_edit)
        form.addRow("Class in (comma-separated)", self.class_in_edit)
        form.addRow("Relation", self.relation_combo)
        form.addRow("Check type", self.check_type_combo)
        form.addRow("Min distance (m)", self.min_distance_spin)
        form.addRow("Severity", self.severity_combo)
        form.addRow("Explain short", self.explain_edit)
        layout.addLayout(form)

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_accept(self):
        if not self.id_edit.text().strip():
            QtWidgets.QMessageBox.warning(self, "Rule", "Rule ID is required.")
            return
        if not self.title_edit.text().strip():
            QtWidgets.QMessageBox.warning(self, "Rule", "Rule title is required.")
            return
        if not self._split_csv(self.class_in_edit.text()):
            QtWidgets.QMessageBox.warning(self, "Rule", "At least one class_in value is required.")
            return
        if not self.relation_combo.currentText().strip():
            QtWidgets.QMessageBox.warning(self, "Rule", "Relation is required.")
            return
        if not self.explain_edit.text().strip():
            QtWidgets.QMessageBox.warning(self, "Rule", "Explain short is required.")
            return
        self.accept()

    def value(self) -> Dict[str, Any]:
        return {
            "id": self.id_edit.text().strip(),
            "title": self.title_edit.text().strip(),
            "class_in": self._split_csv(self.class_in_edit.text()),
            "relation": self.relation_combo.currentText().strip(),
            "check": {
                "type": self.check_type_combo.currentText().strip(),
                "min_distance_m": float(self.min_distance_spin.value()),
            },
            "severity": self.severity_combo.currentText().strip(),
            "explain_short": self.explain_edit.text().strip(),
        }

    @staticmethod
    def _split_csv(value: str) -> List[str]:
        return [part.strip() for part in value.split(",") if part.strip()]


class RulepackWizardDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create Rulepack (Wizard)")
        self.resize(860, 620)
        self.generated_rulepack_path: Optional[Path] = None

        self._classes: List[Dict[str, Any]] = []
        self._rules: List[Dict[str, Any]] = []

        root = QtWidgets.QVBoxLayout(self)
        self.step_title = QtWidgets.QLabel("")
        self.step_title.setStyleSheet("font-weight: 600;")
        root.addWidget(self.step_title)

        self.stack = QtWidgets.QStackedWidget()
        root.addWidget(self.stack, 1)

        self._build_metadata_step()
        self._build_classes_step()
        self._build_defaults_step()
        self._build_rules_step()
        self._build_generate_step()

        button_row = QtWidgets.QHBoxLayout()
        self.back_btn = QtWidgets.QPushButton("Back")
        self.next_btn = QtWidgets.QPushButton("Next")
        self.cancel_btn = QtWidgets.QPushButton("Cancel")
        self.generate_btn = QtWidgets.QPushButton("Generate")
        self.generate_btn.setDefault(True)
        button_row.addWidget(self.back_btn)
        button_row.addWidget(self.next_btn)
        button_row.addStretch(1)
        button_row.addWidget(self.cancel_btn)
        button_row.addWidget(self.generate_btn)
        root.addLayout(button_row)

        self.back_btn.clicked.connect(self._on_back)
        self.next_btn.clicked.connect(self._on_next)
        self.cancel_btn.clicked.connect(self.reject)
        self.generate_btn.clicked.connect(self._on_generate)

        self.stack.currentChanged.connect(self._update_step_state)
        self._update_step_state()

    def _build_metadata_step(self):
        page = QtWidgets.QWidget()
        layout = QtWidgets.QFormLayout(page)
        self.meta_id = QtWidgets.QLineEdit("drainage_ds475_v1")
        self.meta_name = QtWidgets.QLineEdit("Drainage - DS475 (Core)")
        self.meta_version = QtWidgets.QLineEdit("1.0")
        self.meta_author = QtWidgets.QLineEdit("")
        self.meta_description = QtWidgets.QPlainTextEdit("")
        self.meta_description.setMinimumHeight(110)
        layout.addRow("Rulepack ID", self.meta_id)
        layout.addRow("Name", self.meta_name)
        layout.addRow("Version", self.meta_version)
        layout.addRow("Author", self.meta_author)
        layout.addRow("Description", self.meta_description)
        self.stack.addWidget(page)

    def _build_classes_step(self):
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)

        tools = QtWidgets.QHBoxLayout()
        add_btn = QtWidgets.QPushButton("Add Class")
        edit_btn = QtWidgets.QPushButton("Edit Class")
        remove_btn = QtWidgets.QPushButton("Remove Class")
        tools.addWidget(add_btn)
        tools.addWidget(edit_btn)
        tools.addWidget(remove_btn)
        tools.addStretch(1)
        layout.addLayout(tools)

        self.classes_table = QtWidgets.QTableWidget(0, 4)
        self.classes_table.setHorizontalHeaderLabels(["ID", "Name", "Keywords", "Path candidates"])
        self.classes_table.horizontalHeader().setStretchLastSection(True)
        self.classes_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.classes_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.classes_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.classes_table, 1)

        add_btn.clicked.connect(self._on_add_class)
        edit_btn.clicked.connect(self._on_edit_class)
        remove_btn.clicked.connect(self._on_remove_class)
        self.stack.addWidget(page)

    def _build_defaults_step(self):
        page = QtWidgets.QWidget()
        layout = QtWidgets.QFormLayout(page)
        self.max_move_spin = QtWidgets.QDoubleSpinBox()
        self.max_move_spin.setRange(0.0, 100000.0)
        self.max_move_spin.setDecimals(3)
        self.max_move_spin.setValue(0.8)
        self.z_move_allowed = QtWidgets.QCheckBox("Allow Z movement")
        self.z_move_allowed.setChecked(False)
        layout.addRow("constraints.max_move_m", self.max_move_spin)
        layout.addRow("constraints.z_move_allowed", self.z_move_allowed)
        self.stack.addWidget(page)

    def _build_rules_step(self):
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)

        tools = QtWidgets.QHBoxLayout()
        add_btn = QtWidgets.QPushButton("Add Rule")
        edit_btn = QtWidgets.QPushButton("Edit Rule")
        remove_btn = QtWidgets.QPushButton("Remove Rule")
        tools.addWidget(add_btn)
        tools.addWidget(edit_btn)
        tools.addWidget(remove_btn)
        tools.addStretch(1)
        layout.addLayout(tools)

        self.rules_table = QtWidgets.QTableWidget(0, 8)
        self.rules_table.setHorizontalHeaderLabels(
            ["ID", "Title", "Class in", "Relation", "Check", "Min distance", "Severity", "Explain short"]
        )
        self.rules_table.horizontalHeader().setStretchLastSection(True)
        self.rules_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.rules_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.rules_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.rules_table, 1)

        add_btn.clicked.connect(self._on_add_rule)
        edit_btn.clicked.connect(self._on_edit_rule)
        remove_btn.clicked.connect(self._on_remove_rule)
        self.stack.addWidget(page)

    def _build_generate_step(self):
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)

        path_row = QtWidgets.QHBoxLayout()
        self.output_path = QtWidgets.QLineEdit("")
        browse_btn = QtWidgets.QPushButton("Browse...")
        path_row.addWidget(self.output_path, 1)
        path_row.addWidget(browse_btn)
        layout.addWidget(QtWidgets.QLabel("Output rulepack YAML path"))
        layout.addLayout(path_row)

        self.generate_status = QtWidgets.QPlainTextEdit()
        self.generate_status.setReadOnly(True)
        self.generate_status.setPlaceholderText("Validation messages will appear here.")
        layout.addWidget(self.generate_status, 1)

        browse_btn.clicked.connect(self._on_browse_output)
        self.stack.addWidget(page)

    def _on_back(self):
        idx = self.stack.currentIndex()
        if idx > 0:
            self.stack.setCurrentIndex(idx - 1)

    def _on_next(self):
        idx = self.stack.currentIndex()
        if idx < self.stack.count() - 1:
            self.stack.setCurrentIndex(idx + 1)
            if self.stack.currentIndex() == self.stack.count() - 1 and not self.output_path.text().strip():
                default_name = (self.meta_id.text().strip() or "rulepack") + ".yaml"
                self.output_path.setText(str(Path.cwd() / default_name))

    def _update_step_state(self):
        idx = self.stack.currentIndex()
        titles = [
            "Step 1/5 - Metadata",
            "Step 2/5 - Classes",
            "Step 3/5 - Defaults",
            "Step 4/5 - Rules",
            "Step 5/5 - Generate",
        ]
        self.step_title.setText(titles[idx])
        self.back_btn.setEnabled(idx > 0)
        self.next_btn.setEnabled(idx < self.stack.count() - 1)
        self.generate_btn.setEnabled(idx == self.stack.count() - 1)

    def _on_add_class(self):
        dialog = _ClassEditorDialog(self)
        if dialog.exec() != QtWidgets.QDialog.Accepted:
            return
        self._classes.append(dialog.value())
        self._refresh_classes_table()

    def _on_edit_class(self):
        row = self._selected_row(self.classes_table)
        if row is None or row >= len(self._classes):
            return
        dialog = _ClassEditorDialog(self, self._classes[row])
        if dialog.exec() != QtWidgets.QDialog.Accepted:
            return
        self._classes[row] = dialog.value()
        self._refresh_classes_table()

    def _on_remove_class(self):
        row = self._selected_row(self.classes_table)
        if row is None or row >= len(self._classes):
            return
        self._classes.pop(row)
        self._refresh_classes_table()

    def _on_add_rule(self):
        dialog = _RuleEditorDialog(self)
        if dialog.exec() != QtWidgets.QDialog.Accepted:
            return
        self._rules.append(dialog.value())
        self._refresh_rules_table()

    def _on_edit_rule(self):
        row = self._selected_row(self.rules_table)
        if row is None or row >= len(self._rules):
            return
        dialog = _RuleEditorDialog(self, self._rules[row])
        if dialog.exec() != QtWidgets.QDialog.Accepted:
            return
        self._rules[row] = dialog.value()
        self._refresh_rules_table()

    def _on_remove_rule(self):
        row = self._selected_row(self.rules_table)
        if row is None or row >= len(self._rules):
            return
        self._rules.pop(row)
        self._refresh_rules_table()

    def _refresh_classes_table(self):
        self.classes_table.setRowCount(len(self._classes))
        for row, item in enumerate(self._classes):
            self.classes_table.setItem(row, 0, QtWidgets.QTableWidgetItem(str(item.get("id") or "")))
            self.classes_table.setItem(row, 1, QtWidgets.QTableWidgetItem(str(item.get("name") or "")))
            self.classes_table.setItem(row, 2, QtWidgets.QTableWidgetItem(", ".join(item.get("keywords") or [])))
            self.classes_table.setItem(
                row, 3, QtWidgets.QTableWidgetItem(", ".join(item.get("path_candidates") or []))
            )
        self.classes_table.resizeColumnsToContents()

    def _refresh_rules_table(self):
        self.rules_table.setRowCount(len(self._rules))
        for row, item in enumerate(self._rules):
            check = item.get("check") or {}
            self.rules_table.setItem(row, 0, QtWidgets.QTableWidgetItem(str(item.get("id") or "")))
            self.rules_table.setItem(row, 1, QtWidgets.QTableWidgetItem(str(item.get("title") or "")))
            self.rules_table.setItem(row, 2, QtWidgets.QTableWidgetItem(", ".join(item.get("class_in") or [])))
            self.rules_table.setItem(row, 3, QtWidgets.QTableWidgetItem(str(item.get("relation") or "")))
            self.rules_table.setItem(row, 4, QtWidgets.QTableWidgetItem(str(check.get("type") or "")))
            self.rules_table.setItem(row, 5, QtWidgets.QTableWidgetItem(str(check.get("min_distance_m") or "")))
            self.rules_table.setItem(row, 6, QtWidgets.QTableWidgetItem(str(item.get("severity") or "")))
            self.rules_table.setItem(row, 7, QtWidgets.QTableWidgetItem(str(item.get("explain_short") or "")))
        self.rules_table.resizeColumnsToContents()

    def _on_browse_output(self):
        current = self.output_path.text().strip()
        start_dir = str(Path(current).parent) if current else str(Path.cwd())
        chosen, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save Rulepack YAML",
            str(Path(start_dir) / ((self.meta_id.text().strip() or "rulepack") + ".yaml")),
            "Rulepack YAML (*.yaml *.yml)",
        )
        if chosen:
            self.output_path.setText(chosen)

    def _collect_input_data(self) -> Dict[str, Any]:
        return {
            "rulepack": {
                "id": self.meta_id.text().strip(),
                "name": self.meta_name.text().strip(),
                "version": self.meta_version.text().strip(),
                "author": self.meta_author.text().strip(),
                "description": self.meta_description.toPlainText().strip(),
            },
            "classes": list(self._classes),
            "defaults": {
                "constraints": {
                    "max_move_m": float(self.max_move_spin.value()),
                    "z_move_allowed": bool(self.z_move_allowed.isChecked()),
                }
            },
            "rules": list(self._rules),
        }

    def _on_generate(self):
        input_data = self._collect_input_data()
        input_errors = validate_rulepack_input(input_data)
        if input_errors:
            self._show_errors("Input validation failed", input_errors)
            return

        output_data = build_rulepack_yaml(input_data)
        output_errors = validate_rulepack_output(output_data)
        if output_errors:
            self._show_errors("Generated YAML validation failed", output_errors)
            return

        output_path_text = self.output_path.text().strip()
        if not output_path_text:
            self._show_errors("Output path required", ["[output_path] choose where to save the .yaml file"])
            return

        target_path, extension_fixed = ensure_yaml_extension(Path(output_path_text))
        written_path = write_rulepack_yaml(output_data, target_path)
        self.generated_rulepack_path = written_path

        note = ""
        if extension_fixed:
            note = f"\nOutput extension adjusted to: {written_path.name}"
        msg = f"Rulepack generated:\n{written_path}{note}"
        self.generate_status.setPlainText(msg)
        QtWidgets.QMessageBox.information(self, "Rulepack Generated", msg)
        self.accept()

    def _show_errors(self, title: str, errors: List[str]):
        text = "\n".join(f"- {error}" for error in errors)
        self.generate_status.setPlainText(text)
        QtWidgets.QMessageBox.warning(self, title, text)

    @staticmethod
    def _selected_row(table: QtWidgets.QTableWidget) -> Optional[int]:
        selected = table.selectionModel().selectedRows()
        if not selected:
            return None
        return int(selected[0].row())
