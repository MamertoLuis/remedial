# Tasks

## 1. Self-service profile excludes role

- [x] 1.1 Remove `role` from `UserUpdateForm` fields in `users/forms.py` and add a form test asserting the profile form exposes exactly `first_name`, `last_name`, and `email` (no role control) -- verify the new test passes
- [x] 1.2 Add a view-level regression test in `users/tests.py` asserting an authenticated loan officer POSTs `/profile/` with `role=MANAGER` and `role=SYSTEM_ADMINISTRATOR` and the account's role stays unchanged -- verify the test passes
- [x] 1.3 Add a view-level regression test asserting GET `/profile/` renders no role control in the form and the read-only Account Info panel still shows the role -- verify the test passes

## 2. Django admin role/is_staff invariant

- [x] 2.1 Enforce `is_staff == (role == SYSTEM_ADMINISTRATOR)` in `CustomUserAdmin` (`users/admin.py`) via a custom form: saving a user with a role other than SYSTEM_ADMINISTRATOR and `is_staff=True` raises a `ValidationError` and the account keeps its previous flags -- verify with an admin-client test that the save is rejected and the flags are unchanged
- [x] 2.2 Extend the admin form so assigning the SYSTEM_ADMINISTRATOR role sets `is_staff` on the same save -- verify with a test that saving a user with role SYSTEM_ADMINISTRATOR results in `is_staff=True`
- [x] 2.3 Extend the admin form so changing a SYSTEM_ADMINISTRATOR account to another role clears `is_staff` on the same save (and does not touch `is_superuser`) -- verify with a test that the demoted account has `is_staff=False`

## 3. Documentation

- [x] 3.1 Add a note to `README.md` documenting the invariant (only System Administrator accounts hold `is_staff`; other roles never access Django admin) and the two account-creation paths (`createsuperuser` with role seeded by migration 0003, or Django admin with role = System Administrator) -- verify the note exists and the commands it cites run as written

## 4. Integration verification

- [x] 4.1 Run `make audit` (Django system checks plus the full test suite) and verify a clean "100% AUDIT PASSED" result with no regressions in `account_master` role-gating tests
