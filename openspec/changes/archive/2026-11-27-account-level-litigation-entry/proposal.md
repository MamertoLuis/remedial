# Proposal

## Why

Accounts already in litigation — long past due, legal proceedings commenced, but without any recorded escalation-ladder history — cannot be given a Legal Action or Foreclosure strategy. The entry gate (`strategy-lifecycle`) only accepts a ladder at the terminal stage or an approved agreement rescind, and no user role can steer an existing account to either. There is no data signal that the account is already in litigation, so the only source of truth is an officer telling the system so. This change lets an account officer record that fact and have it manager-approved, unblocking these accounts through a normal role flow instead of a manual database edit.

## What Changes

- Add an **account-level litigation entry**: an officer-raised, manager-approved record that an account is entering (or has entered) legal action. Set only by the officer — never derived automatically from delinquency. One active entry per account.
- Reuse the existing manager-approval machinery (`StrategyApproval`, `PENDING_APPROVAL -> APPROVED | REJECTED`, manager-only decision) so the entry carries the same audit trail as the rest of the system.
- Extend the Legal Action / Foreclosure **entry gate** in `strategy-service._check_entry_gates` to accept an **approved active litigation entry** as a valid reason — alongside the existing terminal-stage and approved-rescind hatches. Foreclosure still requires a SECURED account.
- Preserve the one-active-strategy-per-account invariant and the existing supersede behavior.

## Capabilities

### New Capabilities
- `litigation-entry`: an account-level, officer-raised, manager-approved entry to legal action, with at most one active entry per account, that feeds the Legal Action / Foreclosure strategy gate.

### Modified Capabilities
- `strategy-lifecycle`: the "Entry gates for Legal Action and Foreclosure" requirement changes to accept an approved active litigation entry as satisfying the gate (in addition to the ladder terminal stage and an approved rescind).

## Impact

- `account_master/models.py`: new `LitigationEntry` model (account FK, status, raise/approval metadata); likely a new migration.
- `account_master/management` or service layer: `litigation_entry_service` mirroring `strategy_service` approval pattern and `_require_manager`.
- `account_master/services/strategy_service.py`: `_check_entry_gates` reads approved active litigation entry.
- `account_master/views` + forms + templates: officer "raise entry" flow and manager approve/reject flow.
- `account_master/admin.py`: register the new model.
- Django admin: no change to existing role model.