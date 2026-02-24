import importlib
from importlib import metadata as importlib_metadata
import os
import subprocess
import sys
from pathlib import Path

if os.environ.get("IFC_FORCE_X11") == "1":
    os.environ["QT_QPA_PLATFORM"] = "xcb"
elif os.environ.get("IFC_FORCE_WAYLAND") == "1":
    os.environ["QT_QPA_PLATFORM"] = "wayland"
elif (
    os.environ.get("XDG_SESSION_TYPE", "").strip().lower() == "wayland"
    and "QT_QPA_PLATFORM" not in os.environ
):
    # Qt + VTK can crash on some Wayland setups (BadWindow/X_ConfigureWindow).
    # Prefer XWayland/xcb by default; allow override with IFC_FORCE_WAYLAND=1.
    os.environ["QT_QPA_PLATFORM"] = "xcb"

if os.environ.get("IFC_FORCE_SOFTWARE_GL") == "1":
    os.environ.setdefault("QT_OPENGL", "software")
    os.environ.setdefault("LIBGL_ALWAYS_SOFTWARE", "1")

if os.environ.get("IFC_DISABLE_HIDPI") == "1":
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"

# Ensure we don't require python OCC unless explicitly installed
os.environ.setdefault("IFCOPENSHELL_USE_PYTHON_OPENCASCADE", "0")

if os.environ.get("PYTHONFAULTHANDLER") == "1":
    import faulthandler
    faulthandler.enable()


_RUNTIME_DEPENDENCIES = ("PySide6", "ifcopenshell", "vtkmodules", "numpy", "matplotlib")
_DEPENDENCY_DISTRIBUTIONS = {
    "PySide6": "PySide6",
    "ifcopenshell": "ifcopenshell",
    "vtkmodules": "vtk",
    "numpy": "numpy",
    "matplotlib": "matplotlib",
}


def _top_level_module(name: str | None) -> str:
    if not name:
        return ""
    return name.split(".")[0]


def _venv_python_candidates() -> list[Path]:
    root = Path(__file__).resolve().parent
    return [
        root / ".venv" / "bin" / "python3",
        root / ".venv" / "bin" / "python",
        root / ".venv" / "Scripts" / "python.exe",
    ]


