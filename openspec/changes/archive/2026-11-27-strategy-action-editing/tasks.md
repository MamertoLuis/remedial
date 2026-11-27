# Tasks

## 1. Action planning edits and outcome lock

- [x] 1.1 Add `strategy_service.update_action_planning(action, assignee, due_date, officer)` that rejects a terminal status (EXECUTED, SKIPPED, REJECTED) and saves the editable fields otherwise -- verify tests that edits succeed for SELECTED, PENDING_APPROVAL, and APPROVED actions, and are rejected with the fields unchanged for EXECUTED, SKIPPED, and REJECTED actions
- [x] 1.2 Add a thin `strategy_service.skip_action(action, outcome, officer)` wrapper over the model's `skip(outcome)` -- verify tests that a SELECTED non-gated action and an APPROVED gated action skip to SKIPPED with the reason, and that PENDING_APPROVAL, REJECTED, EXECUTED, and already-SKIPPED actions are rejected
- [x] 1.3 Verify outcome-lock semantics with a test: the planning-update path accepts no outcome, and an EXECUTED action's recorded outcome is unchanged after any update attempt

## 2. View and template wiring

- [x] 2.1 Add `update` and `skip` branches to `_handle_strategy_post` in `remedial_strategy.py`, each guarded by `_deny_board_mutations` -- verify a view test that an officer POST updates assignee/due date, a skip POST records SKIPPED with a reason, and a board-member POST is rejected
- [x] 2.2 Add an edit affordance (pre-filled assignee/due date) and a skip-with-reason control to the Tracked Actions table, shown only for eligible non-terminal actions -- verify the template renders these only for non-terminal statuses

## 3. Integration verification

- [x] 3.1 Run `make audit` (Django checks plus the full suite) and verify AUDIT PASSED with no regressions in strategy lifecycle, approval, evidence, and escalation tests