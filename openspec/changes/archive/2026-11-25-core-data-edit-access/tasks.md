# Tasks

## 1. Role & Migration

- [x] 1.1 Add `SYSTEM_ADMINISTRATOR` to `users.User.Role` TextChoices — verify `uv run python manage.py makemigrations users` generates a migration and the choice renders in Django admin
- [x] 1.2 Add a data migration assigning `role = SYSTEM_ADMINISTRATOR` to existing `is_superuser` (and staff) users — verify after `uv run python manage.py migrate` the existing superuser(s) carry the new role
- [x] 1.3 Unit-test the role choices — verify a test asserts the four role values exist on `User.Role` and the default remains `ACCOUNT_OFFICER`

## 2. Shared Authorization Helper

- [x] 2.1 Implement a `system_admin_required` decorator (composing `@login_required` with a `role == User.Role.SYSTEM_ADMINISTRATOR` check) that renders the shared 403 page — verify a unit test asserts an anonymous user, a non-admin role, and a SYSTEM_ADMINISTRATOR are treated correctly
- [x] 2.2 Add the `core_data_edit_allowed` context flag (context processor or view-injected) derived from the decorator rule — verify a unit test asserts the flag is True for SYSTEM_ADMINISTRATOR and False for other roles

## 3. Gate the Fact-Plane Views

- [x] 3.1 Apply `system_admin_required` to `create_borrower`, `update_borrower`, `delete_borrower` — verify view tests: non-admin gets 403 and no write occurs; admin create/update/delete succeed (spec: "Only system administrators edit core-mirrored records through the UI")
- [x] 3.2 Apply the decorator to `create_account`, `create_account_for_borrower`, `update_account`, and the `update_account_status` endpoint — verify view tests: non-admin gets 403 with the LoanAccount unchanged; admin succeeds (spec scenario "Non-administrator is forbidden from changing account status directly")
- [x] 3.3 Apply the decorator to `create_exposure` and `update_exposure` — verify view tests: non-admin gets 403 and no Exposure is created/changed; admin succeeds (spec scenario "Non-administrator is forbidden from creating or editing an exposure")

## 4. Read-Only UI for Non-Administrators

- [x] 4.1 Wrap fact-plane create/edit/delete links in the six templates (`base.html`, `borrower_detail.html`, `account_detail.html`, `borrower_list.html`, `account_list.html`, `_account_status.html`, `partials/_context_header.html`) with the `core_data_edit_allowed` flag — verify a template/rendering test asserts non-admin list and detail pages contain none of the fact-plane edit URLs while admin pages do (spec: "Non-administrators view core-mirrored records read-only")
- [x] 4.2 Parameterize the shared 403 page message so the fact-plane gate states it requires SYSTEM_ADMINISTRATOR — verify the delinquency gate still renders its MANAGER/BOARD_MEMBER text and the fact-plane gate renders the new text

## 5. Refresh Pipeline Regression

- [x] 5.1 Add a regression test that service-layer upserts (`upsert_borrower` / `upsert_loan_account` / `upsert_exposure`) and an import command path write facts without any role — verify the test passes unchanged for non-admin execution context (spec scenario "Refresh pipeline writes are not gated")
- [x] 5.2 Run the existing `account_master` and `users` test modules — verify no existing test broke from the gating (services, imports, and detail views must still pass)

## 6. Integration Verification

- [x] 6.1 Run the full test suite (`uv run python manage.py test`) — verify all tests pass
- [x] 6.2 Run `make audit` — verify system checks and tests pass with 100% compliance

## Workflow follow-up

- Archive the change after the project's review requirements are satisfied.
- Verify the archived result.
