# Design

## Context

Current state that shapes the approach (see proposal.md — Why for motivation):

- **Stack today**: Django 6.0, allauth, django-tables2 (list pages `{% render_table %}`), django-filter (borrower list), crispy-forms (auth + some forms), HTMX 1.9 (CDN + `django-htmx` installed, minimal usage today), Bootswatch United/Bootstrap 5.3 via CDN, custom `bank-theme.css` + `layout.css`, Bootstrap Icons via CDN, `data-bs-theme` dark mode with `localStorage('theme')` and an inline pre-paint script. No Tailwind, no Node toolchain.
- **Base layout** exposes blocks actually used by children: `title`, `content`, `breadcrumbs`, `context_header`, `extra_css`, `extra_js`. The right-column `{% block sidebar %}` is used only by base itself. `reporting/base_report.html` defines `{% block extra_head %}` + print stylesheet that base.html does not declare — that block is silently dropped today (existing finding to fix by adding an `extra_head` block).
- **Routing** (Phase 0 inventory — full table is an implementation deliverable in repo-root `DESIGN.md`): dashboard + portfolio summary; accounts (list, detail, create, update, status update); borrowers (list with filter, detail, create, update, delete); collection activities (list, create, update); exposures (create, update); delinquency statuses (create, update); remedial strategies (create, update, detail); escalation ladder (detail) + issue notice (form); search results; alerts list (Paginator, 20/page) + JSON APIs; compromise agreements (list via ListView without pagination — finding, no pagination to add; detail, create, update, installment forms, mark-installment-paid, term-sheet PDF); reporting (index + 5 report pages, no charts today — finding); profile; allauth pages (login, signup, logout, password reset ×2). `403.html` exists; `404.html`/`500.html` do not (finding — will be created presentation-only).
- **Dashboards**: current dashboard renders KPI cards, alerts summary widget, ops KPIs, activity timeline. There is **no needs-attention dataset** today — the redesigned dashboard requires a new read-only annotated query (see Decisions).
- **Messages**: views already emit `messages.*` but no template renders them (finding — toasts to be added).
- **Status-changing actions** to give confirm modals: `delete_borrower`, `update_account_status` (POST, cycles status), `mark_installment_paid` (POST, HTMX), alert acknowledge/resolve/dismiss APIs (POST).

## Goals / Non-Goals

**Goals:**
- One token system + component set reused by all page types; consistent triage-first dashboard; HTMX table swaps without touching view logic; dark mode without flash; WCAG AA.
- Keep every URL name, view, context variable, form/query parameter, and export endpoint working unchanged.

**Non-Goals:**
- Not changing business logic, models, calculations, permissions, or queries other than the single read-only needs-attention dataset the dashboard template strictly requires.
- Not adding new filters, columns, features, or pagination where the current views have none (compromise list stays unpaginated).
- Not removing any existing table column users rely on; not touching unused scratch templates (`dashboard_*.html`, `pasdue_aging_summary.html`).

## Decisions

### D1. Tailwind via the standalone CLI — no Node/frontend build framework
Use Tailwind **v4 standalone CLI** (single binary, npm-free, pinned `v4.3.5`) driven through `make css`: `tailwindcss -i account_master/static/css/input.css -o account_master/static/css/app.css --minify` with content globs scanning `*/templates/**/*.html`. Compiled `app.css` is COMMITTED (account_master/static is tracked), so deployments/containers need no build step; the Docker image can add `RUN make css` where network exists (repo currently has no Dockerfile — finding). Dark mode with `class` strategy via `@custom-variant dark` in v4.
- *Alternatives*: Play CDN — rejected (network dependency, not suitable for a bank/intranet deployment, no reliable production build); Node + PostCSS — rejected (introduces a Node toolchain, violating the "no new frontend build framework" constraint).
- *Why*: no runtime CDN dependency (current Bootstrap/Bootswatch links are removed), fits uv/Docker project, and keeps the pipeline one compile step.

