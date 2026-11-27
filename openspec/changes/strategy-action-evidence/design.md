# Design

## Context

See proposal.md - Why for motivation. Current state that shapes the approach:

- `StrategyAction` (strategy-scoped, templated, status-tracked) and
  `CollectionActivityLog` (account-scoped free-form diary) have no relationship
  today. The diary is the always-on record — it also serves accounts with no
  strategy (early delinquency) while actions exist only under an ACTIVE
  strategy.
- `StrategyAction.execute()` already takes `outcome`, `assignee`, `executed_on`;
  the execute UI currently captures only `outcome`. The activity create form
  (`CollectionActivityLogForm`) is account-scoped with no knowledge of actions.
- "Active strategy exposes only its own catalog" and the supersede rule keep at
  most one ACTIVE strategy per account, so "the account's ACTIVE strategy
  actions" is a well-defined, bounded set.
- Both models inherit `AuditableModel`, so created/updated metadata is frozen
  on write — historical links survive strategy exit untouched.

## Goals / Non-Goals

**Goals:**

- Add an optional, informational evidence link: a collection activity may cite
  the strategy action it fulfills.
- Keep the diary fully usable without a strategy (link must be nullable and
  never required).
- Provide the one-step "log activity + execute action" convenience so evidence
  and execution can be recorded together.
- Enforce the same-account / active-strategy rule at the data-integrity level.

**Non-Goals:**

- No auto-execution: linking evidence never advances the action state machine.
- No reverse link on `StrategyAction` (the diary stays the source of evidence).
- No change to approval workflow, strategy lifecycle, or the assessment
  snapshot's text summary.
- No backfill of historical activities (links apply to new records only).

## Decisions

**1. FK on the activity: `CollectionActivityLog.action = FK(StrategyAction, null=True, blank=True, on_delete=SET_NULL, related_name="evidence_activities")`.**
The diary cites the plan item it proves; one activity links to at most one
action, while many activities can evidence one action over time. `SET_NULL`
keeps the diary intact if an action is ever deleted (actions cascade-delete
with their strategy today, so this mainly guards the strategy-less diary
history). Alternatives considered: FK on the action (one evidence per action —
too rigid for repeated calls/visits) and a through-model M2M (overkill at this
size).

**2. Same-account rule enforced in the form and service, not the DB.**
A Django `CheckConstraint` cannot span tables, so the rule
(`activity.account == action.strategy.account`) is enforced where writes
happen: the activity form limits the link choices to actions of the account's
ACTIVE strategy, and the service layer raises `ValidationError` as defense in
depth. Model-level `clean()` is skipped deliberately — it would not run on
`objects.create()` paths and the service is the single write gateway for
activities and actions.

**3. Pure evidence by default; one-step convenience preserves it.**
Linking sets no status. The log-and-execute path composes existing primitives
atomically (`transaction.atomic`): it creates the activity, sets
`activity.action`, and calls `StrategyAction.execute()` in one transaction —
so the action still goes through its own state machine (including gated
actions only when approved). No new statuses or transitions are introduced.

**4. UI surface: two entry points, both minimal.**
- Activity create/edit form: an optional "fulfills strategy action" select,
  rendered only when the account has an ACTIVE strategy, populated with that
  strategy's SELECTED/APPROVED/EXECUTED actions.
- Execute flow (strategy detail): alongside the plain execute, a
  "log + execute" affordance collecting activity type/remarks plus the action
  outcome, routed to the one-step service.

## Risks / Trade-offs

- **Link selectable only while strategy is ACTIVE** — after exit, new evidence
  for old actions is impossible. → Mitigation: accepted; the spec explicitly
  keeps old links as history and the active-catalog rule is already the
  project's pattern. If needed later, a follow-up can allow links to exited
  strategies' actions.
- **Double-entry still possible** (officer logs activity normally and executes
  the action separately). → Mitigation: the one-step path reduces the common
  case to a single save; plain paths remain for officers who prefer them.
- **`SET_NULL` vs `CASCADE`** — if strategies/actions are ever hard-deleted,
  evidence links silently detach. → Mitigation: acceptable; the diary rows
  (the records of fact) must survive regardless, and links are evidence
  references, not ownership.

## Migration Plan

- **Deploy:** schema migration adding the nullable FK (`000X_...`); no data
  backfill (historical links don't exist). Ship model + service + form + view
  + template changes together; run `make audit`.
- **Rollback:** reverse the migration (drops the FK column — linked history is
  lost, diary rows remain); revert service/form/view changes. No data repair
  needed because links are additive.

## Open Questions

None — decisions above are consistent with the confirmed scope.
