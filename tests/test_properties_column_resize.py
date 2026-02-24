from pathlib import Path


def _source() -> str:
    return Path("ui/main_window.py").read_text(encoding="utf-8")


def test_property_table_has_draggable_header_divider() -> None:
    source = _source()
    assert 'self.column_divider = QtWidgets.QFrame(self.table_header)' in source
    assert 'self.column_divider.setObjectName("InspectColumnDivider")' in source
    assert "self.column_divider.setCursor(QtCore.Qt.SizeHorCursor)" in source
    assert "self.column_divider.installEventFilter(self)" in source
    assert "QFrame#InspectColumnDivider {" in source


def test_column_resize_persists_property_width_in_user_settings() -> None:
    source = _source()
    assert "def _property_column_width_settings_key() -> str:" in source
    assert 'return "inspect/property_col_width_v1"' in source
    assert 'settings = QtCore.QSettings("Ponker", "Resolve")' in source
    assert "def _load_property_column_width_preference(self) -> None:" in source
    assert "def _save_property_column_width_preference(self) -> None:" in source


def test_column_width_constraints_and_shared_application_across_rows() -> None:
    source = _source()
    assert "PROPERTY_COLUMN_MIN_WIDTH = 180" in source
    assert "VALUE_COLUMN_MIN_WIDTH = 220" in source
    assert "def _column_width_bounds(self) -> tuple[int, int]:" in source
    assert "max_property = max(property_min, data_width - value_min)" in source
    assert "value_max = int(max(int(PropertyRow.VALUE_COLUMN_MIN_WIDTH), int(data_width - property_min)))" in source
    assert "def _apply_row_column_width(self, row: PropertyRow, *, property_width: int, value_width: int) -> None:" in source
    assert "row.label_w.setMaximumWidth(int(property_width))" in source
    assert "row.value_cell.setMaximumWidth(int(value_width))" in source
