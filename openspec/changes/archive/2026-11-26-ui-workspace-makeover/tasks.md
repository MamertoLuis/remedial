# Tasks

## 1. Phase 0 — Inventory, tokens, dependencies

- [x] 1.1 Write `DESIGN.md` at repo root: full page inventory table (route, view, template, page type, HTMX usage, pagination, destructive action) covering every app's `urls.py` (account_master, compromise_agreement, reporting, allauth, profile), color tokens, component partial context variables, HTMX conventions, status→chip mapping, and findings (404/500 missing, no report charts, compromise list unpaginated, scratch templates `dashboard_*.html`/`pasdue_aging_summary.html`, `base_report.html` `extra_head` block currently dropped); verify every route in every `urls.py` appears exactly once in the table
- [x] 1.2 Post the inventory table to the user and confirm the maroon brand hex against the reference screenshot; record the final token values (baseline assumption `#7A1F2B` maroon scale) in `DESIGN.md`; verify the DESIGN.md tokens section contains concrete hex values for brand, neutral, critical, watch, and ok
- [x] 1.3 Add the Tailwind v4 standalone CLI build: pin the version, add `static/css/input.css` with `@theme` tokens and dark-mode `class` custom variant, add a `make css` target and the Docker build step for the compiled stylesheet; verify `make css` produces committed `app.css` served by `{% static %}` on the dev container

## 2. Phase 1 — Shell and tokens

- [x] 2.1 Restructure `account_master/templates/base.html` to the sidebar + top-bar shell, keeping the `content`, `breadcrumbs`, `context_header`, `extra_css`, `extra_js`, and right-column `sidebar` blocks working and adding an `extra_head` block (fixes the dropped `base_report.html` print stylesheet); verify the shell renders every existing route with a route-sweep script returning the expected status (200, redirect, or 403) for each route
- [x] 2.2 Add an `alert_counts` template context processor (mirroring `core_data_edit_allowed`) and wire the Alerts sidebar item badge; verify the badge count matches `AlertService.get_alert_counts` for a user with open alerts and is hidden when there are none
- [x] 2.3 Render Django messages as toasts via a `toast_container` partial in the base layout (success auto-dismisses, errors persist, readable in both themes); verify a `messages.success` and a `messages.error` each render as toasts with the correct dismiss behavior in both themes
- [x] 2.4 Implement dark mode with the Tailwind `class` strategy and the pre-paint `localStorage('theme')` inline script (existing key + toggle kept); verify no theme flash on reload and the choice persists across pages
- [x] 2.5 Add Heroicons outline icon partials (inline SVG) and use them in nav and actions per the one-icon-set rule; verify icons render `aria-hidden` and every icon-only control carries an `aria-label`

## 3. Phase 2 — Shared components

- [x] 3.1 Build `page_header.html` (title, optional subtitle/record count, primary-action slot); verify it renders on one list page with documented context variables in `DESIGN.md`
- [x] 3.2 Create the `ui_filters` template library: `peso` (₱ with thousands separators and two decimals), `peso_compact` (₱53.7M with full figure in `title`), and a tabular-nums class constant; add unit tests for both filters; verify the tests pass and money in templates uses the filters instead of ad-hoc `floatformat`+₱
- [x] 3.3 Build `kpi_tile.html` (label, value, subtext, optional delta and severity, whole tile a link when a URL is given, `peso_compact` on money); verify the KPI strip renders abbreviated values with `title` attributes
- [x] 3.4 Build `status_chip.html` and the `status_chip_class` template tag backed by one status→chip mapping dict covering every value in the loan status, classification, alert type, agreement status, and installment status choice lists; add unit tests for the mapping; verify the tag test passes and a grep finds no hard-coded status badge classes remaining in templates
- [x] 3.5 Build `data_table.html` (sticky header wrapper, `<th scope="col">`, `aria-sort` from the active table order, row hover, severity row highlight, empty-state slot, `collapse_columns` `<details>` row expansion for >7-column tables with least-important columns only); verify on borrower_list (≤7 columns) and account_list (>7 columns) with secondary columns moving under 1280px
- [x] 3.6 Build `pagination.html` (Previous/Next + page numbers, preserves all GET filter parameters, HTMX attributes, loading indicator); verify paging a filtered account_list keeps every filter parameter in the URL and swaps only the table container
- [x] 3.7 Build `filter_bar.html` (horizontal filters, Clear action, existing GET parameter names, `hx-get`/`hx-target="#table-container"`/`hx-push-url="true"`/`hx-select="#table-container"`); verify a filter change updates only the table container and pushes the URL
- [x] 3.8 Build `empty_state.html` (short message + optional one action, no illustrations); verify it renders for "no records match these filters" (with Clear filters action) and for sections with no data at all
- [x] 3.9 Build `confirm_modal.html` (focus trap, Escape closes, `aria-modal`, posts to the same URL and parameters); verify the modal fires the identical POST as before for delete-borrower, account-status update, installment-paid, and alert actions
- [x] 3.10 Update `DESIGN.md` with each partial's context-variable signature, HTMX conventions, and the status→chip mapping table; verify the documented variables match what each shipped partial actually consumes

