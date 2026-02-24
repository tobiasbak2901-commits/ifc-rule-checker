# Classification Mode

## What It Does

`GO` from AI Views step 1 (`Fix classification`) now opens Object Tree -> `Properties` and enables a guided `Classification Mode`.

The mode shows a clear banner with:

- why classification is needed
- current element being handled
- 1-3 suggestion chips
- `Apply classification`, `Next unclassified`, and `Exit` actions

## Flow

1. AI Views `GO` (classify) opens `objectTree` panel and switches to `Properties`.
2. Classification mode is enabled with source `aiViewsGo` and a focus element id.
3. If no valid unclassified selection exists, first unclassified element is selected.
4. Suggestions are shown from AI candidates, with heuristic fallback.
5. `Apply classification` writes override via central API and persists it.
6. Unclassified count updates immediately in AI Views.

If an element has no system/group, apply also writes a minimal system fallback from the chosen classification label so the element exits the unclassified bucket.

## Override Storage

Classification overrides are kept in-memory in:

- `MainWindow._class_overrides`

and persisted through `QSettings` per project under:

- `classification/overrides_v1`

Element metadata also gets a virtual `ponkerClassification` payload in `ifc_meta` for properties display.

## Suggestions

Priority:

1. Existing classifier candidates (`_classification_candidates`)
2. Heuristic fallback when needed:
   - name contains `drain` -> `Drainage`
   - IFC type contains `pipe` -> `Plumbing`
   - IFC type contains `cable` -> `Electrical`
   - fallback -> `Unknown`

## Extending Later

- Add richer scores/sources from dedicated AI service into `classificationSuggestionsForElement`.
- Add additional discipline/type heuristics in the same function.
- Keep `setElementClassification(...)` as single write path to avoid diverging state.
