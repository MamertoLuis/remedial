# Proposal

## Why

The Remedial System UI (Bootswatch United on Bootstrap, top navbar, large KPI cards, side filter panes, full-page-reload filters) is not built for triage. Staff work in it all day, so scanning, density, and consistency matter more than decoration. The current dashboard buries attention items, money figures are hard to scan, list filters reload whole pages, and pages are visually inconsistent with each other (mixed dark-mode support, ad-hoc badge/status styling, no empty states, no rendered Django messages). A triage-first workspace built on shared design tokens and components will make overdue/NPL accounts the first thing staff see and make every list/detail/form page feel like one product.

## What Changes

Presentation-only redesign. No business logic, models, calculations, permissions, or URL names change. Queries are touched only where a restyled template strictly requires a *new read-only* dataset.

- **Shell**: Replace the top navbar with a left sidebar (Dashboard, Borrowers, Loan Accounts, Compromise Agreements, Alerts with badge count, Reports). Content top bar holds page title, as-of timestamp, global search (same form action + field name), dark-mode toggle, user menu. Base layout must keep rendering every existing page.
- **Design tokens**: `brand` (maroon), neutral slate surface/text scales, semantic `critical`/`watch`/`ok`. One status→chip mapping defined in one place. Inter typography, `tabular-nums` on all money/counts. Dark mode via Tailwind `class` strategy, same `localStorage` key, inline pre-paint script.
- **Shared partials** (`templates/partials/`): `kpi_tile`, `status_chip`, `data_table`, `pagination`, `filter_bar`, `empty_state`, `page_header`, money formatter (₱, thousands separators, abbreviated KPIs with `title`), `confirm_modal`.
- **Dashboard**: KPI strip (not large cards: NPL Ratio, Total NPL, Total Past Due, Total Loan Portfolio, strategy counts — red only for NPL/past due), a needs-attention table (20 rows, days past due desc, View all link), alerts panel with empty state. A new read-only needs-attention dataset is added to the dashboard view (strictly required by the template; no existing queries/calculations change).
- **List pages**: `filter_bar` above tables writing to the existing GET parameter names; HTMX swaps of the table container only (`hx-get`/`hx-target`/`hx-push-url`/`hx-select`); restyled existing paginator preserving params; sortable headers kept where the view already sorts (django-tables2 `RequestConfig`); real `<a>` links on primary cells; empty states distinguishing "no records match filters" from "no data".
- **Detail pages**: header with entity name + status chip + key identifiers, single action menu; key facts in a 2–3 column `<dl>`; related records in tabs/sections reusing `data_table`/`empty_state`; plain-text vertical timeline.
- **Form pages**: two columns on desktop, labels above fields, errors in critical red with icon + `aria-describedby`, `non_field_errors` at top, primary button position consistent, CSRF/`method`/`action`/field names untouched.
- **Report pages**: `kpi_tile` summaries, `data_table` tables, exports unchanged. No charts exist in the codebase today — chart styling is conditional and skipped (finding).
- **Auth/error pages**: login as centered card on surface color without sidebar; 403 restyled; **404/500 templates do not exist today and will be added** as presentation-only pages (500 must not depend on context processors that can fail); logout confirmation follows the form pattern.
- **States**: Django messages rendered as toasts (they are currently never rendered anywhere); destructive/status-changing actions (`delete_borrower`, `mark_installment_paid`, `update_account_status`, alert ack/resolve/dismiss) use `confirm_modal` — action behavior and URLs unchanged, delete page remains as fallback.
- **Accessibility & responsive**: visible focus rings, `aria-current` on active nav, `th scope`/`aria-sort`, modal focus trap + Escape, `aria-label` on icon-only buttons; sidebar collapses below 1024px, tables scroll in-container below 768px.
- **Dependencies (only additions, with reason)**: Tailwind CSS build (no Node/framework — standalone CLI or equivalent so no build framework is introduced); exactly one icon set from Heroicons or Lucide (replaces ad-hoc Bootstrap Icons usage to satisfy the one-icon-set rule).

## Capabilities

### New Capabilities
- `ui-workspace`: Owning requirements for the application's presentation layer as a durable system behavior — shell/navigation, design tokens, shared UI components, page-type presentation conventions (dashboard, list, detail, form, report, auth, error), dark mode, money/date formatting, and accessibility/formatting rules. Future visual-evolution changes land here.

### Modified Capabilities
- (none — existing capabilities `account-upsert`, `core-data-edit-access`, `strategy-compromise-supersede` keep their requirements; behavior is unchanged, only presentation.)

## Impact

- **Templates**: every template under `account_master/templates/`, `compromise_agreement/templates/`, `reporting/templates/`, `users/profile.html`, and allauth `account/*` templates; `base.html` shell restructure; shared partials rewritten/added in `templates/partials/` (and `compromise_agreement/templates/compromise_agreement/` partials).
- **Views**: no logic changes. Dashboard view gains one read-only needs-attention dataset. A template context processor (mirroring existing `core_data_edit_allowed` pattern) exposes `alert_counts` for the sidebar badge.
- **Static assets**: Bootstrap/Bootswatch CDN links and `bank-theme.css`/`layout.css` replaced by Tailwind-compiled CSS; icon set swapped to one library; chart colors (none today) read tokens.
- **Dependencies (new)**: Tailwind (build tooling, standalone CLI, no frontend build framework), one icon library (Heroicons or Lucide). Docker/uv: add the CSS compile step for local and container builds.
- **Known findings recorded for the implementer** (in `DESIGN.md`): `404.html`/`500.html` missing; no charts in reporting; `compromise_agreement_list` has no pagination (not added); scratch templates (`dashboard_*.html`, `pasdue_aging_summary.html`) exist unused and stay untouched; search results page is list-type.
