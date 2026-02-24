# AI Card Workflow Smoke Test

## Preconditions
- Start app: `python app.py`
- Load IFC + load/import clashes so at least 2 issues exist.
- Ensure rulepack is loaded (`core-v1` or custom).

## Manual Flow
1. Select one clash in Analyze mode.
2. Verify viewer overlay shows `Ponker AI Card` with:
   - stepper (8 steps)
   - confidence pill (`Confidence x.xx`)
   - structured blocks (no chat transcript)
3. In `Responsibility` step:
   - click `Sæt owner: ...`
   - verify step advances and persists after selecting another issue and back.
4. In `Rule basis` step:
   - if rule mapping exists, verify citations block appears.
   - if missing, verify `No standard linked yet` + `Open rulepack mapping` action appears.
5. In `High-impact` step:
   - click `Generér fixes`
   - verify top candidates appear with solves/creates/move/clearance/violations.
   - click `Preview` on a candidate and verify ghost/overlay preview is shown.
6. In `Decision` step:
   - click `Acceptér fix`
   - verify state moves to `Apply/Export`.
7. In `Apply/Export` step:
   - click `Export`
   - verify file is created in `.ponker/exports/ai_fix_<issue>_<timestamp>.json`.
8. In Inspect tab:
   - verify `AI Trace JSON` block is populated.
   - click `Copy trace JSON` and confirm clipboard contains valid JSON.
9. Enter note text in card note field and click `Gem note/antagelse`.
   - verify note is saved and card refreshes.

## Persistence Check
- Confirm `.ponker/ai_card_state.json` exists.
- Verify selected issue key contains:
  - `active_step`
  - `chosen_owner`
  - `chosen_fix_id` (after acceptance)
  - `pinned_assumptions` / `notes`
