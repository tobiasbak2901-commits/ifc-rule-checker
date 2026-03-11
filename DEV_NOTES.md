# DEV Notes

## Scope Choices
- Kept the existing top navigation (`Project | Analyze | Inspect | Decisions | Issues`) and restructured behavior/layout without removing working analysis/fix flows.
- `Search Sets` panel was moved into the left Analyze area (with issues list) to match the requested mode separation.
- Kept fix-generation actions inside Decisions surfaces and removed them from the Analyze viewer toolbar.

## Selection Behavior
- Single-click in 3D now updates a compact Analyze `Selection` box only (no mode switch).
- Double-click in Analyze opens Inspect on the same selected element.
- Added `Inspect Selected` button in Analyze as a dedicated explicit Inspect action.
- Selection is synchronized across mode switches.

## Properties Panel
- Properties dock remains available only in Inspect mode.
- Added global property search (matches across all groups, not just current category).
- Added Favorites starring:
  - Right-click on property row: star/unstar
  - Double-click property row: toggle star
  - Favorites persist in `~/.ifc_rule_checker_favorites.json`

## Context Menu
- Simplified to requested Revizto-like set:
  - Isolate
  - Isolate in transparency
  - Transparency (toggle)
  - Focus on selection
  - Fit selection
  - Show Properties

## Classification Transparency
- Implemented UI-facing classification candidate ranking with explainability:
  - weighted signals
  - System/Group weighted as primary when present
  - top-3 candidates shown in Inspect Summary
  - classification source label shown
  - Rule Match Debug now shows checked property paths per matcher and matched/failed signals
- Kept rulepack compatibility and existing downstream fix-generation behavior by preserving final `class_name`, `utility_type`, and confidence fields.

## Layout Pass (Analyze/Inspect/Decisions)
- Reorganized Analyze left side into:
  - Search Sets (prominent top section)
  - Clash Results (middle issue/status section)
  - Bottom action section (`Active Search Set` + `Detect Clashes`)
- Kept search-set query editor widgets as hidden placeholders to avoid removing existing internals while following the requested visual structure.
- Removed `Generate Fixes` from the 3D toolbar. Fix generation remains in Decisions (Decision Card / Decisions actions).

## Icon Toolbar Pass
- Replaced text-first 3D toolbar controls with `IconToolButton` components (`ui/icon_tool_button.py`) using Qt standard icons and rich tooltips (title + shortcut + one-line hint).
- Grouped toolbar actions with separators:
  - Navigation: Orbit, Pan, Zoom, Focus
  - View tools: Isolate, Show All, Transparency, Section Box
  - Measure: Measure Distance, Measure Minimum Distance
  - Analysis (Analyze mode only): Detect Clashes, Generate Issues
- Added keyboard shortcuts used in tooltip text:
  - `F`, `M`, `Shift+M`, `I`, `Shift+I`, `T`, `B`, `Ctrl+D`, `Ctrl+G`
- `Section Box` is implemented as a non-breaking placeholder toggle (logs state change) because no clipping box feature existed yet.

## Context Menu + Properties Behavior
- Updated 3D context menu to the requested subset:
  - Isolate
  - Isolate in transparency
  - Transparency (toggle)
  - Focus on selection
  - Fit selection
  - Show Properties
- `Show Properties` now **does not auto-switch tabs**. It keeps current mode, syncs selection, and preloads the Inspect properties data; if already in Inspect, it focuses the Properties panel.

## Find Objects Panel

See [docs/find-objects.md](docs/find-objects.md) for the full reference.

Summary of current layout and behavior:

- **Minimal header**: single primary row `[Scope combo] [Quick search] [Find all]`,
  plus a meta row with filter chips and `+ Add filter`.
- **Filter chips**: each active filter (search text, non-Everywhere scope, every
  condition row) renders as a removable chip.  Clicking `×` on a chip removes
  that specific filter and re-runs the preview.
- **Advanced filters**: condition rows with AND/OR group logic.  The operator
  list is filtered to kinds appropriate for the selected property
  (`number / string / boolean / enum / enum_dynamic`).
- **Numeric shorthand**: entering `<100`, `>50`, `<=200`, `>=75` in a numeric
  value field is silently translated to the correct operator + bare value
  inside `ConditionRow.descriptor()`.
- **Debounced preview**: any change to search, scope, or conditions schedules a
  250 ms debounce that updates the *Matches: N* counter without touching the
  table.  `Find all` still populates the table explicitly.
- **Options menu**: *Prune below result* and *Elements only* live in a `⋯ Options`
  QToolButton/QMenu in the action footer; their underlying checkboxes are kept
  hidden for behavior-code compatibility.

## Search Sets UX Scaffold
- Search Sets list now shows checkbox + count in label (`Set Name (N)`).
- Added `Pick in 3D`:
  - Toggled pick mode adds clicked element GUIDs to a set’s manual selection bucket.
  - Manual picks are merged with query matches in search-set evaluation.
- Added `Filter...` button as placeholder (non-breaking informational dialog).
