# Tasks

## 1. Evidence link model

- [x] 1.1 Add a nullable `action` foreign key to `CollectionActivityLog` (to `StrategyAction`, `null=True`, `blank=True`, `on_delete=SET_NULL`, `related_name="evidence_activities"`), create the schema migration, and add a model test asserting an activity can carry an action link and that deleting the strategy's account keeps the diary row (link nulled) -- verify `makemigrations --check` is clean and the migration applies on a fresh test database

## 2. Same-account rule and pure-evidence semantics

- [x] 2.1 Extend `CollectionActivityLogForm` with an optional "fulfills strategy action" field whose choices are limited to the account's ACTIVE strategy actions (SELECTED, APPROVED, EXECUTED) -- verify a test that the select offers only those actions and renders empty when the account has no ACTIVE strategy
- [x] 2.2 Enforce the same-account rule in the activity service write path (reject an action whose strategy belongs to another account or is not ACTIVE with a `ValidationError`) -- verify tests that a cross-account link and a link to an exited strategy are both rejected
- [x] 2.3 Verify pure-evidence semantics with a test: linking a collection activity to a SELECTED action leaves the action SELECTED (no auto-execution)

## 3. One-step log-and-execute convenience

- [x] 3.1 Add an atomic service path that creates the collection activity, links it to the action as evidence, and executes the action in one transaction (activity type, remarks, and outcome inputs; approval-gated actions still require APPROVED status) -- verify a test that the path produces a linked EXECUTED action with the entered outcome, and that a gated action without approval is rejected
- [x] 3.2 Wire the execute flow in `remedial_strategy` (view branch + detail template affordance) so an officer can submit the one-step path -- verify a view test that the POST creates the activity, the link, and the EXECUTED action

## 4. Integration verification

- [x] 4.1 Run `make audit` (Django checks plus the full suite) and verify AUDIT PASSED with no regressions in strategy lifecycle, approval, and escalation tests