### D2. Icon set — Heroicons outline, inline SVG sprite
Replace Bootstrap Icons CDN with **Heroicons (outline)** bundled as a small collection of inline SVG snippets (one include partial per icon or a single sprite partial). No runtime library download.
- *Alternatives*: Lucide — equally acceptable; chose Heroicons for outline weight and simple SVG partials. Rule: one set only; no new runtime dependency.
- *Why*: works offline/intranet, tree-shaken by construction, `aria-hidden` + `aria-label` on icon-only buttons is explicit in the partials.

### D3. Tokens — single source in `input.css`
Define `@theme` tokens in `account_master/static/css/input.css`: `--color-brand-*` (maroon derived from existing brand — **assumption: maroon ≈ `#7A1F2B` scale; confirm against the reference screenshot in Phase 0 of apply**), `--color-surface`/`--color-ink` neutral slate scales, semantic `--color-critical` (red), `--color-watch` (amber), `--color-ok` (emerald). All utilities derive from these; semantic colors appear only for meaning. A `grep`-based check task enforces "no color utility without `dark:` variant".

### D4. Status → chip mapping in exactly one place
New template-tag module (`ui_tags.py`) exposing `status_chip_class <value>` (returns Tailwind pill classes) backed by a single dict mapping: loan status (PERFORMING→ok, PAST_DUE→watch, NPL/SECURED_NPL→critical, WRITEOFF/CLOSED→neutral), classification (current/EM/substandard/doubtful/loss), alert type (CRITICAL→critical, WARNING→watch, INFO→neutral, SUCCESS→ok), agreement status, installment status (PAID→ok, OVERDUE→critical, PENDING→watch). Chips always include the text label.
- *Why*: removes the scattered ad-hoc `badge bg-*` classes currently duplicated across templates.

### D5. Money/number formatting — one template filter library
New `ui_filters.py`: `peso` (₱ 1,234,567.89), `peso_compact` (₱53.7M — full value in `title`), plus a `tabular` class constant; all values rendered with `tabular-nums`. KPI tiles use `peso_compact`; tables/details use `peso`.
- *Why*: current templates mix `floatformat` with manual ₱ and no tabular figures; one filter guarantees consistent output per the spec.

### D6. `data_table` wraps django-tables2 — do not replace it
All django-tables2 pages keep their `Table` classes and `RequestConfig` (ordering + pagination stay view-side). The shared `data_table.html` partial accepts the table object and renders chrome: sticky header wrapper, `<th scope="col">`, `aria-sort` on the active sort column (from `table.order_by`), row hover, severity row highlight (a per-table `row_class` callable), an empty-state slot, and the pagination partial. Table styling is applied by adding Tailwind attrs to each `Table.Meta.attrs` (one edit per table file) rather than restyling the whole library.
- *Alternatives*: hand-written tables per page — rejected (would duplicate ordering/pagination/filter wiring and risk breaking param contracts).
- **Collapse rule**: a `collapse_columns` list on the partial hides secondary columns below 1280px and renders them in a `<details>` row expansion (definition list). Only columns designated least important per page; no column is removed at ≥1280px.

### D7. HTMX without view changes
Filter forms and pagination links get `hx-get`, `hx-target="#table-container"`, `hx-push-url="true"`, `hx-select="#table-container"`, plus a shared `hx-indicator`. Every list template wraps its table in `<div id="table-container">`. Because `hx-select` extracts the container from a normal full-page response, existing views keep working with zero view edits, and the same URL renders a full page without JavaScript. django-tables2 sort links (plain `<a href>`) get `hx-get` attributes added via the data_table layer so sorting also swaps in place.

### D8. Shell restructure keeps child blocks intact
`base.html` becomes: left sidebar (nav + alerts count badge) + main column (top bar: title, as-of timestamp, global search with **unchanged** `q` field/action, theme toggle, user menu) + `{% block content %}` + right `{% block sidebar %}` kept for compat. Preserve `breadcrumbs`/`context_header` blocks. Add an `extra_head` block so `reporting/base_report.html`'s print CSS actually loads (fixes the current silent-drop finding). Alerts badge count comes from a new lightweight context processor (pattern: existing `core_data_edit_allowed`) exposing `alert_counts` for authenticated users; unauthenticated stays `0`.
- Auth pages (login/signup/logout/reset) and error pages render through a minimal shell variant (no sidebar/top bar), keeping the centered-card pattern.

