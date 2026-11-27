# Proposal

## Why

`RemedialStrategy` today is a thin record — type, dates, free-text outcome — with no decision basis, no tracked execution, and no failure or escalation semantics. Choosing a strategy is supposed to rest on seven inputs (delinquency, outstanding exposure, borrower financial condition, willingness to pay, guarantor, collection history, recovery assessment), but four of them have no data model at all, and "subject to approval" actions (restructuring terms, compromise discounts, write-off, legal filing) have no approval workflow and no single accountable approver. The result: officers cannot justify *why* a strategy was chosen for an account at a given time, manager approval authority is unenforced, and escalating an account after a failed arrangement is unmodeled. The recently shipped escalation ladder (terminal stage → Legal Action / Foreclosure strategy) exposes exactly this gap: there is no framework for how a strategy is entered, executed, failed, and replaced.

## What Changes

- **Strategy assessment snapshots**: capture the seven decision inputs at decision time (with `as_of` date and officer rationale). Delinquency, exposure, and collection history are derived from existing records; financial condition, willingness to pay, guarantor, and recovery assessment get new modeled data (structured scales, not free text). The snapshot is re-captured on every escalation.
- **Sequential strategy lifecycle** (one ACTIVE per account — existing invariant preserved): the officer's recommendation becomes the ACTIVE strategy immediately (no strategy-level approval), unlocking its action menu. Strategies exit via completion conditions (per type) or via officer-declared failure; the next strategy is recommended only after the previous one exits.
- **Failure and rescind**: failure is declared by the loan officer. For agreement-carrying strategies (Compromise, Restructuring) an unsuccessful agreement opens a **rescind action**, which itself awaits manager approval; once approved, the agreement is RESCINDED and the strategy CANCELLED, and the account escalates to the next recommendation directly — the closed escalation ladder does not reopen.
- **Tracked action execution**: each strategy type gets an action catalog (template → per-strategy instances), with status, assignee, due date, and outcome. Actions that commit the bank financially, legally, or contractually are approval-gated (`requires_approval`); communication/field actions are executed and recorded directly.
- **Single-approver model**: the manager is the sole approver (board-level authority is delegated to the manager); the BOARD_MEMBER role is read-only. Approval records carry conditions (e.g., "subject to 20% downpayment within 10 days") — unmet conditions are what make an agreement "unsuccessful."
- **Entry gates**: Legal Action requires (ladder terminal reached) OR (approved rescind of an agreement); Foreclosure additionally requires a SECURED account.
- **Strategy type labels** refined to the recommended six names (Intensive Collection, Loan Restructuring/Rehabilitation, Compromise Settlement, Collateral Recovery/Foreclosure, Legal Action, Write-Off/Post-Write-off Recovery) — display-only, existing code values unchanged (non-breaking).

## Capabilities

### New Capabilities

- `strategy-assessment`: captures the decision inputs (delinquency, exposure, financial condition, willingness to pay, guarantor, collection history, recovery assessment) as a timestamped snapshot with rationale, re-captured at each escalation, and records the missing entity data (guarantor, financial condition, willingness, recovery/collateral assessment).
- `strategy-lifecycle`: governs recommendation → ACTIVE → exit (completion or failure), the one-ACTIVE-per-account sequencing, agreement rescind flow and escalation, entry gates for Legal Action / Foreclosure, and direct post-rescind escalation.
- `strategy-actions`: provides the per-strategy action catalog, tracked execution records, the approval-gated action workflow, approval records with conditions, and the manager-only / board-read-only approval authority.

### Modified Capabilities

- `notice-escalation-ladder`: adds that a ladder closed because of an approved arrangement stays closed — an approved rescind does not reopen it, and post-rescind escalation is a direct strategy recommendation (no notices).

## Impact

- **Models** (`account_master`): `RemedialStrategy` (action menu, entry gates), new `StrategyActionCatalogEntry`/`StrategyAction`, `StrategyApproval`, `StrategyAssessment`, `Guarantor`, financial-condition/willingness/recovery-assessment fields or records, recovered-asset/collection detail for Collateral Recovery; `CompromiseAgreement` gains an unsuccessful state and PENDING approval handling; `CollectionActivityLog` activity types align with the action catalog.
- **Escalation module**: close-reason handling (no reopen after rescind), Legal/Foreclosure entry-gate checks.
- **UI**: strategy detail (assessment, actions, approvals), officer action selection/execution, manager approval queue; board sees reports only (permission-gating).
- **Roles/permissions**: approval actions restricted to MANAGER; BOARD_MEMBER read-only.
- **No change** to `strategy-compromise-supersede`: the one-active invariant and agreement superseding behavior are preserved (and now also enforced by the sequential lifecycle).
- **Data**: additive only — new tables/fields; existing records remain valid; strategy type labels updated without changing stored values.
