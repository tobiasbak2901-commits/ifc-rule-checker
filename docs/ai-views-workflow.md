# AI Views Workflow

## Guided Workflow (Quick Start)

AI Views now includes a compact stepper that guides users through the recommended order:

1. `Fix classification`
2. `Run clash test`
3. `Review clashes`
4. `Focus high-risk`

Each step exposes:

- status: `Done`, `Next`, or `Blocked`
- short explanation of why the step matters
- primary `Go` action button (enabled only when actionable)

## Step Logic

Workflow state is derived (not persisted) from model/clash counts:

- `nextStep = classify` when `unclassifiedCount > 0`
- `nextStep = runClash` when `unclassifiedCount == 0` and clash test has not run
- `nextStep = reviewClashes` when clashes exist (`clashingCount > 0`)
- `nextStep = highRisk` when high-risk buckets exist (`highRiskCount > 0`)
- otherwise `nextStep = done`

Status assignment:

- steps before `nextStep` become `Done`
- the current `nextStep` is `Next`
- steps after `nextStep` are `Blocked`
- when `nextStep = done`, all steps are `Done`

## CTA Behavior and Fallbacks

### Workflow CTAs

- `classify`
  - selects first unclassified element
  - switches Object Tree to `Properties`
  - enters Inspect mode and opens AI classification helper when available
  - fallback message: use Properties when full classify flow is unavailable

- `runClash`
  - opens `CLH` panel
  - switches clash workflow to `Setup`
  - focuses `Run clash test` button when possible
  - ensures active/default clash test is loaded

- `reviewClashes`
  - opens `CLH` panel
  - switches clash workflow to `Results`

- `highRisk`
  - selects top high-risk bucket elements
  - frames selection in viewer

### Card CTAs

- `Open clashes`
  - disabled when no clashing elements
  - disabled reason:
    - `No clashes yet. Run a clash test first.` (before any run)
    - `No clashes in latest run.` (after run with 0 clashes)

- `Classify now` / `Select all`
  - disabled when no unclassified elements

- `Review high-risk`
  - disabled when no high-risk systems

## What’s Next Banner

A contextual banner under the stepper mirrors `nextStep` and launches the same action as the step `Go` button.

Examples:

- `Next: Classify 63 elements`
- `Next: Run a clash test`
- `Next: Review 14 clashing elements`