### D9. Needs-attention dataset (the only query addition)
Add `DashboardService.get_needs_attention(limit=20)`: a read-only query annotating accounts with latest-exposure outstanding balance and days past due (`latest_exposure` subquery already used by `account_list`), ordered by days past due descending, limited to 20, with status chip + strategy + officer fields pulled from existing relations. This mirrors existing patterns (`get_total_past_due_loans`), changes no existing query or KPI calculation, and is strictly required for the new dashboard table per the task boundary ("unless a template change strictly requires it").

### D10. Messages → toasts; destructive actions → confirm modal
New `toast_container.html` partial rendered once in base top-right: success auto-dismisses, errors persist (both themes). New `confirm_modal.html` partial (focus trap, Escape to close, `aria-modal`) used by delete-borrower (from list/detail), account status update, mark-installment-paid, and alert ack/resolve/dismiss — all POSTing to the same URLs with the same parameters; the existing `delete_borrower.html` page remains as a no-JS fallback.

### D11. Error/auth pages
Add `templates/404.html` and `templates/500.html` under `remedial/templates/` (BASE_DIR = the inner Django package dir; the `templates` DIRS entry points there — the directory does not exist yet and is created by the auth/error task group), `500.html` inheriting a shell variant that cannot fail on missing context (per task constraint). Restyle `403.html`; logout follows the form-page pattern (already restyled earlier this session, will be migrated to the new system).

### D12. Reporting
KPIs via `kpi_tile`, tables via `data_table`, Print/export actions unchanged. No charts exist (finding) — Chart.js/token-color requirements are conditional and skipped; if inline SVG appears in any report page, it must read tokens.

## Risks / Trade-offs

- **Tailwind v4 vs v3 syntax** → Pin the CLI version in the Makefile/uv and use v4 customs (`@custom-variant dark`); a wrong assumption fails loudly at build time (fast feedback), and the compiled CSS diff is reviewable.
- **django-tables2 styling via `attrs`** → Table configs are numerous; missing attribute updates show as unstyled tables. Mitigation: one checklist task per list page in `tasks.md`, verify each page renders styled before moving on.
- **HTMX swap vs full page divergence** → `hx-select` mitigates, but if a view later renders different content for AJAX requests this breaks. Mitigation: pages keep serving full HTML; partials are only used for the alert APIs already in place.
- **Needs-attention query performance** → Same annotated-subquery pattern account_list already uses; limit to 20 rows. Mitigation: keep `limit=20`, add index note if profiling shows issues (out of scope to change schema).
- **Maroon brand assumption** → If the actual maroon differs, it's a token/`input.css` one-line change after confirmation.
- **Removing Bootstrap/Bootswatch** → Any stray Bootstrap class in a template renders unstyled. Mitigation: the apply order restyles each page (dashboard → list → detail → form → report/auth/error) and verifies each load before the next, with the CSS gap grep from the spec.

## Migration Plan

1. Phase 1 shell + tokens land first, keeping the old CSS for unstyled pages (new layout renders every page — base must not crash any template).
2. Restyle pages in the task-specified order; run `docker compose up` and load each route after each step; run the existing test suite after each milestone (Makefile `make audit` gate).
3. Remove Bootstrap/Bootswatch/bank-theme/style CSS and leftover CDN links only after every page is migrated.
4. Rollback: revert to the previous commit — templates and static CSS are the only surface, no schema/migration impact.

## Open Questions

- Confirm the exact maroon brand values against the reference screenshot during Phase 0 of apply (token change only, does not alter spec or approach).
- Confirm default sort for the attention queue (days past due descending is specified; order is already fixed — no further ambiguity).
- Alert badge count source of truth: existing `alert_counts` context from `AlertService.get_alert_counts` reused as-is by the new context processor.
