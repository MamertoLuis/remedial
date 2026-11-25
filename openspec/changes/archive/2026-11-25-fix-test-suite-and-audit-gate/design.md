# Design

## Context

The full suite previously could not run at all (every project app had zero migrations, so the migration graph failed). Initial migrations were generated as part of `import-from-iaccs` (task approved separately), making the suite runnable. It now runs **178 tests with 12 pre-existing failures** and there is **no Makefile**, so the SDD exit gate (`make audit` = 100% compliant) has nothing to run. See `proposal.md` — Why. The 12 failures break down as:

- Alert view + alert API tests (8) — authenticate via `client.login(email=..., password=...)`, which never authenticates the `AbstractUser`-based custom `User`, so login-protected views return 302 instead of 200/400.
- `test_upsert_borrower_create` — `upsert_borrower` calls `update_or_create` twice, so `created` is always `False` even for new rows.
- `test_save_supersedes_compromise_agreements` — the supersede logic in `RemedialStrategy.save` is commented out.
- Compromise-agreement installment-regeneration message tests (2) — expectations around the Django messages framework that need reconciling with `CompromiseAgreement.save` behavior.

## Goals / Non-Goals

**Goals:**
- Make the full test suite pass (178 tests) with only intentional skips (live DB tests gated by `IACCS_LIVE`).
- Add a `Makefile` `audit` target that runs the system checks and the full test suite and fails non-zero on any failure.

**Non-Goals:**
- Coverage thresholds, lint/typing enforcement (ruff, mypy) — not currently configured and out of scope unless requested.
- Changing the repo's `**/migrations/*.py` gitignore convention.
- Refactoring unrelated code discovered along the way.

## Decisions

### D1. Fix alert tests by authenticating properly

Use `self.client.force_login(user)` in alert view/API tests instead of `client.login(email=..., password=...)`, which cannot succeed on the custom `User`. Force-login is the correct tool for view-level tests (it exercises authorization without re-testing password hashing).

- Why: the views correctly enforce login; the defect is test-side authentication.
- Alternatives considered: fixing `client.login` arguments — fragile and depends on `USERNAME_FIELD`/backend setup; force_login is the stable option.

### D2. Fix `upsert_borrower` to a single `update_or_create`

Remove the redundant double `update_or_create` so the returned `created` flag is accurate. Behavior otherwise unchanged (same fields/defaults).

- Why: the double call is a code smell and makes every borrower import report as "updated".
- Note: `upsert_loan_account` is already a single call; the loan-account requirement is a coverage guarantee, verified by tests.

### D3. Enable `RemedialStrategy.save` supersede of compromise agreements

Fulfill the commented-out block: on saving an ACTIVE strategy, supersede active `CompromiseAgreement`s for the same account that are not linked to this strategy: `CompromiseAgreement.objects.filter(account=self.account, status=ACTIVE).exclude(strategy=self).update(status=SUPERSEDED)`.

- `CompromiseAgreement.account` already carries `related_name="compromise_agreements"` and the status enum includes ACTIVE/SUPERSEDED, so no model change is expected.
- Exact `exclude` semantics (exclude strategy vs nothing) to be confirmed against existing tests during implementation.

### D4. Reconcile compromise-agreement regeneration message tests

Investigate whether the defect is test-side (message key / middleware setup) or `CompromiseAgreement.save` reporting. Fix whichever is wrong; keep the tests asserting the intended user-facing message.

### D5. Add a `Makefile` `audit` target

Add `audit: check test` where `test` runs `uv run python manage.py test` and `check` runs `uv run python manage.py check`. A non-zero exit from either fails the audit. Intentional skips (live DB tests) are allowed; failures/errors are not.

## Risks / Trade-offs

- [Force-login bypasses password auth in tests] → acceptable: auth backend behavior is out of scope; view/enum logic is what we assert.
- [Supersede logic could affect existing accounts on first deploy] → it only changes strategy/compromise relationship rows going forward; limited blast radius; covered by tests.
- [Messages-framework tests depend on `django.contrib.messages` middleware] → verify middleware is installed before finalizing the compromise-agreement fix.
- [Adding a Makefile changes the repo toolchain surface] → minimal (`check` + `test`); the gate it provides is required by project governance.

## Migration Plan

No data migration. Deploy the code + Makefile; rerun `make audit` at the end to confirm 100% compliance. Rollback = revert the small code edits; no schema impact.

## Open Questions

- Should `make audit` also fail on unexpected skips (not just failures/errors)? Default: no — live DB tests skip by design when `IACCS_LIVE` is unset. Confirm during implementation.
- Exact `exclude` clause in the supersede query (D3) — confirm against the strategy/compromise model relationships and existing tests.