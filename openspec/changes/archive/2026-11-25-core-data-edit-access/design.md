# Design

## Context

See `proposal.md` — Why. Core-mirrored facts (`Borrower`, `LoanAccount`, `Exposure`) are authoritative in the iAccs core and are today editable through unrestricted UI views. This change gates those UI edits to the new SYSTEM_ADMINISTRATOR role while leaving the refresh pipeline ungated.

Current state this design composes with:

- `users.User.Role` has three choices (`ACCOUNT_OFFICER`, `MANAGER`, `BOARD_MEMBER`) on a `CharField(max_length=20)`.
- The existing role-gating pattern is a per-view helper, `_is_manager_or_board_member(user)` in `account_master/views/delinquency.py`, returning a 403 via the shared `account_master/403.html` template.
- Fact-plane views to gate: Borrower (`create_borrower`, `update_borrower`, `delete_borrower`), LoanAccount (`create_account`, `create_account_for_borrower`, `update_account`, `update_account_status`), Exposure (`create_exposure`, `update_exposure`) — nine views total.
- Templates that surface edit controls for these records: `base.html` (nav dropdown), `borrower_detail.html`, `account_detail.html`, `borrower_list.html`, `account_list.html`, `_account_status.html`, and `partials/_context_header.html`.
- Writes happen through `upsert_borrower` / `upsert_loan_account` / `upsert_exposure` in the service layer, called by the UI views and by `import_from_iaccs` / the CSV import commands.

## Goals / Non-Goals

**Goals:**
- A single, shared authorization rule for "may edit core-mirrored data" (role `SYSTEM_ADMINISTRATOR`).
- All nine fact-plane views enforce it; non-admins receive a clean 403.
- Non-admin users see those records read-only (no create/edit/delete controls in templates).
- The refresh pipeline (imports + service upserts) writes facts without the role gate.

**Non-Goals:**
- No change to the judgment-plane views already gated for manager/board (`create_delinquency_status` / `update_delinquency_status`) or the uncompensated judgment views (collection activities, strategies, compromise agreements).
- No switch to the Django `groups`/`permissions` model; this change stays consistent with the project's custom `role` field. Migrating to Groups/Permissions is a separate, larger follow-up.
- No new notification/audit layer beyond what already exists (`AuditableModel` provenance).

## Decisions

### D1: Add `SYSTEM_ADMINISTRATOR` to `User.Role` and assign it to existing staff via data migration

Add the choice value `SYSTEM_ADMINISTRATOR` (18 chars) to the `Role` TextChoices; it fits the existing `max_length=20`. A data migration assigns the role to existing users who are `is_superuser` (or `is_staff`) so the operator who bootstraps the system is not locked out of fact-plane maintenance. Rollback-safe: the choice is additive.

Rationale vs. alternatives: reusing the existing custom `role` field is lowest-risk and matches how the delinquency view already gates by role. Using Django permissions would be cleaner long-term but is a broader architectural change (see Non-Goals).

### D2: One shared helper / decorator, applied to all nine views

Mirror the existing `_is_manager_or_board_member` pattern but make it a reusable `system_admin_required` decorator that composes `@login_required` and the role check, returning the existing 403 page. Apply it at the top of each of the nine fact-plane views.

Decision: authorize when `request.user.is_authenticated and request.user.role == User.Role.SYSTEM_ADMINISTRATOR`. Strictly role-based (per the spec), not `is_superuser` — the data migration in D1 ensures the bootstrap user already carries the role, so no special superuser bypass is needed and the rule stays explicit and testable.

Rationale vs. alternatives: a decorator is consistent with the function-based views and keeps the gating at the view boundary, so the service layer and import commands are automatically ungated (D5).

### D3: Hide edit controls in templates for non-admins

Wrap the create/edit/delete links for the fact-plane records in an authorization check so non-admin templates render read-only. Use a single injected flag (a tiny context processor, `core_data_edit_allowed`, derived from `request.user`) referenced by the six templates above, rather than repeating role checks inline in each template.

Rationale: one flag keeps the templates DRY and lets one unit test assert both branches; inline `{% if %}` per template would silently miss a location. This complements (not replaces) the view-level enforcement in D2 — hiding controls is UX, the decorator is the security boundary.

### D4: Update the shared 403 page copy for the fact-plane gate

The existing `403.html` currently states "Only users with MANAGER or BOARD_MEMBER role can access this feature." Add parameterized messaging so the fact-plane gate can explain it requires SYSTEM_ADMINISTRATOR, while the delinquency gate keeps its current text. Minor, but avoids a misleading uniform error.

### D5: Keep gating strictly in the view layer so the refresh pipeline is untouched

All authorization lives in the view decorator and templates; nothing changes in `services/main.py`, the importer, or the models. Because `import_from_iaccs` and the CSV commands call the service layer directly (bypassing views), they continue to write facts without the role — verified by a regression test rather than by adding a bypass flag.

## Risks / Trade-offs

- **[Bootstrap lockout]** If no user has the role, full lockout of fact-plane edits. → Mitigation: D1 data migration seeds the role onto existing superusers/staff; Django admin is the provisioning path for others.
- **[Role-check drift]** Re-introducing scattered string-compare role checks. → Mitigation: every check goes through the single `system_admin_required` decorator; templates use the single context flag.
- **[Missed template control]** An edit link stays visible to non-admins somewhere. → Mitigation: a test asserts non-admin list/detail renders contain none of the create/update/delete URLs; view-level 403 remains the real security boundary regardless.
- **[Misleading 403]** Uniform error text confuses non-admin users. → Mitigation: D4 parameterized 403 messaging.
- **[Role vs superuser divergence]** A superuser without the role is blocked. → Documented decision (strict role gate + D1 seeding); not a security defect, and matches "role governs app access."

## Migration Plan

- Schema migration: add `SYSTEM_ADMINISTRATOR` to `role` choices (CharField width unchanged).
- Data migration: set `role = SYSTEM_ADMINISTRATOR` for existing `is_superuser` users (staff on request).
- Deploy is additive: views gain a 403 for non-admins, templates hide buttons, import path unchanged. Rollback = revert the decorators/templates and the data migration; no destructive changes.

## Open Questions

- Whether a supervisor/Manager should ever override fact-plane edits in an emergency — deferred; not in this change's scope. The single decorator is the one place to relax it later.
- Whether to later formalize these gates with Django Groups/Permissions instead of the custom role — a separate follow-up, recorded as a Non-Goal here.