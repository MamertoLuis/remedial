# Proposal

## Why

The project's delivery gate requires a fully green `make audit` run, but the audit gate cannot be satisfied: there is **no Makefile (and no `audit` target)**, and the full test suite fails 12 tests. The suite only becomes runnable after initial migrations were generated (tracked in the `import-from-iaccs` change); those 12 pre-existing failures are now exposed and must be fixed so the SDD exit gate (`make audit` = 100% compliant) can actually be enforced. Two of the failures are real behavior bugs (upsert result reporting, strategy supersede), the rest are test-side defects.

## What Changes

- Fix alert view and alert API tests to authenticate correctly (they call `client.login(email=...)` which never authenticates the custom `User`, so the login-protected views return 302). Verified root cause: `client.login(email=...)` does not authenticate the `AbstractUser`-based user.
- Fix `upsert_borrower` to report accurate `created`/`updated` semantics (it currently calls `update_or_create` twice, so `created` is always `False`).
- Enable active `RemedialStrategy` save to supersede active compromise agreements for the same account (the logic exists in the model but is commented out).
- Fix compromise-agreement installment-regeneration message expectations.
- Add a `Makefile` with an `audit` target that runs the system checks and the full test suite and fails non-zero on any failure.

## Capabilities

### New Capabilities

- `account-upsert`: Accurate create/update semantics for borrower and loan-account identity upserts, so callers can rely on the returned `created` flag for reporting.
- `strategy-compromise-supersede`: Creating an active remedial strategy supersedes any active compromise agreement on the same account, keeping at most one active repayment arrangement.

### Modified Capabilities

- None. The OpenSpec specs inventory is empty; these are new capabilities.

## Impact

- `account_master/services/main.py` — `upsert_borrower` deduplicated to a single `update_or_create`.
- `account_master/models.py` — `RemedialStrategy.save` supersede block enabled; possibly add a `related_name` on `CompromiseAgreement.account` if the reverse lookup is missing.
- Tests: `account_master/tests_alert_views.py`, `account_master/tests.py` (AlertAPITests), `account_master/tests_services_core_basic.py`, `account_master/tests_models_strategy.py`, `compromise_agreement/tests.py`.
- New `Makefile` with `audit` target (system checks + full test suite).
- No new runtime dependencies. No data migration expected.