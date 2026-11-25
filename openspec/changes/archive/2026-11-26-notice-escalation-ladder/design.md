# Design

## Context

See `proposal.md` — Why. The system's recovery process has three workflows; this change models workflow 1 (notices) which is currently only a flat `CollectionActivityLog` (a "Demand Letter" is one more row). Existing constraints this design composes with:

- **Mirror/judgment split**: mirrored facts (`Borrower`, `LoanAccount`, `Exposure`, derived delinquency/status) are refreshed from the iAccs core and must not hold officer-owned process state. A snapshot only ever refreshes the mirrored account *status*.
- **Alert engine**: `AlertService.check_alert_rules()` iterates active `AlertRule`s and routes by `rule_type` to per-type checkers (`_check_collection_inactivity`, `_check_dpd_thresholds`, etc.). Alerts are surfaced through the AJAX `refresh_alerts` path.
- **Strategy invariants**: `RemedialStrategy.save()` enforces one active strategy per account and supersedes orphaned active compromises. Terminal-stage recommendation should ride this existing invariant.
- **PTP data**: `CollectionActivityLog` already carries `promise_to_pay_amount` / `promise_to_pay_date` per contact row.

## Goals / Non-Goals

**Goals:**
- A positioned, timed notice ladder owned entirely in the judgment plane.
- Officer-driven advancement: the system computes due dates and alerts but never auto-sends or auto-advances.
- A reusable per-stage duration that is tunable at runtime (matching the app's configurable alert-rule philosophy).
- Clean coupling from fact refresh ("cure", "delinquent") into the ladder without polluting mirrored models.

**Non-Goals:**
- Any scheduled/provisioned automation (no Celery, no auto-dispatch of notices). Notices are issued by humans.
- No changes to the mirror plane's schema (`Borrower`, `LoanAccount`, `Exposure`, `DelinquencyStatus`).
- No new value added to workflows 2 (contact) and 3 (agreements) beyond the interaction hooks described here.

## Decisions

### D1: Three new models, fixed template that is admin-tunable

`EscalationStage` (template): ordered `stage_no`, `label`, `duration_days`, `is_terminal`. Seeded with the fixed ladder (First Demand → Warning → Legal Intent). Model (not constants) so durations can be tuned in Django admin, consistent with the app's `AlertRule` configurability.

`EscalationState` (position, one per account): FK to `EscalationStage` (`current_stage`), `stage_started_on`, `next_notice_due`, `status` enum `PENDING|ACTIVE|PAUSED|CLOSED`, `closed_reason`, plus audit fields (`created_by`/`updated_by`).

`Notice` (history): FK to account, stage, `issued_on`, `method`, `issued_by` (User), `reference_no`.

Rationale: separates position (what stage / when next due) from history (what was actually sent), mirroring the `Exposure`/`ProvisionHistory` separation already in the codebase.

### D2: Due-date enforcement via a new alert rule type, evaluated in the existing pass

Add `RuleType.NOTICE_OVERDUE` (e.g. `NEXT_NOTICE_OVERDUE`) and a `_check_notice_overdue` handler in `AlertService`, rather than overloading `COLLECTION_INACTIVITY`. The two are semantically distinct (contact inactivity vs. an escalation notice past its due date) and a dedicated type lets a bank tune each independently. The alert is advisory — it surfaces "next notice due/overdue" but never advances the ladder.

Alternative considered: a background job attended to `next_notice_due`. Rejected — the alert pass already runs and no job queue is active; evaluation stays event/downstream-driven.

### D3: Fact-plane → ladder coupling is an explicit snapshot hook, not embedded logic

The ladder's starts/ends depend on mirrored facts (delinquency onset, cure). Rather than embedding ladder logic in `CollectionActivityLog`/`LoanAccount`/`DelinquencyStatus`, add a single explicit call site in the snapshot path (`services/main.py`, where `_auto_create_delinquency_status` → `_update_loan_account_status` runs): `sync_escalation_on_snapshot(account, derived_status)`. That function (in the new `escalation_service`) applies the ladder rules:

- delinquent + no open state → create `PENDING` at stage 1;
- performing (cured) + open ACTIVE → `CLOSED(reason="cured")`.

This keeps the mirror models free of judgment logic and makes the fact→ladder boundary visible in one place. Rationale over Django signals: explicit, readable, and audited at a known call site.

### D4: "Pending PTP" is defined from the contact log

A ladder is `PAUSED` when the account's most recent open promise-to-pay is pending, derived as: a `CollectionActivityLog` with `promise_to_pay_date` set and not yet reached (or otherwise un-settled) exists for the account. On issue/advance and on snapshot, `escalation_service` re-derives this so pause/resume follows the contact log without a separate record.

### D5: Terminal recommendation (re)uses the strategy invariants

`escalation_service.recommend_terminal(account, strategy_type, user)` closes the ladder (`CLOSED(reason="terminal")`) and creates an ACTIVE `RemedialStrategy` of type `Legal Action` or `Foreclosure` through the existing strategy creation path, so the DB constraint (one active strategy) and the supersede-orphaned-compromises rule apply unchanged. Conversely, "arrangement approved" closes the ladder through a hook triggered when an account gains an active `CompromiseAgreement`/restructuring arrangement.

### D6: All ladder logic lives in `escalation_service`

Models stay thin (fields only); transitions, due-date math, pause/resume, and close rules live in `account_master/services/escalation_service.py`. Mirrors the existing `ecl_service`/`alert_service` pattern.

## Risks / Trade-offs

- **[PTP semantic ambiguity]** "Pending PTP" needs a concrete definition; an honored promise may not clear the delinquency, so the ladder must not reset. → Mitigation: define pending narrowly (promise date set and unresolved); ladder only pauses during that window; honored/broken only recorded on the contact log and never moves the stage (per spec).
- **[Arrangement detection]** "Arrangement active" must be detectable; a restructuring may or may not produce an agreement record. → Mitigation: close trigger keys off the existence of an active arrangement record (`CompromiseAgreement`) and any restructuring-equivalent the strategy layer exposes; confirmed at apply time.
- **[Alert latency]** Overdue detection is only as fresh as the alert pass → acceptable since advancement is manual; the pass runs on officer workflow events and the refresh endpoint.
- **[Template entropy]** Governed stages that drift from the fixed ladder → seeded once; tuning is an admin act recorded by `current_stage` position, and edits only affect future due-date math.
- **[Coupling location]** Adding a hook in the snapshot path risks ordering bugs → mitigation: the hook is idempotent (only creates/transitions when the fact state actually changed) and safe to call on repeat snapshots.

## Migration Plan

- Add three tables (`EscalationStage`, `EscalationState`, `Notice`) via a standard Django migration. No existing table changed; the mirror plane is untouched.
- Seed the ladder template (`EscalationStage` rows) in a data migration.
- Deploy is additive: nothing existing reads the new tables, so rollback = drop the three tables and revert the new service/hook code. No destructive or breaking changes.

## Open Questions

- Exact stage labels and durations for the ladder (First Demand → Warning → Legal Intent) — tunable later via admin, safe to defer.
- Which restructuring state counts as an "active arrangement" for close-on-arrangement — a `CompromiseAgreement` is unambiguous; the restructuring equivalent is confirmed during apply without changing specs or approach.