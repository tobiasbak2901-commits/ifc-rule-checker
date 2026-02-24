# Rule System Strategy (MVP)

## Principles
- Core rules are owned by the application and are not user-editable.
- Users can only adjust exposed parameters through the UI.
- Rulepacks are versioned and selected per project.
- Uploading arbitrary rule files is not supported in MVP.
- Custom rulepacks are a paid/enterprise feature.

## UI Policy
- Rulepack selection is offered as a fixed list of versioned packs.
- Parameter adjustments are limited to numeric controls (distances, tolerances, max moves).
- No file pickers or direct rule file editing in the UI.

## Suggested UI Copy
- Rulepack menu: "Core v1.0", "Custom rulepacks (Enterprise)" (disabled)
- Parameters dialog: "Default clearance (mm)", "Clearance tolerance (mm)", "Default max move (mm)"
