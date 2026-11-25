# Tasks

## 1. Data Model & Migration

- [x] 1.1 Add `EscalationStage` model (ordered `stage_no`, `label`, `duration_days`, `is_terminal`, audit fields) in `account_master/models.py` — verify a migration is generated and `uv run python manage.py makemigrations account_master` shows the new table
- [x] 1.2 Add `EscalationState` model (FK to account + `current_stage`, `stage_started_on`, `next_notice_due`, `status` PENDING/ACTIVE/PAUSED/CLOSED, `closed_reason`, audit fields) with a unique constraint for one open state per account — verify a unit test asserts an account cannot hold two open escalation states
- [x] 1.3 Add `Notice` model (FK to account + stage, `issued_on`, `method`, `issued_by`, `reference_no`) — verify a unit test covers creation and account filtering
- [x] 1.4 Create a data migration seeding the fixed ladder stages (First Demand → Warning → Legal Intent, terminal flag, per-stage durations) — verify staging is idempotent and `uv run python manage.py migrate` seeds exactly the expected stage rows
- [x] 1.5 Register the three models in `account_master/admin.py` — verify the admin pages load without error and stage durations are editable

## 2. Escalation Service Core (judgment plane)

- [x] 2.1 Create `account_master/services/escalation_service.py` with `start_escalation(account)` that creates a PENDING state at stage 1 only when no open state exists (spec: "Each account tracks one escalation position") — verify unit tests cover first-delinquency creation and no-dup behavior
- [x] 2.2 Implement `issue_notice(account, stage, method, user)` that records a `Notice`, advances the state to the next stage, computes `next_notice_due = issued_on + duration_days`, and closes the state at the terminal stage (spec: "Issuing a notice advances the position and sets the next due date") — verify unit tests cover non-terminal advance, terminal close, and never-auto-advance
- [x] 2.3 Implement `recommend_terminal(account, strategy_type, user)` that closes the state (reason "terminal") and creates an ACTIVE `RemedialStrategy` of type Legal Action or Foreclosure through the existing strategy creation path (spec: "Escalation closes on ... terminal recommendation") — verify a unit test asserts a Legal Action strategy is created, the ladder closes, and the existing one-active-strategy invariant still holds
- [x] 2.4 Implement `close_escalation(account, reason)` with reasons "cured" / "arrangement" / "terminal" — verify a unit test asserts a closed state has the expected reason and no further notices are scheduled

## 3. Fact-Plane Hook (snapshot coupling)

- [x] 3.1 Add `sync_escalation_on_snapshot(account, derived_status)` in `escalation_service.py`, idempotent, called from the snapshot path in `services/main.py` after `_update_loan_account_status` — verify a unit test: a delinquent snapshot creates a PENDING state; a performing (cured) snapshot closes an open ACTIVE state with reason "cured"; repeat snapshots do not duplicate or wrongly transition (spec: "Escalation closes on cure")
- [x] 3.2 Confirm the mirror plane models (`LoanAccount`, `Exposure`, `DelinquencyStatus`) contain no ladder logic — verify `grep` finds no Escalation references in the mirror models and the existing snapshot tests still pass unchanged

## 4. Arrangement Hook (workflow-3 integration)

- [x] 4.1 Trigger `close_escalation(account, "arrangement")` when an account gains an approved active arrangement (an active `CompromiseAgreement`, and the restructuring arrangement equivalent per the apply-time confirmation) — verify a unit test approves a compromise agreement and asserts the ladder closes with reason "arrangement" (spec: "Escalation closes on ... arrangement approval")

## 5. Promise-to-Pay Pause (workflow-2 integration)

- [x] 5.1 Implement pending-PTP detection (most recent open promise on `CollectionActivityLog` with unresolved `promise_to_pay_date`) and `pause`/`resume` transitions — verify unit tests cover: pending promise → PAUSED; promise resolved → resumes ACTIVE at the same stage; honored promise that does not clear the delinquency leaves the stage unchanged (spec: "Ladder pauses only while a promise to pay is pending")

## 6. Alert Enforcement (due-date prompt)

- [x] 6.1 Add `RuleType.NOTICE_OVERDUE` and a `_check_notice_overdue` handler in `alert_service.py` that raises an alert for open ACTIVE states whose `next_notice_due` has passed — verify a unit test activates a rule, evaluates `check_alert_rules()`, and asserts the alert is created; and an on-time state produces none
- [x] 6.2 Verify no auto-advance: past-due `next_notice_due` produces the alert but never moves the stage — verify the test in 6.1 also asserts the stage is unchanged after evaluation (spec: "The system never advances without an officer action")

## 7. Admin & Officer UI

- [x] 7.1 Add officer-facing views: ladder detail for an account (current stage, status, next notice due, notice history) and issue-notice action — verify view tests return the ladder context and an issued notice is recorded (spec: "Issuing a notice advances the position")
- [x] 7.2 Wire the views into `account_master/urls.py` and add templates — verify a smoke test renders the ladder page and issue-notice page with the account's current state (spec: "Each account tracks one escalation position")

## 8. Integration Verification

- [x] 8.1 Run the full test suite (`uv run python manage.py test`) — verify all existing and new tests pass
- [x] 8.2 Run `make audit` — verify system checks and tests pass with 100% compliance

## Workflow follow-up

- Archive the change after the project's review requirements are satisfied.
- Verify the archived result.
