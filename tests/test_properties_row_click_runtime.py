import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6 import QtCore, QtWidgets
    from PySide6.QtTest import QTest
except Exception as exc:  # pragma: no cover - optional runtime dependency
    pytest.skip(f"PySide6 runtime unavailable: {exc}", allow_module_level=True)

try:
    from ui.main_window import InspectPropertyGrid, PropertyRow
except Exception as exc:  # pragma: no cover - optional runtime dependency chain (ifcopenshell/vtk/etc)
    pytest.skip(f"Main window runtime dependencies unavailable: {exc}", allow_module_level=True)


def _app() -> QtWidgets.QApplication:
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    return app


def test_clicking_value_cell_text_toggles_checkbox_selection() -> None:
    app = _app()
    row = PropertyRow(
        label="IfcType",
        value="IfcPipeSegment",
        source_group="item",
        source_key="type",
        selection_key="item|type",
        selected=False,
    )
    row.resize(560, 36)
    row.show()
    app.processEvents()

    assert row.is_selected() is False
    assert row.select_cb.isChecked() is False

    QTest.mouseClick(row.value_w, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier, row.value_w.rect().center())
    app.processEvents()

    assert row.is_selected() is True
    assert row.select_cb.isChecked() is True
    assert bool(row.property("selected")) is True

    row.close()


def test_clicking_copy_button_does_not_toggle_row_selection() -> None:
    app = _app()
    row = PropertyRow(
        label="Name",
        value="Pipe-101",
        source_group="item",
        source_key="name",
        selection_key="item|name",
        selected=False,
    )
    row.resize(560, 36)
    row.show()
    app.processEvents()

    assert row.copy_btn.isVisible() is True
    assert row.is_selected() is False

    QTest.mouseClick(row.copy_btn, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier, row.copy_btn.rect().center())
    app.processEvents()

    assert row.is_selected() is False
    assert row.select_cb.isChecked() is False
    assert bool(row.property("selected")) is False

    row.close()


def test_clicking_favorite_button_does_not_toggle_row_selection() -> None:
    app = _app()
    row = PropertyRow(
        label="System",
        value="Heating",
        source_group="item",
        source_key="system",
        selection_key="item|system",
        selected=False,
    )
    row.resize(560, 36)
    row.show()
    app.processEvents()

    assert row.favorite_btn.isVisible() is True
    assert row.is_selected() is False

    QTest.mouseClick(row.favorite_btn, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier, row.favorite_btn.rect().center())
    app.processEvents()

    assert row.is_selected() is False
    assert row.select_cb.isChecked() is False
    assert bool(row.property("selected")) is False

    row.close()


def test_arrow_keys_navigate_between_rows_without_toggling_selection() -> None:
    app = _app()
    grid = InspectPropertyGrid()
    grid.add_group("main", "Main")
    grid.set_group_rows(
        "main",
        [
            {
                "label": "Type",
                "value": "IfcPipeSegment",
                "source_group": "item",
                "source_key": "type",
                "selection_key": "item|type",
                "selected": False,
                "selectable": True,
            },
            {
                "label": "System",
                "value": "Heating",
                "source_group": "item",
                "source_key": "system",
                "selection_key": "item|system",
                "selected": False,
                "selectable": True,
            },
        ],
    )
    grid.resize(700, 280)
    grid.show()
    app.processEvents()

    row_a = grid._rows_by_selection_key.get("item|type")
    row_b = grid._rows_by_selection_key.get("item|system")
    assert isinstance(row_a, PropertyRow)
    assert isinstance(row_b, PropertyRow)

    row_a.setFocus(QtCore.Qt.TabFocusReason)
    app.processEvents()
    assert row_a.hasFocus() is True

    QTest.keyClick(row_a, QtCore.Qt.Key_Down)
    app.processEvents()
    assert row_b.hasFocus() is True
    assert row_a.is_selected() is False
    assert row_b.is_selected() is False

    QTest.keyClick(row_b, QtCore.Qt.Key_Up)
    app.processEvents()
    assert row_a.hasFocus() is True
    assert row_a.is_selected() is False
    assert row_b.is_selected() is False

    grid.close()
