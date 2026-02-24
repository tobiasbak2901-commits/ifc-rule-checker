# Classification Overrides

## Purpose

Manual/AI classification accepts from the “Hjælp mig med at klassificere” modal are now handled through a central API and persisted per project.

## API

Implemented in `ui/main_window.py`:

- `setElementClassification(elementId, payload)`
- `clearElementClassification(elementId)`

Supported payload fields:

- `classification` (required)
- `confidence` (optional)
- `source` (`manual` or `ai`)
- `system` (optional)
- `discipline` (optional)

Element IDs are normalized through `_resolve_element_key(...)` to avoid GUID key mismatches.

## Data Model

Runtime source-of-truth:

- `self._class_overrides: Dict[str, Dict[str, object]]`

Stored override payload includes:

- `label` / `classification`
- `confidence`
- `source`
- `updatedAt`
- optional `system`
- optional `discipline`

Element metadata is also updated with:

- `elem.class_name`
- `elem.class_confidence`
- `elem.ifc_meta["ponkerClassification"]`

## Persistence

Overrides are persisted in `QSettings` as JSON:

- key: `classification/overrides_v1`
- shape: `{ "<projectId>": { "<elementGuid>": overridePayload } }`

Project key resolution uses IFC path stem when available.

## Modal Behavior

In `_show_ai_classification_menu`:

- `Acceptér <label> (score)`:
  - disables clicked button while processing
  - calls `setElementClassification(..., source="ai")`
  - closes modal on success
  - shows toast: `Classified as <label>.`

- `Ryd manuel klassifikation`:
  - disables clicked button while processing
  - calls `clearElementClassification(...)`
  - closes modal on success
  - shows toast: `Classification cleared.`

Errors are logged and surfaced in status bar.

## UI Reactivity

After each change:

- issue/fix panels refresh
- AI views refresh is triggered immediately (`ObjectTreePanel.refresh_now()`)
- AI card refresh is scheduled
- selected element properties refresh

This ensures `Unclassified elements` count updates from the same override source.
