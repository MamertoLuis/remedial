# Design

## Context

The system today has `RemedialStrategy` (six fixed type values, statuses ACTIVE/COMPLETED/CANCELLED, a `save()` that cancels competing ACTIVE strategies and supersedes active compromise agreements, and a partial unique constraint on one ACTIVE per account). `CompromiseAgreement` exists with its own module, statuses, and installment generation; `CollectionActivityLog` is a contact log (Call/Visit/Demand Letter/Negotiation) carrying promise-to-pay fields the ladder pauses on; `DelinquencyStatus` and `Exposure` are EVENT/MONTH_END snapshots; `EscalationStage`/`EscalationState` are a template/instance pair; `users.User` has ACCOUNT_OFFICER, MANAGER, BOARD_MEMBER roles. Motivation is in proposal.md — Why.

The design goal is a recommendation-driven, strictly sequential strategy framework: what the specs describe must map onto these existing models with additive schema changes only.

## Goals / Non-Goals

**Goals:**
- One ACTIVE strategy per account, entered by officer recommendation, exited by completion or failure → next.
- Assessment snapshots capturing all seven decision inputs, re-captured on escalation.
- Per-strategy action catalogs with tracked execution records and approval-gated actions; manager sole approver; board read-only.
- Rescind flow (agreement strategies only), direct post-rescind escalation, Legal/Foreclosure entry gates, ladder stays closed after rescind.

**Non-Goals:**
- No rules engine or system-recommended strategy — strategy choice stays officer judgment; the assessment feeds a decision-support view, not an algorithm.
- No full restructuring schedule engine (restructured terms are recorded as approved actions/outcomes; a dedicated schedule module would be a later change).
- No new report pages for the board — BOARD_MEMBER read-only access on existing pages.
- No rename of stored strategy type values — label-only display refinement.
- No change to ladder notice issuance or promise-to-pay pause mechanics.

## Decisions

### D1 — Strategy statuses unchanged; limbo lives in pending actions
Status set stays ACTIVE/COMPLETED/CANCELLED and the one-ACTIVE invariant holds. A strategy awaiting a rescind decision stays ACTIVE; the pending rescind *action* carries the limbo.
*Alternative rejected:* a PENDING_APPROVAL strategy status — would duplicate state that actions already model, and weaken "one thing at a time."

### D2 — Action catalogs as DB templates, following the ladder's template/instance pattern
`StrategyActionCatalogEntry` (strategy_type, code, name, ordering, `requires_approval`) is the reusable template; `StrategyAction` (catalog_entry, strategy, status, assignee, due_date, outcome) is the per-strategy instance. The six catalogs are seeded from the proposal's action lists via a data migration and are admin-tunable.
*Alternative rejected:* a hardcoded enum — the ladder precedent (`EscalationStage` as admin-tunable template) is already established, and the catalog is expected to grow.

### D3 — Action status machine
`SELECTED → PENDING_APPROVAL (if gated) → APPROVED | REJECTED` then `→ EXECUTED` (with outcome/assignee/date) or `SKIPPED`. Non-gated actions go `SELECTED → EXECUTED` directly. Rejection is final for that selection; the officer may select a different action or re-submit (a new approval record).

### D4 — Approvals as records with conditions
`StrategyApproval` (action, approver, decision, decided_at, comments, conditions as structured text). Gated actions are not executable until an APPROVED record exists. Enforcement: only MANAGER role may act on approvals; BOARD_MEMBER is read-only (permission checks at view/service boundary). Approval conditions are the hook the specs describe — unmet conditions, declared by the officer, mark an agreement unsuccessful.

### D5 — Assessment as a snapshot record
`StrategyAssessment` (strategy one-to-one, as_of_date, officer rationale) freezes the seven inputs. Delinquency and exposure values are *copied* from the latest `DelinquencyStatus`/`Exposure` at recommendation time (snapshot semantics — same reasoning as Exposure's EVENT snapshots, so historical justification survives later edits). Financial condition, willingness to pay, and recovery assessment are ordered-scale choices plus notes; `Guarantor` and `Collateral` become account-level entities referenced by the assessment.

### D6 — Side effects live in a strategy service, not model `save()`
The existing `save()` overrides already mix cross-entity logic and don't scale. New transitions — approval of a rescind action → agreement RESCINDED + strategy CANCELLED; approved write-off action → account WRITEOFF; approval of compromise settlement → agreement ACTIVE; officer failure declaration → agreement UNSUCCESSFUL — are orchestrated in a `strategy_service` module called from views/forms. Existing supersede behavior in `RemedialStrategy.save()` is kept as a safety net.

### D7 — New CompromiseAgreement states; agreement activation follows approval
Add `UNSUCCESSFUL` to CompromiseAgreement statuses (officer-declared, prerequisite for the rescind action). Creating a compromise under the new flow holds the agreement non-ACTIVE until its approval clears; existing ACTIVE agreements are untouched (additive migration).

### D8 — Action records are the execution log; CollectionActivityLog stays a contact log
`StrategyAction` outcome records serve as the tracked execution under a strategy (and feed the collection-history summary in later assessments). `CollectionActivityLog` remains the pre-strategy contact log (ladder notices, promise-to-pay) — its pause mechanic depends on it. The ladder's PTP flow is not altered.

### D9 — Entry gates enforced at strategy creation
Legal Action recommendation requires (ladder state CLOSED with `closed_reason` TERMINAL) OR (an approved rescind on this account's agreement). Foreclosure additionally requires `LoanAccount` SECURED. The ladder's terminal path that creates Legal/Foreclosure strategies continues to work unchanged.

## Risks / Trade-offs

- **Side-effect sprawl** (multiple approval types flipping states in different modules) → All transitions go through `strategy_service`; each approval action template carries an explicit side-effect code, so behavior is enumerable and testable.
- **Catalog drift** (30+ templates vs. the action lists in the proposal) → The seed migration is reviewed against the proposal lists as an acceptance step; catalogs are admin-editable afterwards.
- **Compromise activation change** (new flow holds agreements non-ACTIVE until approval) → Strictly additive status handling; existing ACTIVE agreements and the compromise module's installments logic are preserved.
- **Duplicate history sources** (StrategyAction vs CollectionActivityLog) → Documented separation (execution log vs contact log); the assessment summary draws from both.
- **Rescind double-path** (RESCINDED vs SUPERSEDED exits) → RESCINDED is officer-declared failure; SUPERSEDED remains the mechanism when a new ACTIVE strategy replaces stale active arrangements. Distinct close records keep the two unambiguous.

## Migration Plan

1. Additive schema: new tables (`StrategyActionCatalogEntry`, `StrategyAction`, `StrategyApproval`, `StrategyAssessment`, `Guarantor`, `Collateral`) and new status values (`CompromiseAgreement.UNSUCCESSFUL`) via migrations.
2. Seed the six action catalogs with a data migration aligned to the proposal's lists.
3. Label-only refinement of strategy type display names; stored values unchanged; no data backfill for existing strategies (assessments only exist for new recommendations).
4. Rollback: drop the new tables/status values; nothing existing is rewritten.

## Open Questions

- Whether a rejected gated action may be re-submitted by the officer or must be a fresh selection — deferrable to apply without changing specs (both satisfy "rejected is not executed").
- Whether `Guarantor`/`Collateral` should live on the account or on the assessment — account-level chosen (they persist beyond one recommendation), but the linkage shape can be finalized during apply.
