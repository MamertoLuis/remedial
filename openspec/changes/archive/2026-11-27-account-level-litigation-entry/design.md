# Design

## Context

Today the Legal Action / Foreclosure recommendation gate (`strategy_service._check_entry_gates`, enforced in `create_strategy_recommendation`) passes only when `ladder_terminal_closed(account)` or `approved_rescind_exists(account)` is true. Accounts already in litigation with no ladder history can satisfy neither, and no role flow (officer issue-notice, manager approval, board read-only) can create a terminal-closed state. Motivation and behaviour are in proposal.md and the specs (`litigation-entry`, and the `strategy-lifecycle` gate delta).

The system already owns an approval pattern we can reuse: `StrategyAction` moves `PENDING_APPROVAL -> APPROVED | REJECTED`, `StrategyApproval` records the decision, and `_require_manager` restricts decisions to the MANAGER role.

## Goals / Non-Goals

**Goals:**
- Introduce an account-level `LitigationEntry` record raised by an officer and decided only by a manager.
- Satisfy the existing Legal Action / Foreclosure gate for accounts that already hold an APPROVED active entry.
- Reuse the project's established manager-approval semantics and one-open-invariant idioms.
- Preserve the one-active-strategy-per-account invariant and the existing supersede behavior.

**Non-Goals:**
- Auto-deriving litigation entry from delinquency or any other data signal.
- Creating or approving any `StrategyAction` or changing the action catalog.
- Altering the Foreclosure SECURED requirement, the terminal-stage hatch, or the approved-rescind hatch.
- Strategy-level approval for non-litigation strategy creation.

## Decisions

1. **Standalone `LitigationEntry` model, not a `StrategyAction`.** The gate runs at strategy creation, before any strategy (and therefore any action) exists; `StrategyApproval` requires a `StrategyAction` FK, so it cannot be reused directly. Keeping a dedicated model is the minimal fit.
   - Alternative: synthesize a throwaway `StrategyAction` to carry the approval — rejected as a hack that pollutes the action history.

2. **Approval state lives on the entry itself.** `LitigationEntry` carries `status` (`PENDING_APPROVAL | APPROVED | REJECTED`), `raised_by`/`raised_at`, and `decided_by`/`decided_at`/`decision_notes`, updating via a service that enforces `_require_manager` for the decision — mirroring the existing approval flow without a second record type.
   - Alternative: a parallel generic approval model for litigation — rejected as added machinery for a single case.

3. **One active entry per account via a partial unique constraint.** Mirror `EscalationState`'s `uniq_open_escalation_state_per_account` (a `UniqueConstraint` on `account` conditioned on active statuses). Active = `PENDING_APPROVAL | APPROVED`; `REJECTED` does not count, so an officer can re-raise after rejection.

4. **Gate reads a single helper.** Add `has_approved_litigation_entry(account)` (returns whether an active APPROVED entry exists) and OR it into `strategy_service._check_entry_gates`, alongside `ladder_terminal_closed` and `approved_rescind_exists`. Keep the SECURED branch for Foreclosure untouched.
   - Import note: put the query helper in the new litigation service and have `strategy_service` import it (or query `LitigationEntry` directly in `strategy_service`) with a local import where needed, following the existing `from .main import ...` cycle-avoidance style.

5. **New service module `account_master/services/litigation_service.py`** owning raise / approve / reject and the gate helper, keeping models thin — same split used by `escalation_service` and `strategy_service`.

6. **UI flow.** Officer-facing view+form to raise an entry (target type, start date, rationale); manager-facing view+form to approve/reject with notes. A small surfaced error on `create_remedial_strategy` when the gate fails now names the litigation-entry option alongside the existing reasons.

## Risks / Trade-offs

- **Cross-module import cycle** (strategy_service ↔ litigation_service) → Use a local import inside the gate helper or query the model directly in `strategy_service`, consistent with existing cycle handling.
- **Hand-editing in admin bypasses the service invariant** — `EscalationState` already accepts direct admin edits; `LitigationEntry` is registered in admin for completeness, but the one-active-per-account constraint is DB-enforced, so admin edits cannot open a second active entry.
- **Stale APPROVED entries never expire** — an approved entry is durable and manager-revocable only by a future flow; acceptable because entering litigation is a persistent state mirroring an account's real-world position. Recovery is re-raising after a reject if policy changes.

## Migration Plan

- New migration creating `LitigationEntry` (account FK, target strategy type, start date, status, raise/decision metadata, `created_by`/`updated_by` audit fields) plus the partial unique constraint for one active entry per account.
- Rollback: reverse migration drops the table; the gate simply reverts to today's behavior (terminal-stage / approved-rescind only), with no data loss beyond the entries.