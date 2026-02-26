# Find Objects

The Find Objects panel lets users search and filter model elements by
quick-search text, scope, and structured conditions.  Results can be
selected, isolated, or saved as a Search Set.

---

## Header layout

```
[ Scope combo ] [ Quick search input ] [ Find all ]
[ filter chips · · · ]  [ + Add filter ]
```

- **Scope combo** — sets which elements are candidates:
  - *Everywhere* (default): all indexed elements.
  - *Within current selection*: elements whose GUIDs are in the current
    Object Tree selection.
  - *Search below current selection*: elements that are descendants of
    selected tree nodes.
  - *Within search set*: elements belonging to the active Search Set.
- **Quick search** — plain-text substring/token match against name, type,
  system, and file fields.  Cleared by the `×` button or the chip (x).
- **Find all** button — executes the full search and populates the results
  table.

---

## Match-count preview (debounce)

A **250 ms debounced preview** updates the *Matches: N* counter
automatically whenever the scope, quick-search text, or any condition
changes.  The preview runs the same filter logic as Find all but skips
table population, keeping the interaction lightweight.

The results table is only populated when **Find all** is clicked
explicitly (or Enter is pressed in the quick-search field).

---

## Filter chips

Active filters are shown as compact removable chips below the header:

| Chip label | Produced by | Remove action |
|---|---|---|
| `Search: <text>` | Quick-search text is non-empty | Clears the search field |
| `Scope: <label>` | Scope is not *Everywhere* | Resets combo to Everywhere |
| `<Prop> <op> <val>` | Each active condition row | Removes that condition row |

The chip area is hidden when there are no active filters.

---

## Advanced filters (condition groups)

Click **+ Add filter** in the header meta row (or the *Advanced filters*
toggle) to open the conditions panel.

- Each **condition row** has: *Category* combo → *Property* combo →
  *Operator* combo → *Value* input.
- The **operator list is filtered by property kind**:
  - `number` → equals, greater than, less than, exists
  - `string` → contains, starts with, ends with, equals, in list, exists
  - `boolean` → equals, exists
  - `enum` → equals, in list, exists
  - `enum_dynamic` → equals, contains, starts with, ends with, in list, exists
- **Numeric shorthand input**: for `number`-kind properties the value field
  accepts shorthand comparison syntax.  Entering `<100`, `<=200`, `>50`, or
  `>=75` is automatically interpreted as the corresponding operator
  (`less_than` / `greater_than`) with the bare number as the value.  The
  UI field is not rewritten; interpretation happens at query time inside
  `ConditionRow.descriptor()`.
- Conditions within a group are combined with **AND** or **OR** (toggled
  per group via the group toolbar).
- **Add group** nests a child group; child groups inherit AND/OR logic
  independently.

---

## Results section

```
[ Matches: N ]                          [ Scope: <label> ]
┌─────────────────────────────────────────────────────────┐
│ ☐  Name          Type     System     File               │
│ ☐  ...                                                  │
└─────────────────────────────────────────────────────────┘
```

- **Matches: N** — live preview count (updates on every debounced change).
- **Scope: \<label\>** — mirrors the active scope combo selection.
- Table columns: checkbox (for selection), Name, Type, System, File.
- Empty state shows a context-sensitive message (no model, no scope
  selection, no matches, etc.).

---

## Actions footer

```
[ ⋯ Options ]              [ Select all ] [ Isolate ] [ Focus ] [ Clear ]
```

- **Select all** — selects all result GUIDs in the Object Tree and viewer.
- **Isolate** — isolates result elements in the 3D viewer.
- **Focus** — focuses the camera on result elements.
- **Clear** — clears search text and resets scope to Everywhere.
- **⋯ Options** menu (overflow):
  - *Prune below result* — hides tree nodes that have no matching
    descendants.
  - *Elements only* — excludes group/container nodes from results.

---

## Save / update Search Set

The footer below the action buttons contains **Save as Search Set…** and
**Update selected Search Set** buttons.  These capture the current scope +
conditions + quick-search into a reusable Search Set definition.
