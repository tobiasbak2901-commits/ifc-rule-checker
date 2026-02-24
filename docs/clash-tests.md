# Clash Tests (Revizto baseline)

## Implementation Notes

### Data model
Clash test baseline is implemented in `clash_tests/`:

- `clash_tests/models.py`
  - `ClashTest`
  - `SearchSet`
  - `IgnoreRule`
  - `ClashResult`
  - `ClashGroup`
  - `Viewpoint`
  - `ClashType` (`hard`, `tolerance`, `clearance`)
  - `ClashResultStatus` (`new`, `triaged`, `closed`)
- `clash_tests/store.py`
  - SQLite persistence and schema management.
- `clash_tests/engine.py`
  - Deterministic clash run per test config.
- `clash_tests/grouping.py`
  - Element A / Proximity / Level grouping logic.

SQLite file location:

- `./.ponker/clash_tests.db`

Tables created:

- `clash_tests`
- `search_sets`
- `clash_results`
- `clash_groups`
- `ignore_rules`
- `issue_views`

### Create a clash test

1. Open **Analyze** mode.
2. Click **Clash test settings**.
3. Configure:
   - Search sets A/B (multi-select)
   - Clashing type (`Hard`, `Tolerance`, `Clearance`)
   - Value in mm (used for tolerance/clearance)
   - Ignore rules (add/remove + enable/disable)
   - Grouping order and enabled keys
   - Proximity cell size (meters)
   - Auto viewpoint / auto screenshot flag
4. Save.

The saved test is marked active and persisted in `clash_tests.db`.

### Run clash test and where results are stored

1. Click **Detect Clashes**.
2. Engine runs broadphase + narrowphase using active test settings.
3. Ignore rules are applied before result creation.
4. Group keys are computed:
   - `elementAKey`
   - `proximityCell` (`floor(x/p), floor(y/p), floor(z/p)`)
   - `levelId` (or `UnknownLevel` if level intervals unavailable)
5. Groups and viewpoints are generated.
6. Results are persisted to:
   - `clash_results`
   - `clash_groups`
   - `issue_views`

UI behavior:

- Left issue list supports grouped/ungrouped rendering.
- Group headers show clashes under each group.
- Selecting a clash shows properties including clash metadata and viewpoint camera data.

### Notes

- Level grouping falls back to `UnknownLevel` when IFC storey intervals are unavailable.
- Screenshot capture is currently stubbed (`captureScreenshot(viewpoint)`), but viewpoint metadata is persisted.