## 4. Phase 3 — Dashboard

- [x] 4.1 Add `DashboardService.get_needs_attention(limit=20)` (read-only annotated query reusing the existing latest-exposure subquery pattern, ordered by days past due descending) plus a unit test; verify the test passes and existing KPI methods are untouched (`git diff` shows no edits to them)
- [x] 4.2 Restyle the dashboard: KPI strip (red only for NPL and past-due values), needs-attention table (borrower, account no., outstanding, days past due, strategy, assigned officer, status chip, action; View all link), alerts panel with a "No open alerts" empty state; verify the page loads, KPI figures match pre-restyle values, the table matches the attention query result, and the empty alert state renders when there are no open alerts

## 5. Phase 3 — Borrowers (list → detail → form)

- [x] 5.1 Restyle borrower_list with `page_header` (title, record count, primary action), `filter_bar`, `data_table`, `pagination`, real links on primary cells, and HTMX swaps; verify filters, sorting, and pagination still change the result set, the empty-filters state offers Clear, and middle-click on a primary cell opens the detail page
- [x] 5.2 Restyle borrower_detail: entity header with name + status chip + identifiers, key facts in a 2–3 column `<dl>`, accounts table via `data_table` with `empty_state`; verify the page renders and an account-less borrower shows the empty state
- [x] 5.3 Restyle create_borrower and update_borrower (one column below 768px, two on desktop, labels above fields, help text below, errors in critical red with icon linked via `aria-describedby`, `non_field_errors` at top, primary/secondary button positions consistent); verify field names, widgets, validation, and submit behavior are unchanged by exercising save and a validation-error case
- [x] 5.4 Wire `confirm_modal` to delete-borrower from the list and detail pages (POST to the existing `delete_borrower` URL; `delete_borrower.html` page kept as the no-JS fallback); verify deletion succeeds only after confirmation and Cancel performs no request

## 6. Phase 3 — Loan accounts

- [x] 6.1 Restyle account_list: `page_header`, `filter_bar` preserving all existing GET parameter names (`status`, `account_officer`, `security`, `borrower_group`, `transaction_type`, `remedial_status`, `legal_status`, `foreclosure_status`), `data_table` with `collapse_columns` for the >7-column layout, `pagination`, HTMX swaps; verify every filter still changes results using its original parameter name and the row expansion appears below 1280px
- [x] 6.2 Restyle account_detail: header with account number + status chip + key identifiers, single action menu, key facts `<dl>` grid, related records (collection activities, strategies, exposures, delinquency history, agreements) in tabs or stacked sections reusing `data_table` and `empty_state`; verify all sections render and empty sections show empty states
- [x] 6.3 Restyle create_account and update_account forms (layout and error wiring per form rules; any existing dynamic/JS field behavior preserved); verify create and update still work end-to-end and validation errors render linked to fields
- [x] 6.4 Wrap `update_account_status` (account detail status action) with `confirm_modal`; verify the status changes only after confirmation and the `_account_status` partial swap still works

## 7. Phase 3 — Related-record pages

- [x] 7.1 Restyle collection activity list, create, and update (list via `data_table` + pagination where present, forms per form rules); verify list filters/actions and create/update POSTs still work
- [x] 7.2 Restyle exposure create and update forms; verify fields, validation, and submit behavior are unchanged
- [x] 7.3 Restyle delinquency status create and update forms; verify fields, validation, and submit behavior are unchanged
- [x] 7.4 Restyle remedial strategy create, update, and detail (detail header/dl/table/timeline conventions); verify strategy create/update still work and the detail timeline renders without decorative icons
- [x] 7.5 Restyle escalation ladder detail and issue-notice form; verify the ladder renders and issuing a notice still posts to the same URL with the same effect

