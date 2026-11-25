# Proposal

## Why

The system's own source-of-truth principle says mirrored core facts — `Borrower` (clients), `LoanAccount`, and `Exposure` — belong to the iAccs core and should only ever be written by the refresh pipeline, never by hand in the UI. Today those record types are editable through unrestricted create/update/delete views (`create_account`, `create_borrower`, `create_exposure`, their `update_*` counterparts, `delete_borrower`, and the `update_account_status` endpoint). Any authenticated user can fabricate or alter core data, causing drift between this system and the authoritative core. The fix is to gate the UI-enabled editing of these facts to a privileged system-administrator role while keeping the refresh pipeline as the primary writer.

## What Changes

- Add a new **`SYSTEM_ADMINISTRATOR` role** to the custom `User.role` choices, so a distinct administrative persona exists for maintaining core-mirrored data (and, later, configuration).
- **Role-gate the fact-plane editing views** so only users with the `SYSTEM_ADMINISTRATOR` role can create, update, or delete `Borrower`, `LoanAccount`, and `Exposure` records through the UI:
  - Borrower: `create_borrower`, `update_borrower`, `delete_borrower`
  - LoanAccount: `create_account`, `create_account_for_borrower`, `update_account`, `update_account_status`
  - Exposure: `create_exposure`, `update_exposure`
  - Any other authenticated role requesting these actions receives a `403 Forbidden`.
- **Non-admin users see these records read-only**: detail and list views remain available to all logged-in users, but their templates no longer surface "create"/"edit"/"delete" controls for core-mirrored data.
- **The refresh pipeline is unaffected**: `import_from_iaccs`, the CSV import commands, and the service-layer upserts continue to write `Borrower` / `LoanAccount` / `Exposure` as before. Gating applies only to the user-facing views.
- Introduce a shared authorization helper (e.g., a `system_admin_required` decorator) consistent with the existing `_is_manager_or_board_member` pattern in the delinquency views, replacing ad-hoc role checks.

## Capabilities

### New Capabilities

- `core-data-edit-access`: Owns the authorization rule that only users with the SYSTEM_ADMINISTRATOR role may create, update, or delete core-mirrored records (Borrower, LoanAccount, Exposure) through the UI, while all other authenticated roles read them-only; also owns the presence of the SYSTEM_ADMINISTRATOR role on the user model.

### Modified Capabilities

- None. No existing capability requirements change (`account-upsert`, `strategy-compromise-supersede` are unaffected; gating edits no behavior those specs describe).

## Impact

- `users`: add `SYSTEM_ADMINISTRATOR` to `User.Role` choices and a migration (default admin users picked via `is_superuser`/staff continue to work; role gating is separate from Django superuser status). Django admin already allows creating a user with this role.
- `account_master`: a shared `system_admin_required` authorization helper; apply it to the nine fact-plane views listed above; update `account_master/urls.py` names only if needed (routes stay; behavior is gated); adjust templates (`account_list`, `borrower_list`, `account_detail`, `borrower_detail`, `partials/_context_header`) to hide edit controls for non-admins.
- Reflection into `compromise_agreement`, `reporting`, alerting: none. Manager/board compensation and the existing `create_delinquency_status` / `update_delinquency_status` manager gating are out of scope (judgment-plane, already gated).
- Tests: view authorization tests (403 for non-admin, success for admin) and a regression test that the refresh pipeline/service layer still writes facts unaffected.
- No new external dependencies. Django admin remains the provisioning path for the role.