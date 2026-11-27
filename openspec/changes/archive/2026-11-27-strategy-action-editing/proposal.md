# Proposal

## Why

Strategy actions behave as a to-do checklist for a remedial strategy, but once an officer selects an action the planning fields (assigned staff, due date) are write-once: they can be set at selection time only and never adjusted while the action is in flight, and the model's skip-with-reason path has no UI. An officer cannot reassign a pending action, reschedule a missed due date, correct a typo, or close a checklist item whose plan changed — making the checklist unmanageable in practice.

## What Changes

- **Editable planning fields while in flight** Add an update path so `assignee` and `due_date` can be edited while the action is in a non-terminal status (`SELECTED`, `PENDING_APPROVAL`, `APPROVED`).
- **Lock on terminal status** Editing `assignee`/`due_date` SHALL be rejected once the action is `EXECUTED`, `SKIPPED`, or `REJECTED`. `outcome` is written only by execute or skip and SHALL NOT be editable through the editing path.
- **Skip with a reason** Expose a skip action on non-pending, non-terminal actions (`SELECTED` for non-gated; `APPROVED` for gated): recording a reason SHALL leave the action `SKIPPED`. An action awaiting approval or already terminal SHALL NOT be skippable.
- **Tests** Regression tests for the edit rules (per-state acceptance/rejection), the outcome-lock, and the skip path, plus view-level coverage.

## Capabilities

### New Capabilities

(empty)

### Modified Capabilities

- `strategy-actions`: adds the editing/locking rules for tracked actions (assignee and due date editable while non-terminal and locked once terminal; outcome written only at execute/skip) and the officer's skip-with-reason path.

## Impact

- `account_master/services/strategy_service.py` — a planning-update helper that validates non-terminal status; skip already exists on the model and is reused.
- `account_master/views/remedial_strategy.py` — `update` and `skip` branches in the strategy POST handler (alongside the existing `select`, `execute`, `log_execute`, `fail`).
- `account_master/templates/account_master/remedial_strategy_detail.html` — edit affordance (pre-filled assignee/due date) and skip control on the Tracked Actions rows.
- `account_master/tests_strategy_framework.py` — new tests for edit acceptance/rejection, outcome lock, and skip.
- No model or migration change; the lock rules are enforced in the service/view, not the database.