# Tasks

## 1. Model and migration

- [x] 1.1 Add `LitigationEntry` model to `account_master/models.py` (account FK, target strategy type, litigation start date, status `PENDING_APPROVAL | APPROVED | REJECTED`, `raised_by`/`raised_at`, `decided_by`/`decided_at`/`decision_notes`, audit fields) with a partial unique constraint for one active (`PENDING_APPROVAL | APPROVED`) entry per account, and verify `makemigrations` generates a migration and `migrate` applies it.
- [x] 1.2 Register `LitigationEntry` in `account_master/admin.py` and verify it appears in Django admin.

## 2. Litigation service

- [x] 2.1 Create `account_master/services/litigation_service.py` with `raise_litigation_entry(account, strategy_type, start_date, rationale, officer)` (only ACCOUNT_OFFICER, returns the PENDING_APPROVAL entry or raises when one is active) and `has_approved_litigation_entry(account)`; verify unit tests cover officer-only raise and the one-active-per-account rule.
- [x] 2.2 Add `approve_litigation_entry(entry, approver, notes)` / `reject_litigation_entry(entry, approver, notes)` enforcing MANAGER-only decisions; verify tests cover manager approve, manager reject allowing a re-raise, and non-manager rejection.
- [x] 2.3 Export the new service functions from `account_master/services/__init__.py` and verify imports resolve.

## 3. Strategy gate integration

- [x] 3.1 Extend `strategy_service._check_entry_gates` to accept a legal action / foreclosure when `has_approved_litigation_entry(account)` is true (keeping the SECURED branch for Foreclosure); verify a test recommends Legal Action for an account with an approved entry and no ladder, and blocks when the entry is PENDING_APPROVAL or REJECTED.
- [x] 3.2 Update the strategy-recommendation error path so a blocked recommendation surfaces the litigation-entry option; verify the message renders on the create-strategy page.

## 4. Officer UI flow

- [x] 4.1 Add an officer-facing view + form to raise a litigation entry (target type, start date, rationale) wired to a URL; verify a POST creates a PENDING_APPROVAL entry and the account detail/ladder page links to it.
- [x] 4.2 Add a template for raising an entry and verify it renders for an officer and is rejected for non-officer roles.

## 5. Manager UI flow

- [x] 5.1 Add a manager-facing view + form to approve/reject an entry with notes, restricted by manager role; verify an approve transitions to APPROVED and a reject to REJECTED.
- [x] 5.2 Add a template listing pending entries for decision and verify managers can decide and others are blocked.

## 6. Integration

- [x] 6.1 Run the full account_master test suite and `make audit` and verify all existing strategy/escalation tests still pass alongside the new litigation-entry tests.