# Remedial System — UI Workspace Design System

> Part of the `ui-workspace-makeover` change. This file is the live design record
> for the presentation layer: page inventory, tokens, shared components, HTMX
> conventions, and status→chip mapping. Update it alongside template changes.

## 1. Page inventory (Phase 0)

Every route from every `urls.py`, its view, its template, and its page-type
classification per the change spec. "HTMX" = the page template already uses
`hx-*` attributes or HTMX-driven swaps today; "Pagination" = the view already
paginates (page size noted).

### account_master/urls.py

| URL name | View | Template | Page type | HTMX | Pagination | Destructive action |
|---|---|---|---|---|---|---|
| `dashboard` | `views.dashboard` | `account_master/dashboard.html` | Dashboard | alert polling (fetch/JSON) | — | — |
| `portfolio_summary` | `views.portfolio_summary` | `account_master/portfolio_summary.html` | Report | — | — | — |
| `account_list` | `views.account_list` | `account_master/account_list.html` | List | — | yes (25, tables2) | — |
| `create_account` | `views.create_account` | `account_master/create_account.html` | Form | — | — | — |
| `create_account_for_borrower` | `views.create_account` | `account_master/create_account.html` | Form | — | — | — |
| `account_detail` | `views.account_detail` | `account_master/account_detail.html` | Detail | `_account_status` partial | related tables (25) | status change, ECL generate |
| `update_account` | `views.update_account` | `account_master/update_account.html` | Form | — | — | — |
| `update_account_status` | `views.update_account_status` | `account_master/_account_status.html` (partial) | Action (POST, cycles status) | yes (partial swap) | — | status change |
| `borrower_list` | `views.borrower_list` | `account_master/borrower_list.html` | List (django-filter) | — | yes (25, tables2) | — |
| `create_borrower` | `views.create_borrower` | `account_master/create_borrower.html` | Form | — | — | — |
| `borrower_detail` | `views.borrower_detail` | `account_master/borrower_detail.html` | Detail | — | accounts table (25) | delete via confirm |
| `update_borrower` | `views.update_borrower` | `account_master/update_borrower.html` | Form | — | — | — |
| `delete_borrower` | `views.delete_borrower` | `account_master/delete_borrower.html` | Confirm/Form | — | — | **delete borrower** |
| `collection_activity_list` | `views.collection_activity_list` | `account_master/collection_activity_list.html` | List | — | yes (25, tables2) | — |
| `create_collection_activity` | `views.create_collection_activity` | `account_master/create_collection_activity.html` | Form | — | — | — |
| `update_collection_activity` | `views.update_collection_activity` | `account_master/update_collection_activity.html` | Form | — | — | — |
| `create_exposure` | `views.create_exposure` | `account_master/create_exposure.html` | Form | — | — | — |
| `update_exposure` | `views.update_exposure` | `account_master/update_exposure.html` | Form | — | — | — |
| `create_delinquency_status` | `views.create_delinquency_status` | `account_master/create_delinquency_status.html` | Form | — | — | — |
| `update_delinquency_status` | `views.update_delinquency_status` | `account_master/update_delinquency_status.html` | Form | — | — | — |
| `create_remedial_strategy` | `views.create_remedial_strategy` | `account_master/create_remedial_strategy.html` | Form | — | — | — |
| `update_remedial_strategy` | `views.update_remedial_strategy` | `account_master/update_remedial_strategy.html` | Form | — | — | — |
| `remedial_strategy_detail` | `views.remedial_strategy_detail` | `account_master/remedial_strategy_detail.html` | Detail | — | — | — |
| `search` | `views.search` | `search/search_results.html` | List | — | — | — |
| `alert_list` | `alert_list.alert_list` | `account_master/alert_list.html` | List | — | yes (20, Paginator) | ack/resolve/dismiss |
| `api_refresh_alerts` | `alerts_api.refresh_alerts` | JSON API | API | yes | — | — |
| `api_acknowledge_alert` / `api_resolve_alert` / `api_dismiss_alert` | `alerts_api.*` | JSON API | API | yes | — | status-changing |
| `api_get_alert_detail` | `alerts_api.get_alert_detail` | JSON API | API | yes | — | — |
| `api_create_alert_rule` | `alerts_api.create_alert_rule` | JSON API | API | — | — | — |
| `api_bulk_acknowledge` / `api_bulk_resolve` / `api_bulk_dismiss` | `alerts_api.bulk_alert_action` | JSON API | API | yes | — | status-changing |
| `generate_ecl_provision` | `views.generate_ecl_provision` | JSON response | Action (POST) | yes | — | writes ECL row |
| `escalation_ladder_detail` | `views.escalation_ladder_detail` | `account_master/escalation_ladder.html` | Detail | — | — | — |
| `issue_escalation_notice` | `views.issue_escalation_notice` | `account_master/issue_notice.html` | Form | — | — | creates notice |

