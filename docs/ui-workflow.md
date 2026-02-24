# UI Workflow: Clash Detection (Guided)

This project now uses a guided clash workflow in the right-side `Clash Detection` panel:

1. `Setup`
2. `Results`
3. `Fix`

The 3D viewer remains mounted in the center and is not remounted when switching panel tabs or toggling panel visibility.

## Workflow State

Runtime state is tracked by `ClashWorkflowState` (`ui/clash_workflow_state.py`):

- `activeStep`: `setup | results | fix`
- `selectedTestId`
- `lastRun`:
  - `time`
  - `results_count`
- `selectedClashId`

## Step Behavior

## Setup

- Configure:
  - Search sets A/B (multi-select lists)
  - Clash type (`Hard | Clearance | Tolerance`)
  - Threshold in mm (for Clearance/Tolerance)
  - Grouping (check + reorder)
  - Ignore rules (same element/system/model)
- Primary CTA: `Run clash test`
- Secondary: `Advanced...` (collapsible)

## Results

- Shows summary:
  - `N clashes found`
  - last run time
  - active test
- Primary CTA:
  - `Review clashes` (no selection)
  - `Open next clash` (if a clash is already selected)
- Secondary: `Re-run test`
- Disabled before first run with empty state:
  - `Run a test to see results`

## Fix

- Shows selected clash details + AI summary text.
- Primary CTA:
  - `Apply suggested fix` (if recommendation exists)
  - `Generate fixes` (otherwise)
- Secondary:
  - `Show alternatives`
  - `Mark as approved`
  - `Assign`
  - `Explain / Suggest fix`
- Disabled before first run and when no clash is selected.

## Panel Bar

Panel bar order reflects workflow:

1. `OBJ` (Model)
2. `SET` (Search Sets)
3. `CLH` (Clash)
4. `ISS` (Issues placeholder)
5. `AI` (assistant, pinned bottom)

Shortcuts:

- `Ctrl+1`: toggle Object Tree
- `Ctrl+2`: toggle Search Sets
- `Ctrl+3`: toggle Clash
- `Ctrl+4`: toggle AI

Panel open/closed and dock side (left/right) are stored in `QSettings` key `workspace/panels_v1`.