## 8. Phase 3 — Compromise agreements, alerts, search

- [x] 8.1 Restyle compromise_agreement_list with `page_header` (title + count) and `data_table`; verify it renders and NO pagination is introduced (finding recorded: the view has no paginator)
- [x] 8.2 Restyle compromise agreement detail, agreement form, and installment form (header/dl/tables/empty states for detail; form rules for forms); verify create/update/mark-paid still work with mark-paid confirmed through the modal
- [x] 8.3 Verify the term-sheet PDF export endpoint still downloads a PDF unchanged after the restyle
- [x] 8.4 Restyle alert_list: `filter_bar`, `data_table`, `pagination`, HTMX container swaps, bulk acknowledge/resolve/dismiss via `confirm_modal`; verify pagination keeps parameters and alert actions confirm before firing the same POST endpoints
- [x] 8.5 Restyle search results as a list-type page with `page_header` and `empty_state`; verify the global search from the top bar still returns results with the same `q` parameter and URL

## 9. Phase 3 — Report pages

- [x] 9.1 Restyle reporting index as a list page; verify every report link renders and navigates to its report
- [x] 9.2 Restyle the five report pages with `kpi_tile` summaries and `data_table` tables, keep exports/print actions unchanged, and confirm `base_report.html`'s `extra_head` print stylesheet now loads; verify each report route renders correct figures and Print/export behavior is unchanged
- [x] 9.3 Confirm the reports have no charts (finding recorded — conditional chart requirements skipped); verify no inline SVG or chart markup uses hard-coded hex colors

## 10. Phase 3 — Auth and error pages

- [x] 10.1 Restyle login, signup, and password-reset pages as centered cards on the surface color with app name, no sidebar; verify login, signup links, and password reset flows still work
- [x] 10.2 Migrate the logout confirmation page to the new form-page pattern and shell; verify POST logout works and Cancel returns to the dashboard
- [x] 10.3 Restyle 403 and create `remedial/templates/404.html` and `remedial/templates/500.html` (simple pages, one message, Dashboard link; 500 must not depend on context processors that can fail); verify each renders with a test-client forced error and the Dashboard link works

## 11. Phase 4 — Visual system compliance sweep

- [x] 11.1 Run the color-gap check (grep for color utilities without a `dark:` variant across templates) and fix every gap; verify the sweep passes with zero findings
- [x] 11.2 Run the money/count check (grep for money values not using the shared filters or tabular-nums); fix every gap; verify no proportional-figure money or count values remain
- [x] 11.3 Remove Bootstrap/Bootswatch CDN links, `bank-theme.css`, and `layout.css` after all pages are migrated, and remove any remaining Bootstrap class usages found by grep; verify every template still renders styled with the new system
- [x] 11.4 Audit icon usage: icon-only buttons have `aria-label`, no decorative icons on headings or empty states; verify by grep + spot check
- [x] 11.5 Finalize `DESIGN.md` (page inventory, tokens, component docs, HTMX conventions, status→chip mapping, findings, verification status); verify it matches the shipped templates and lists open decisions for the user

## 12. Integration verification

- [x] 12.1 Route sweep: every route in every `urls.py` returns 200 or the expected redirect/403 for the applicable user roles; verify with a scripted test-client sweep over the route inventory
- [x] 12.2 Verify every list page's filters, sorting, and pagination still change results (per page)
- [x] 12.3 Verify every form's fields, validation errors, and submit still work (create, edit, and error cases per page)
- [x] 12.4 Verify HTMX partial responses match full-page content for the same URL (compare the `#table-container` fragment of an HX-request response with the full render)
- [x] 12.5 Verify dark mode applies on every page with no flash on load and acceptable contrast in both themes
- [x] 12.6 Verify keyboard-only navigation works on the dashboard, one list page, and one detail page (Tab/Shift+Tab order, visible focus rings, modal Escape and focus trap)
- [x] 12.7 Run the full test suite and `make audit`; verify it exits 0 with "AUDIT PASSED" (or the fixed equivalent)

## Workflow follow-up

- Archive the change after the project's review requirements are satisfied.
- Verify the archived result.
