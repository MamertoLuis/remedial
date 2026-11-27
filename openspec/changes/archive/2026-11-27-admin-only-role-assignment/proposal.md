# Proposal

## Why

Every authenticated user can currently change their own role through the
self-service profile page: `UserUpdateForm` exposes the `role` field and the
profile view binds it to `request.user` with no gating. Because the
application authorizes its views on `request.user.role` alone, any user --
including a loan officer -- can unilaterally elevate themselves to Manager or
even System Administrator. Role assignment is a governance action, not profile
data: roles are assigned once at account creation and only the System
Administrator may change them, and non-admin roles must never hold Django
admin access.

## What Changes

- **BREAKING (behavior)** Remove `role` from the self-service profile form
  (`UserUpdateForm`), so profile updates cover only `first_name`, `last_name`,
  and `email`. Undeclared POST fields are ignored by Django forms, so a crafted
  request carrying `role=...` is silently rejected with no escalation path.
- **Django admin invariant** Enforce `is_staff == (role ==
  SYSTEM_ADMINISTRATOR)` in the `UserAdmin` form: saving a non-admin account
  with `is_staff=True` raises a validation error, assigning the System
  Administrator role auto-sets `is_staff`, and demoting an admin clears it.
  This makes "non-admin roles cannot access Django admin" structurally true at
  the single place roles are managed.
- **Tests** Regression coverage: profile form exposes no role field; crafted
  role-changing POSTs leave the role unchanged; the admin UI refuses
  inconsistent role/is_staff combinations; admin creation auto-sets `is_staff`.
- **Documentation** A README note stating the invariant so operators creating
  accounts through Django admin follow it (Administrator accounts are
  `is_staff`, usually `is_superuser`; all other roles are never staff).

## Capabilities

### New Capabilities

- `self-service-profile`: The user account editing surface -- what a user may
  change about their own account (name/email only, never role) and how roles
  and Django admin access are governed (roles assigned at account creation,
  changed only by the System Administrator through Django admin, non-admin
  roles never staff).

### Modified Capabilities

(empty)

## Impact

- `users/forms.py` -- drop `role` from `UserUpdateForm` fields.
- `users/admin.py` -- role/is_staff invariant enforced in the `UserAdmin` form.
- `users/tests.py` -- regression tests for profile and admin-form behavior.
- `README.md` -- document the invariant and the intended account-creation flow.
- No model or migration changes; the `role` field and the four role choices are
  unchanged. Existing role-gated views (`system_admin_required`,
  `manager_required`, delinquency/strategy checks) are unaffected, as is the
  `core-data-edit-access` capability.
