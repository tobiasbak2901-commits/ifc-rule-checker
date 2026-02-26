# Ponker Resolve

A desktop application for IFC model analysis, clash detection, and rule-based issue management.

## Features

- **3D Viewer** — Interactive VTK-based viewer with orbit, pan, zoom, isolate, transparency, and section box tools
- **Clash Detection** — Spatial broadphase + narrowphase clash detection with incremental caching and identity persistence across runs
- **Rule Engine** — Configurable rulepacks (YAML) with classifiers, clearance rules, and policy constraints
- **AI Cards** — AI-assisted fix generation and decision support for detected issues
- **Search Sets** — Named element sets defined by queries or manual 3D picks
- **Properties Panel** — IFC property inspection with favorites, presets, and global search
- **BCF Export** — Export issues to BCF format

## Requirements

- Python 3.13+
- [ifcopenshell](https://ifcopenshell.org/)
- PySide6
- VTK
- NumPy, Matplotlib, PyYAML

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
python app.py
```

### Environment variables

| Variable | Effect |
|---|---|
| `IFC_FORCE_X11=1` | Force XCB/X11 platform |
| `IFC_FORCE_WAYLAND=1` | Force Wayland platform |
| `IFC_FORCE_SOFTWARE_GL=1` | Use software OpenGL renderer |
| `IFC_DISABLE_HIDPI=1` | Disable HiDPI scaling |

## Running tests

```bash
pytest tests/
```

## Project structure

```
app.py                  Entry point
models.py               Core data models
clash_detection.py      Clash detection engine
rules.py                Rule evaluation
rulepack_generator.py   Rulepack authoring
search_sets.py          Search set queries
ui/                     Qt UI components
  main_window.py        Main application window
  panels/               Dock panels (properties, issues, clash, etc.)
  viewer.py             3D viewer widget
viewer/                 Viewer subsystems (auto-fit, model activation)
clash_tests/            Clash test definitions and benchmarks
ai/                     AI provider integrations
rulepack/               Default and example rulepacks (YAML)
standards/              Referenced building standards excerpts
tests/                  Test suite
```
