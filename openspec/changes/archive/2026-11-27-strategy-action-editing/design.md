# Design

## Context

See proposal.md - Why for motivation. Current state that shapes the approach:

- `StrategyAction` has `assignee`, `due_date`, `outcome`, a status machine
  (`SELECTED` -> `PENDING_APPROVAL` -> `APPROVED | REJECTED`; `SELECTED`/
  `APPROVED` -> `EXECUTED | SKIPPED`), and a `skip(outcome)` method that
  already restricts skipping to `SELECTED`/`APPROVED`.
- The strategy detail POST handler (`_handle_strategy_post` in
  `remedial_strategy.py`) dispatches `select`, `execute`, `log_execute`, and
  `fail`. `select` sets `assignee`/`due_date`; `execute` sets `outcome`. There
  is no update path and no skip UI; `skip()` is currently unreachable from the
  interface.
- The `strategy-actions` capability (synced) already carries the tracking and
  evidence requirements; this change extends the same capability with edit/lock
  and skip rules. The evidence work established the lock-on-terminal stance.

## Goals / Non-Goals

**Goals:**

- Make `assignee` and `due_date` editable while an action is in flight
  (`SELECTED`, `PENDING_APPROVAL`, `APPROVED`) and locked once terminal.
- Guarantee `outcome` is written only at execute/skip and never via an edit
  path.
- Expose skip-with-reason on non-pending, non-terminal actions.

**Non-Goals:**

- No model or schema change (migration-free).
- No change to the approval workflow or the state transitions themselves.
- No editing of a strategy's own fields (e.g. start date/type) — those remain
  outside this change.
- No history/audit trail for edits beyond `AuditableModel`'s `updated_at`
  (a full audit log is out of scope; existing audit columns are reused).

## Decisions

**1. Enforce the rules in the service and view, not the model or DB.**
No migration is needed. A service helper `update_action_planning(action,
assignee, due_date)` validates that the action is in a non-terminal status
(`EXECUTED`, `SKIPPED`, `REJECTED` are terminal and rejected) then saves the
fields. Skip reuses the model's `skip(outcome)`, which already rejects
`PENDING_APPROVAL`, `REJECTED`, `EXECUTED`, `SKIPPED` — so a thin
`skip_action` wrapper suffices. Alternatives considered: adding `clean()` or a
model method — unnecessary, since `execute`/`skip` are the only status writers
and editing is a pure-field update; keeping the constraint at the service keeps
`objects.create/update` ORM paths unconstrained (matching the evidence-link
decision).

**2. Outcome lock is structural, not a field validator.**
`outcome` is written only by `execute()` and `skip()`; the new `update`
branch accepts no outcome input, so there is no path that mutates a recorded
outcome. No extra lock code is required beyond "don't add an outcome to the
update path." This yields the spec's "no path edits a recorded outcome"
guarantee by construction.

**3. Editable vs skippable sets differ.**
- Editable (`assignee`/`due_date`): any non-terminal action —
  `SELECTED`, `PENDING_APPROVAL`, `APPROVED`.
- Skippable: `SELECTED` (non-gated) and `APPROVED` (gated) only —
  deliberately **not** `PENDING_APPROVAL`, matching "an action awaiting
  approval is not skippable" (the manager decides a pending action).
This follows `is_released_for_execution`'s already-established gating shape
(keyed off status + `requires_approval`), computed in the template and again
in the service.

**4. UI: an edit row and a skip control on the Tracked Actions table.**
For each non-terminal action the detail template renders a pre-filled
`assignee`/`due_date` form (`action = "update"`) and, when skippable, a small
skip form with a reason field (`action = "skip"`). The board read-only guard
(`_deny_board_mutations`) applies to both branches.

## Risks / Trade-offs

- **No scheduling/assignment validation** — an officer could set a `due_date`
  in the past or a free-text assignee. → Mitigation: accepted; these are
  planning fields with no domain constraints today (select already accepts
  free text), and adding validation is out of scope.
- **Skip could hide an unfinished duty** — an officer marks an item SKIPPED
  rather than executing it. → Mitigation: the reason is recorded and the
  action stays visible in the table as SKIPPED (terminal, locked); the
  evidence link lets an activity later prove the work anyway.
- **Lock relies on the single POST handler** — if a future caller writes
  `assignee`/`due_date` directly via ORM, the lock is bypassed. → Mitigation:
  the same trust assumption the rest of the framework uses (all UI writes go
  through `_handle_strategy_post`/services); acceptable at this size.

## Migration Plan

- **Deploy:** no schema migration. Ship service + view branches + template +
  tests together; run `make audit`.
- **Rollback:** revert `strategy_service.py`, `remedial_strategy.py`, and the
  template; no data repair (only planning fields and statuses were touched).

## Open Questions

None — the confirmed decisions (lock-on-terminal, edits across non-terminal
states, include skip) fully determine the change.