def _python_can_import(python_bin: Path, module_name: str) -> bool:
    probe = subprocess.run(
        [str(python_bin), "-c", f"import {module_name}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return probe.returncode == 0


def _maybe_reexec_with_project_venv(missing_module: str) -> None:
    if missing_module not in _RUNTIME_DEPENDENCIES:
        return
    if os.environ.get("IFC_RULE_CHECKER_REEXEC") == "1":
        return
    current = Path(sys.executable)
    for candidate in _venv_python_candidates():
        if not candidate.exists():
            continue
        if candidate == current:
            continue
        if not _python_can_import(candidate, "PySide6"):
            continue
        if not _python_can_import(candidate, missing_module):
            continue
        env = dict(os.environ)
        env["IFC_RULE_CHECKER_REEXEC"] = "1"
        os.execve(str(candidate), [str(candidate), str(Path(__file__).resolve()), *sys.argv[1:]], env)


def _exit_missing_dependency(missing_module: str) -> None:
    print(
        f"Afhaengigheden '{missing_module}' mangler. "
        "Koer appen via .venv eller installer dependencies med: "
        "python -m pip install -r requirements.txt",
        file=sys.stderr,
    )
    raise SystemExit(1)

def run_doctor() -> int:
    print("IFC Rule Checker --doctor")
    print(f"Python executable: {Path(sys.executable).resolve()}")
    print(f"Python version: {sys.version.split()[0]}")
    print(
        "Display env: "
        f"XDG_SESSION_TYPE={os.environ.get('XDG_SESSION_TYPE', '-')}, "
        f"WAYLAND_DISPLAY={os.environ.get('WAYLAND_DISPLAY', '-')}, "
        f"DISPLAY={os.environ.get('DISPLAY', '-')}, "
        f"QT_QPA_PLATFORM={os.environ.get('QT_QPA_PLATFORM', '-')}"
    )
    print("Checking required modules in active environment...")
    missing: list[tuple[str, str]] = []
    installed: list[tuple[str, str]] = []
    for module_name in _RUNTIME_DEPENDENCIES:
        try:
            importlib.import_module(module_name)
        except Exception as exc:
            missing.append((module_name, f"{exc.__class__.__name__}: {exc}"))
            continue
        dist_name = _DEPENDENCY_DISTRIBUTIONS.get(module_name, module_name)
        try:
            version = importlib_metadata.version(dist_name)
        except importlib_metadata.PackageNotFoundError:
            version = "unknown"
        installed.append((module_name, version))
    if installed:
        print("Installed:")
        for module_name, version in installed:
            print(f"- {module_name} ({version})")
    if not missing:
        print("Result: OK. No required modules are missing.")
        return 0
    print("Result: Missing or failing modules:")
    for module_name, reason in missing:
        print(f"- {module_name}: {reason}")
    print("Install dependencies with: python -m pip install -r requirements.txt")
    return 1


def _load_runtime():
    try:
        from PySide6 import QtCore, QtWidgets
        from PySide6.QtGui import QFont, QIcon, QSurfaceFormat
    except ModuleNotFoundError as exc:
        missing = _top_level_module(exc.name)
        _maybe_reexec_with_project_venv(missing)
        if missing == "PySide6":
            _exit_missing_dependency(missing)
        raise

    try:
        from ui.main_window import MainWindow
    except ModuleNotFoundError as exc:
        missing = _top_level_module(exc.name)
        _maybe_reexec_with_project_venv(missing)
        if missing in _RUNTIME_DEPENDENCIES:
            _exit_missing_dependency(missing)
        raise
    return QtCore, QtWidgets, QFont, QIcon, QSurfaceFormat, MainWindow


def _present_main_window(window, app, QtCore) -> None:
    try:
        screen = app.primaryScreen()
        if screen is not None:
            available = screen.availableGeometry()
            frame = window.frameGeometry()
            frame.moveCenter(available.center())
            window.move(frame.topLeft())
    except Exception:
        pass

    try:
        state = window.windowState()
        state = state & ~QtCore.Qt.WindowMinimized
        state = state | QtCore.Qt.WindowActive
        window.setWindowState(state)
    except Exception:
        pass

    window.show()
    window.raise_()
    window.activateWindow()
    QtCore.QTimer.singleShot(150, window.raise_)
    QtCore.QTimer.singleShot(200, window.activateWindow)


def main():
    QtCore, QtWidgets, QFont, QIcon, QSurfaceFormat, MainWindow = _load_runtime()

    if os.environ.get("IFC_DISABLE_HIDPI") == "1":
        QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_DisableHighDpiScaling)
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_ShareOpenGLContexts)
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_UseDesktopOpenGL)
    if os.environ.get("QT_OPENGL") == "software" or os.environ.get("LIBGL_ALWAYS_SOFTWARE") == "1":
        QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_UseSoftwareOpenGL)

    fmt = QSurfaceFormat()
    fmt.setDepthBufferSize(24)
    fmt.setStencilBufferSize(8)
    fmt.setVersion(3, 2)
    fmt.setProfile(QSurfaceFormat.CoreProfile)
    QSurfaceFormat.setDefaultFormat(fmt)

    app = QtWidgets.QApplication([])
    app.setApplicationName("IFC Rule Checker")
    app.setDesktopFileName("ifc-rule-checker")
    base_font = app.font()
    if int(base_font.pointSize()) < 14:
        base_font.setPointSize(14)
    base_font.setWeight(QFont.Weight.Medium)
    app.setFont(base_font)

    assets_dir = Path(__file__).resolve().parent / "assets"
    icon_candidates = [
        assets_dir / "branding" / "exports" / "ponker_icon_512.png",
        assets_dir / "branding" / "ponker_icon_square.svg",
        assets_dir / "ponker-icon.svg",
        assets_dir / "ifc-rule-checker.svg",
    ]
    icon_path = next((p for p in icon_candidates if p.exists()), None)
    if icon_path is not None and icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    w = MainWindow()
    if icon_path is not None and icon_path.exists():
        w.setWindowIcon(QIcon(str(icon_path)))
    w.resize(1200, 800)
    _present_main_window(w, app, QtCore)
    app.exec()


if __name__ == "__main__":
    if "--doctor" in sys.argv[1:]:
        raise SystemExit(run_doctor())
    main()