### compromise_agreement/urls.py

| URL name | View | Template | Page type | HTMX | Pagination | Destructive action |
|---|---|---|---|---|---|---|
| `compromise_agreement_list` | `CompromiseAgreementListView` | `compromise_agreement/compromise_agreement_list.html` | List (tables2) | — | **no** (finding — do not add) | — |
| `compromise_agreement_detail` | `CompromiseAgreementDetailView` | `compromise_agreement/compromise_agreement_detail.html` | Detail | — | — | — |
| `compromise_agreement_create` | `CompromiseAgreementCreateView` | `compromise_agreement/compromise_agreement_form.html` | Form | — | — | — |
| `compromise_agreement_update` | `CompromiseAgreementUpdateView` | `compromise_agreement/compromise_agreement_form.html` | Form | — | — | — |
| `compromise_installment_create` | `CompromiseInstallmentCreateView` | `compromise_agreement/compromise_installment_form.html` | Form | — | — | — |
| `compromise_installment_update` | `CompromiseInstallmentUpdateView` | `compromise_agreement/compromise_installment_form.html` | Form | — | — | — |
| `mark_installment_paid` | `mark_installment_paid` | `compromise_agreement/_installment_row.html` (partial) | Action (POST, HTMX) | yes | — | status-changing |
| `generate_term_sheet_pdf` | `generate_term_sheet_pdf` | PDF export | Export | — | — | — |

### reporting/urls.py (namespaced `reporting:`)

| URL name | View | Template | Page type | HTMX | Pagination | Destructive action |
|---|---|---|---|---|---|---|
| `reports_index` | `views.reports_index` | `reporting/reports_index.html` | List (report links) | — | — | — |
| `loan_portfolio_breakdown` | `views.loan_portfolio_breakdown` | `reporting/loan_portfolio_breakdown.html` | Report | — | — | — |
| `past_due_aging_summary` | `views.past_due_aging_summary` | `reporting/past_due_aging_summary.html` | Report | — | — | — |
| `npl_portfolio_analysis` | `views.npl_portfolio_analysis` | `reporting/npl_portfolio_analysis.html` | Report | — | — | — |
| `top_20_npl_accounts` | `views.top_20_npl_accounts` | `reporting/top_20_npl_accounts.html` | Report | — | — | — |
| `loan_officer_performance_summary` | `views.loan_officer_performance_summary` | `reporting/loan_officer_performance_summary.html` | Report | — | — | — |

### remedial/urls.py (root) + others

| URL name | View | Template | Page type | HTMX | Pagination | Destructive action |
|---|---|---|---|---|---|---|
| `profile` | `users.views.profile` | `users/profile.html` | Form | — | — | — |
| `admin/` | Django admin | admin | Admin (not restyled) | — | — | — |
| allauth `account_login` | allauth | `account/login.html` | Auth | — | — | — |
| allauth `account_logout` | allauth | `account/logout.html` | Auth/Form (confirm) | — | — | ends session |
| allauth `account_signup` | allauth | `account/signup.html` | Auth | — | — | — |
| allauth `account_reset_password` | allauth | `account/password_reset.html` | Auth | — | — | — |
| allauth `account_reset_password_from_key` | allauth | `account/password_reset_from_key.html` | Auth | — | — | — |
| error 403 | — | `account_master/403.html` | Error | — | — | — |
| error 404 | — | **missing → create** `remedial/templates/404.html` | Error | — | — | — |
| error 500 | — | **missing → create** `remedial/templates/500.html` | Error | — | — | — |

### Findings

1. **404/500 templates do not exist** — they will be created presentation-only; 500 must not depend on context processors that can fail.
2. **No charts** in any report page — the conditional chart requirements are skipped; no Chart.js anywhere.
3. **`compromise_agreement_list` has no pagination** — not added; keep the view as-is.
4. **Scratch/unused templates**: `dashboard_base_test.html`, `dashboard_clean.html`, `dashboard_final_test.html`, `dashboard_isolated.html`, `dashboard_minimal*.html`, `dashboard_no_load.html`, `dashboard_params_test.html`, `dashboard_raw.html`, `dashboard_simple.html`, `dashboard_single_line.html`, `dashboard_test_include.html`, `reporting/pasdue_aging_summary.html` (typo duplicate) — unused, **left untouched**.
5. **`reporting/base_report.html` `{% block extra_head %}` is silently dropped** today because `base.html` has no such block — the shell adds an `extra_head` block so the print stylesheet loads.
6. **Django messages are emitted but never rendered** anywhere — a `toast_container` partial is added in the shell.
7. **`remedial/templates/` does not exist yet** — `STATICFILES`/`TEMPLATES.DIRS` already points there; created by the error-page task.

## 2. Color tokens

