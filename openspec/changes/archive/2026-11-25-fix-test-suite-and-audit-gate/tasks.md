# Tasks

## 1. Alert View Tests Authentication

- [x] 1.1 Fix alert list view tests (`account_master/tests_alert_views.py`) to authenticate via `self.client.force_login(self.user)` — verify `test_alert_list_page_loads` and `test_alert_list_filtering` return 200 and pass
- [x] 1.2 Run the alert view module — verify `uv run python manage.py test account_master.tests_alert_views` is fully green

## 2. Alert API Tests Authentication

- [x] 2.1 Fix `AlertAPITests` in `account_master/tests.py` to authenticate before hitting the AJAX/alert endpoints — verify the refresh/resolve/acknowledge/dismiss/invalid-method tests pass (HTTP 400/200 as asserted)
- [x] 2.2 Run the alert API tests — verify `uv run python manage.py test account_master.tests.AlertAPITests` is fully green

## 3. Account Upsert Semantics

- [x] 3.1 Fix `upsert_borrower` (`account_master/services/main.py`) to a single `update_or_create` so `created` is accurate — verify `test_upsert_borrower_create` passes and an existing-borrower upsert returns `created == False` (spec: "Borrower upsert reports accurate result")
- [x] 3.2 Confirm and test accurate `created` for loan-account upsert — verify `test_upsert_account_create`/update coverage passes (spec: "Loan-account upsert reports accurate result")
- [x] 3.3 Run `uv run python manage.py test account_master.tests_services_core_basic` — verify green

## 4. Strategy Supersede

- [x] 4.1 Enable the supersede block in `RemedialStrategy.save` so an ACTIVE strategy sets active CompromiseAgreements for the same account (excluding its own) to `SUPERSEDED` — verify `test_save_supersedes_compromise_agreements` passes
- [x] 4.2 Add test coverage for the spec scenarios: own strategy's agreement unchanged, and no-op when no active agreement exists — verify tests pass

## 5. Compromise Regeneration Messages

- [x] 5.1 Reconcile the installment-regeneration message expectations in `compromise_agreement/tests.py` (fix test-side messages and/or `CompromiseAgreement.save` reporting, confirming `django.contrib.messages` middleware is installed) — verify both `test_installment_regeneration_*` tests pass

## 6. Audit Gate + Full Suite

- [x] 6.1 Add a `Makefile` with an `audit` target running `uv run python manage.py check` and `uv run python manage.py test` (fails non-zero on any failure/error; intentional skips allowed) — verify `make audit` exits 0
- [x] 6.2 Run the full suite (`uv run python manage.py test`) and `make audit` — verify 100% green (no failures/errors; only the `IACCS_LIVE`-gated skips remain) and record the result

## Workflow follow-up

- Archive the change after the project's review requirements are satisfied.
- Verify the archived result.