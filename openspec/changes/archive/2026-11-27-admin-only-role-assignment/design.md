# Design

## Context

See proposal.md - Why for motivation. Current state that shapes the approach:

- `users/views.py::profile` binds `UserUpdateForm` (a `UserChangeForm` exposing
  `first_name`, `last_name`, `email`, `role`) to `request.user` with only
  `@login_required`; the profile template renders every form field, so the role
  dropdown is self-service today.
- `role` **is** the application's authorization primitive: `system_admin_required`,
  `manager_required`, and the raw role checks in `delinquency.py` /
  `remedial_strategy.py` trust `request.user.role` exclusively.
- Django admin is the sole user/role management surface (README documents
  `createsuperuser` for the administrator account) and is gated by Django's own
  `is_staff` check (`AdminSite.has_permission` returns `is_active and is_staff`).
  `users/admin.py` registers a `CustomUserAdmin` with `role` in both
  fieldsets; nothing today ties `role` to `is_staff`.
- Migration `0003` seeds the SYSTEM_ADMINISTRATOR role onto existing superuser
  and staff accounts; the app is used by ~10 people with one administrator
  account (`is_staff`, usually also `is_superuser`).

## Goals / Non-Goals

**Goals:**

- Eliminate self-service role mutation with no observable change to ordinary
  profile edits (name/email).
- Make "non-admin roles are never Django admin staff" structurally enforced at
  the one place roles are managed: the `UserAdmin` form.
- Keep Django admin as the only user/role management surface.

**Non-Goals:**

- No in-app user-management page (Django admin is adequate at ~10 users).
- No changes to `is_superuser` semantics.
- No "last System Administrator" guard: self-demotion stays possible as an
  operator action and is covered by the documented convention of always keeping
  one System Administrator.
- No audit log for role changes.
- No model or migration changes.

## Decisions

**1. Fix at the form level, not the view level.**
Dropping `role` from `UserUpdateForm.fields` makes crafted POSTs carrying
`role=...` inert by construction: Django forms only process declared fields, so
no existing-view gating is needed. The template iterates `{{ form }}`, so it
renders no role control without a template change. Alternative considered:
leaving `role` in the form and gating in the view (e.g., removing
`request.user.role` on save). Rejected: it keeps role in the self-service
surface and adds a second code path to forget.

**2. Enforce the invariant in the `UserAdmin` form, not on the model.**
`is_staff == (role == SYSTEM_ADMINISTRATOR)` is enforced via a custom form
(`get_form`/`clean`/`save_model` on `CustomUserAdmin`): saving a non-admin
account with `is_staff` raises `ValidationError`; assigning or demoting the
SYSTEM_ADMINISTRATOR role syncs `is_staff` in the same save. Alternative
considered: overriding `User.save()` to sync flags. Rejected: model-level
enforcement would break `createsuperuser` (role defaults to ACCOUNT_OFFICER
while `is_staff=True`) and would constrain ORM management-command paths; the
form-level check matches the "management happens in Django admin" posture and
leaves migrations and commands untouched.

**3. Keep the default `admin.site`; no custom `AdminSite`.**
Alternative considered: an `AdminSite.has_permission` override requiring
`role == SYSTEM_ADMINISTRATOR` in addition to `is_staff`. Rejected as
redundant once the invariant holds (with it, `is_staff` already implies the
admin role) and expensive: 24 `@admin.register` registrations across three
apps would need rewiring to a custom site instance.

**4. Keep `role` visible in Django admin unchanged.**
The existing `fieldsets`/`add_fieldsets` already present the role at creation
and edit time; the change only adds validation and flag-sync, so the
operator's mental model ("role set at account creation, changed only here")
is preserved.

## Risks / Trade-offs

- **Self-demotion can orphan the admin role** (no last-admin guard).
  → Mitigation: document the convention (always keep a System Administrator)
  in the README; recovery via the shell (`manage.py shell`) if ever needed.
  A structural guard can be added later as a follow-up change.
- **Existing inconsistent accounts.** If any non-admin account already has
  `is_staff=True`, the invariant would flag it on next save.
  → Mitigation: pre-rollout audit step -- verify every `is_staff=True` account
  in Django admin has the SYSTEM_ADMINISTRATOR role; correct anomalies
  manually before the change is trusted.
- **Validation-error friction for legitimate transfers.** Moving a former
  admin to a non-admin role now requires the operator to see the role and
  `is_staff` change together; the form error message makes the required
  combination explicit.

## Migration Plan

- **Deploy:** code-only change; no schema migration. Steps: (1) audit existing
  accounts as above, (2) apply the form/validation change, (3) run the test
  suite (`make audit`).
- **Rollback:** revert the `users/forms.py` and `users/admin.py` changes; the
  profile form returns to its previous fields and admin validation is removed.
  No data needs reversing.
- **README:** document the invariant and the two account-creation paths
  (`createsuperuser` -- role seeded by migration 0003 -- or Django admin with
  role = System Administrator, which auto-sets `is_staff`).