Defined once in `account_master/static/css/input.css` (`@theme`). All utility classes derive from
these; semantic colors appear only when their meaning applies.

| Token | Hex (light) | Use |
|---|---|---|
| `brand-600` | `#7A1F2B` (maroon) | Active nav, primary buttons, focus rings, links |
| `brand-700` / `brand-50`…`brand-900` | scale around `#7A1F2B` | Hover states, tinted backgrounds |
| `surface` (light) | `slate-50` `#f8fafc` | Page background |
| `surface-dark` | `slate-950` `#020617` | Page background (dark) |
| `card` (light) | white `#ffffff` | Card/tile background |
| `card-dark` | `slate-900` `#0f172a` | Card/tile background (dark) |
| `ink` (light) | `slate-900` `#0f172a` | Primary text |
| `ink-dark` | `slate-100` `#f1f5f9` | Primary text (dark) |
| `muted` | `slate-500` `#64748b` | Secondary/help text |
| `critical` | red `#dc2626` (light) / `#f87171` (dark) | NPL, overdue, errors, critical alerts |
| `watch` | amber `#d97706` (light) / `#fbbf24` (dark) | Past due, warnings, watch states |
| `ok` | emerald `#059669` (light) / `#34d399` (dark) | Performing, resolved, success |
| `neutral` | slate `#64748b` | Closed/write-off/no-data states |

> Maroon is a baseline assumption pending confirmation against the reference
> screenshot (task 1.2) — change is a one-line token update.

## 3. Shared component partials

Location: `templates/partials/` (account_master) + tag libraries
`account_master/templatetags/ui_tags.py` (status chip classes, `query_url`,
`row_cell`, `capture`) and `ui_filters.py` (`peso`, `peso_compact`).

**HTMX conventions**: every list page wraps its table in
`<div id="table-container">`; filters and pagination use `hx-get`,
`hx-target="#table-container"`, `hx-push-url="true"`,
`hx-select="#table-container"`; the shared `hx-indicator` overlay is part of
`data_table.html`. Views are untouched — `hx-select` extracts the container
from a normal full-page response, so URLs work with and without JS.

| Partial | Context variables | Behavior |
|---|---|---|
| `page_header.html` | `page_title`, `page_subtitle` (opt), `record_count` (opt int), `primary_action` (opt dict: url+label) | Title row with count and action slot |
| `kpi_tile.html` | `label`, `value`, `subtext` (opt), `delta` (opt), `severity` (opt: critical/watch/ok/neutral), `url` (opt — whole tile links), `is_money` (opt bool) | KPI value with full `title` tooltip; money abbreviated via `peso_compact` |
| `status_chip.html` | `value` (raw status value), `label` (opt override), `title` (opt) | Pill chip via `status_chip_class` tag; text label always shown |
| `data_table.html` | `table` (django-tables2) or None, `table_id` (opt, default `table-container`), `empty_title/empty_message/empty_url/empty_label` (opt) | Wrapper + hx-indicator + empty slot; column collapse driven by `table.collapse_columns` (class attr on Table subclasses) |
| `pagination.html` | `page_obj` (Django page), `hx_target` (opt string) | Prev/next + numbers; preserves all GET params except `page` via `query_url` tag; HTMX attrs when `hx_target` set |
| `filter_bar.html` | `filter_fields` (safe HTML — build with `{% capture as filter_fields %}`), `clear_url`, `hx_target` (opt) | Horizontal filter row with Clear; form `hx-get` to `request.path` |
| `empty_state.html` | `title` (opt), `message` (opt), `action_url` (opt), `action_label` (opt) | Short message + optional single action, no illustrations |
| `confirm_modal.html` | `modal_id`, `title`, `message`, `form_action`, `extra_fields` (opt safe HTML), `confirm_label` (opt), `confirm_class` (opt) | Focus trap, Escape closes, posts to the same URL/params; open via `data-modal-open="{{ modal_id }}"` |
| `toast_container.html` | — (uses `messages`) | Top-right toasts inside `#toast-container`; success auto-dismiss (5s), errors persist; both themes |
| `icon.html` | `name` (heroicon slug), `class` (opt) | Heroicons outline inline SVG, `aria-hidden="true"` |

**django-tables2 override** (`templates/django_tables2/table.html`, app-level):
adds `class="app-table"` (tables no longer carry `table table-striped`),
`<th scope="col">`, `aria-sort` on the active sort column, HTMX sort links,
`<details>` row expansion for `table.collapse_columns`, styled empty text, and
restyled pagination preserving GET params via `{% querystring ... as=x %}`.

**Template tags** (`ui_tags.py`): `status_chip_class` (chip classes),
`status_severity` (value → severity filter), `query_url` (page number → query
string preserving filters), `row_cell` (row/column cell for the details row),
`capture`/`endcapture` (capture block output into a variable for filter bars).

