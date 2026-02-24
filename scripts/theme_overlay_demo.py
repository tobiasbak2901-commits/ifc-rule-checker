from __future__ import annotations

import sys

from PySide6 import QtCore, QtWidgets

from ui.theme import DARK_THEME, dropdown_menu_overrides, normalize_stylesheet


class OverlayThemeDemo(QtWidgets.QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Overlay Theme Demo")
        self.resize(680, 420)
        self.setObjectName("OverlayThemeDemo")
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._open_context_menu)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QtWidgets.QLabel("Dark overlay surfaces: dropdowns, menus, context menu, tooltip, modal")
        title.setWordWrap(True)
        layout.addWidget(title, 0)

        combo_row = QtWidgets.QHBoxLayout()
        combo_row.setSpacing(8)
        for label_text in ("Name", "Type", "System", "GlobalId"):
            label = QtWidgets.QLabel(label_text)
            combo = QtWidgets.QComboBox()
            combo.addItems([f"{label_text} A", f"{label_text} B", f"{label_text} C"])
            combo_row.addWidget(label, 0)
            combo_row.addWidget(combo, 1)
        layout.addLayout(combo_row, 0)

        menu_btn = QtWidgets.QPushButton("Open menu")
        menu_btn.setToolTip("Tooltip should use dark surface and readable text.")
        menu = QtWidgets.QMenu(menu_btn)
        menu.addAction("Action one")
        menu.addAction("Action two")
        disabled = menu.addAction("Disabled action")
        disabled.setEnabled(False)
        menu.addSeparator()
        menu.addAction("Last action")
        menu_btn.setMenu(menu)
        layout.addWidget(menu_btn, 0)

        modal_btn = QtWidgets.QPushButton("Open modal panel")
        modal_btn.clicked.connect(self._open_modal)
        layout.addWidget(modal_btn, 0)

        hint = QtWidgets.QLabel("Right click anywhere in this window for a context menu.")
        hint.setObjectName("OverlayHint")
        layout.addWidget(hint, 0)
        layout.addStretch(1)

        self._apply_style()

    def _apply_style(self) -> None:
        stylesheet = f"""
            QWidget#OverlayThemeDemo {{
                background: {DARK_THEME.colors.background};
                color: {DARK_THEME.colors.text_primary};
                font-size: 13px;
            }}
            QLabel#OverlayHint {{
                color: {DARK_THEME.colors.text_secondary};
            }}
            QPushButton, QComboBox {{
                min-height: 28px;
                padding: 4px 10px;
                border-radius: 8px;
                border: 1px solid rgba(255, 255, 255, 38);
                background: {DARK_THEME.colors.panel_overlay};
                color: {DARK_THEME.colors.text_primary};
            }}
            QPushButton:hover, QComboBox:hover {{
                border-color: rgba(255, 95, 178, 128);
            }}
            {dropdown_menu_overrides(DARK_THEME)}
        """
        self.setStyleSheet(normalize_stylesheet(stylesheet, DARK_THEME))

    def _open_context_menu(self, pos: QtCore.QPoint) -> None:
        menu = QtWidgets.QMenu(self)
        menu.addAction("Context action")
        menu.addAction("Another action")
        menu.exec(self.mapToGlobal(pos))

    def _open_modal(self) -> None:
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Modal panel")
        layout = QtWidgets.QVBoxLayout(dialog)
        layout.addWidget(QtWidgets.QLabel("Modal content should be readable in dark mode."))
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.exec()


def main() -> int:
    app = QtWidgets.QApplication(sys.argv)
    window = OverlayThemeDemo()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