**Filters** (`ui_filters.py`): `peso` (₱1,234,567.89), `peso_compact` (₱53.7M).

## 4. Status → chip mapping

Single source of truth in the `status_chip_class` template tag
(`ui_tags.py`); returns Tailwind pill classes. Text label always rendered.

| Domain | Value | Severity |
|---|---|---|
| Loan status | PERFORMING | ok |
| Loan status | PAST_DUE | watch |
| Loan status | NPL | critical |
| Loan status | WRITEOFF, CLOSED | neutral |
| Classification | C (Current) | ok |
| Classification | SM (Especially Mentioned), SS (Substandard) | watch |
| Classification | D (Doubtful), L (Loss) | critical |
| Alert type | CRITICAL | critical |
| Alert type | WARNING | watch |
| Alert type | INFO | neutral |
| Alert type | SUCCESS | ok |
| Strategy status | ACTIVE | ok |
| Strategy status | COMPLETED, CANCELLED | neutral |
| Agreement status | ACTIVE | ok |
| Agreement status | COMPLETED, SUPERSEDED | neutral |
| Agreement status | RESCINDED | critical |
| Installment status | PAID | ok |
| Installment status | UNPAID | watch |
| Escalation status | PENDING, PAUSED | watch |
| Default / unknown | any other value | neutral |

## 5. HTMX conventions

- Table container id: `table-container`; filters/pagination in list pages target it.
- Filter forms: `hx-get` (same URL = `request.path`), `hx-target="#table-container"`, `hx-push-url="true"`, `hx-select="#table-container"`; `hx-indicator` overlay in `data_table.html`.
- Views are untouched: they return full HTML; `hx-select` extracts the container, so the same URL works with and without JavaScript.
- django-tables2 sort links and pagination links carry `hx-get` attributes from the override `table.html` template.
- HTMX CSRF: the base layout adds `X-CSRFToken` to every htmx request.

## 6. Component notes / findings updates

- **Collapse rule applied to >7-column tables only**: `CompromiseAgreementTable` (9 cols, collapse `discount_amount`/`discount_percentage`), `CompromiseInstallmentTable` (8, collapse `payment_date`), `CollectionActivityLogTable` (8, collapse `remarks`), `ExposureTable` (8, collapse `shouldbepay`). Borrower (6) and account list (7) tables are ≤7 — no collapse there (finding: the plan's "account_list >7" assumption did not hold; the 10-column compromise list is the flagship collapse page).
- Tables no longer use Bootstrap `table table-striped`; the django-tables2 override renders `class="app-table"` for every table.
- `compromise_agreement/tables.py` previously pinned `template_name = django_tables2/bootstrap5.html`; removed so the app override applies.

## 7. Verification status

Tracked in the change's `tasks.md` (groups 11–12). Repo root `DESIGN.md` is
kept in sync by task 11.5.

### Phase 11 sweep results (updates)

- **Bootstrap/Bootswatch removed** (task 11.3): CDN links, `bank-theme.css`,
  `layout.css`, Bootstrap JS and Bootstrap Icons CDN are gone. The shell's
  search input and user menu are Tailwind/native (`<details>` dropdown); the
  content grid is `lg:flex` Tailwind (no `row`/`col-*`).
- **Remaining Bootstrap classes live only in unused templates** — scratch
  `dashboard_*.html` variants and unused legacy partials (`_kpi_card`,
  `_risk_panel`, `_class_badge`, `_context_header`, `_alert_*`, `_decision_card`,
  `_status_badge`, `_loan_status_badge`, `_tabs`) which no rendered page
  includes; left untouched per scope.
- **Timeline restyled** (dashboard): `_timeline.html`/`_timeline_item.html`/
  `_timeline_filter.html` converted to app classes; the type/date filter
  controls were decorative (view never consumed them) and are now inert chips;
  the custom-date-range Bootstrap modal was removed with the rest of the
  timeline JS that only logged to console.
- **Color-gap check** (11.1): the only non-dark-variant utility was
  `text-slate-500` (46 uses) → now `text-slate-500 dark:text-slate-400`.
  Semantic tokens (brand/critical/watch/ok/neutral) auto-adapt via the `.dark`
  variable overrides in `input.css`, so no per-usage `dark:` variant is needed.
- **Money/count check** (11.2): all `|peso` cells and right-aligned numeric
  cells now carry `tabular-nums`.
- **Icon audit** (11.4): every icon-only button has `aria-label`; the last
  decorative heading icon (dashboard clock) was removed.
- **Testing**: full suite `278 tests OK` (6 pre-existing skips); the pre-existing
  markup-content tests in `tests.py`/`tests_alert_views.py` were updated to the
  new presentation strings (same data, new labels), and
  `test_refresh_alerts_api` invalidates the cached alert counts the global
  `ui_shell` context processor now populates.
