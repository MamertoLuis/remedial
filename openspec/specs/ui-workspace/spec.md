# ui-workspace Specification

## Purpose

Defines the observable presentation-layer behavior of the Remedial System workspace: a single design-token system, a persistent triage-first shell, shared UI components, page-type conventions, dark mode, and accessibility rules — while guaranteeing the restyle leaves all functional behavior, routing, and data semantics untouched.

## Requirements

### Requirement: Restyle preserves functional behavior

The restyle SHALL preserve every existing URL name, view name, template context variable, form field name, form `method` and `action`, GET filter parameter name, pagination parameter (`page`), search parameter, and export endpoint; the system SHALL present the same data and results as before the restyle.

#### Scenario: All existing routes still resolve

- **WHEN** a user navigates to any route that existed before the restyle
- **THEN** the route resolves with the same URL name and renders the same underlying data

#### Scenario: Form and filter parameters are unchanged

- **WHEN** a user submits any existing form or filter that reads or writes through GET or POST parameters
- **THEN** the parameter names and values accepted are exactly those accepted before the restyle

#### Scenario: Export endpoints keep their format

- **WHEN** a user triggers any existing export action (for example, the term sheet PDF)
- **THEN** the export is produced by the same endpoint in the same format as before

### Requirement: Persistent left navigation sidebar

The system SHALL render a persistent left sidebar on all authenticated pages listing Dashboard, Borrowers, Loan Accounts, Compromise Agreements, Alerts, and Reports; the item for the current page SHALL be marked with `aria-current="page"`; the Alerts item SHALL show an unread count badge when open alerts exist; and the sidebar SHALL collapse to icons at widths below 1024px and to an overlay drawer below 768px.

#### Scenario: Sidebar lists all primary navigation items

- **WHEN** an authenticated user loads any page within the workspace
- **THEN** the sidebar shows the six navigation items and the item matching the current page carries `aria-current="page"`

#### Scenario: Alerts badge reflects open alerts

- **WHEN** the authenticated user has open alerts and any page is loaded
- **THEN** the Alerts sidebar item displays a badge with the count of open alerts, and no badge when there are none

#### Scenario: Sidebar adapts to narrow viewports

- **WHEN** the viewport is narrower than 1024px
- **THEN** the sidebar collapses (icons only, or an overlay drawer below 768px) and the main content remains usable

### Requirement: Content top bar with search

Authenticated pages SHALL render a content top bar containing the page title, an as-of timestamp where the page provides one, the global search form using the pre-existing action and field name, a dark-mode toggle, and the user menu.

#### Scenario: Global search keeps its contract

- **WHEN** a user submits the global search from the top bar
- **THEN** it issues a request to the same search URL with the same field name as before the restyle and shows the results page

#### Scenario: Top bar exposes theme toggle and user menu

- **WHEN** an authenticated user loads any workspace page
- **THEN** the top bar shows the dark-mode toggle and the user menu alongside the page title

### Requirement: Single design-token system

All pages SHALL use one design-token system defining a `brand` color derived from the existing maroon brand, neutral surface and text scales, and semantic colors `critical` (red), `watch` (amber), and `ok` (emerald); tokens SHALL be defined once and reused, and every page SHALL render from tokens rather than ad-hoc colors.

#### Scenario: Tokens are applied on every page

- **WHEN** any page in the workspace is rendered
- **THEN** its colors, borders, and text derive from the shared token set

#### Scenario: Semantic colors carry meaning only

- **WHEN** a value or state is critical (NPL, overdue, critical alert) it is shown in `critical` red, watch-level states in `watch` amber, and resolved or healthy states in `ok` emerald
- **THEN** no decorative element uses a semantic color outside its meaning, and red never appears decoratively

### Requirement: Money and number formatting

All monetary values SHALL be formatted with the peso sign, thousands separators, and two decimals in tables and details, and SHALL use tabular numerals; KPI figures SHALL use the abbreviated form (for example ₱53.7M) with the full figure available in a `title` attribute; all count values SHALL use tabular numerals.

#### Scenario: Money renders consistently

- **WHEN** a monetary value is displayed in a table, detail, or KPI
- **THEN** tables and details show ₱ with thousands separators and two decimals, KPIs show the abbreviated form with the full value in a `title` attribute

#### Scenario: Tabular numerals on money and counts

- **WHEN** any money or count value is rendered
- **THEN** it uses tabular numerals so values align in columns

### Requirement: Status chips

The system SHALL render every status value as a pill-shaped chip that always shows a text label; the mapping of status values to chip colors SHALL be defined in exactly one place and reused by all templates.

#### Scenario: All statuses render as labeled chips

- **WHEN** any page shows a loan status, alert type, classification, or agreement status
- **THEN** it renders as a pill chip with a visible text label and a color from the single status-to-chip mapping

#### Scenario: Chip mapping is centralized

- **WHEN** a new status value needs a chip color
- **THEN** the change is made in the single mapping definition, and all pages reflect it

### Requirement: Dashboard triage layout

The dashboard SHALL present a KPI strip (NPL Ratio, Total NPL, Total Past Due, Past Due Ratio, Total Loan Portfolio, followed by strategy counts) where only NPL and past-due values use `critical` red, a needs-attention table of the 20 most past-due accounts sorted by days past due descending with a View all link, and an alerts panel that shows an empty state when no open alerts exist. Total Past Due and Past Due Ratio SHALL follow the umbrella past-due definition (including NPL) specified by the portfolio-metrics capability.

#### Scenario: Dashboard shows the KPI strip

- **WHEN** an authenticated user opens the dashboard
- **THEN** the KPI strip shows the portfolio and strategy KPIs with NPL and past-due values in red and other values in neutral or brand colors

#### Scenario: Past Due Ratio tile is shown

- **WHEN** an authenticated user opens the dashboard
- **THEN** the KPI strip includes a Past Due Ratio tile computed from the umbrella past-due definition

#### Scenario: Needs-attention table is a triage queue

- **WHEN** the dashboard renders the needs-attention table
- **THEN** it lists up to 20 accounts ordered by days past due descending with borrower, account number, outstanding amount, days past due, strategy, assigned officer, status chip, and an action, plus a View all link to the accounts list

#### Scenario: Alerts panel has an empty state

- **WHEN** the authenticated user has no open alerts on the dashboard
- **THEN** the alerts panel shows a "No open alerts" empty state instead of an empty list

### Requirement: List and table pages

List pages SHALL show a page header with title and record count, a filter bar above the table, and the table with its existing columns; filters SHALL read from and write to the URL query string preserving existing parameter names, and a Clear action SHALL reset them; primary cells SHALL be real links to the detail page.

#### Scenario: Filters live in the URL

- **WHEN** a user changes a filter on a list page
- **THEN** the filter values are written to the URL using the same parameter names as before and the results update

#### Scenario: Empty results are distinguishable

- **WHEN** a list filter matches no records
- **THEN** the page shows an empty state that offers a Clear filters action, distinct from the page's no-data state

#### Scenario: Rows link to details

- **WHEN** a user middle-clicks, keyboard-activates, or clicks the primary cell of a table row
- **THEN** the detail page for that record opens through a real link

### Requirement: HTMX table refreshes

On list pages, filter changes and pagination SHALL swap only the table container using HTMX (`hx-get`, `hx-target`, `hx-push-url`, `hx-select`) so the URL updates and a loading indicator shows; the same URL SHALL work with and without JavaScript.

#### Scenario: Filter change updates the table only

- **WHEN** a user changes a list filter with JavaScript enabled
- **THEN** only the table container is replaced, the URL updates via the history API, and a loading indicator appears during the swap

#### Scenario: Full-page navigation still works

- **WHEN** a user opens a list URL directly or JavaScript is disabled
- **THEN** the full page renders the same filtered results

### Requirement: Pagination preserves state

List pages SHALL keep the existing paginator and its page size and `page` parameter, restyled through the shared pagination component, and the shared component SHALL preserve all other active filter parameters while paging.

#### Scenario: Pagination keeps filters

- **WHEN** a user pages on a filtered list
- **THEN** the page number and all active filter parameters remain in the URL and the results are correct

### Requirement: Detail pages

Detail pages SHALL render a header with entity name or account number, status chip, and key identifiers; key facts in a definition grid of two or three columns; and related records in tabs or stacked sections reusing the shared table and empty-state components.

#### Scenario: Key facts render as a definition grid

- **WHEN** a user opens any detail page
- **THEN** key facts render in a two- or three-column definition grid with formatted money and a consistent date format

#### Scenario: Related records have empty states

- **WHEN** a detail page has a related-records section with no records
- **THEN** the section renders an empty state appropriate to that section

### Requirement: Form pages

Form pages SHALL render fields with labels above inputs, help text below in muted text, and validation errors in `critical` red with an icon, linked to their field via `aria-describedby`; `non_field_errors` SHALL render at the top of the form; field layout SHALL be one column on narrow viewports and two columns on desktop; every field name, widget, validation rule, and choice list SHALL be preserved.

#### Scenario: Errors are associated with fields

- **WHEN** a form submission fails validation
- **THEN** each field error renders in red with an icon and is associated with its field through `aria-describedby`

#### Scenario: Form behavior is unchanged

- **WHEN** a user submits a restyled form
- **THEN** the submitted data, validation rules, and resulting behavior are identical to before the restyle

### Requirement: Report pages

Report pages SHALL present summary figures with the shared KPI tile and tabular data with the shared table component, and SHALL keep existing export endpoints and formats unchanged.

#### Scenario: Reports reuse shared components

- **WHEN** a report page renders summary figures and tables
- **THEN** figures use the KPI tile and tables use the shared table component with empty states

### Requirement: Auth and error pages

Login SHALL render as a centered card on the surface color with the app name and form and no sidebar; logout confirmation SHALL follow the form page pattern; 403, 404, and 500 pages SHALL render a simple page with the site header, a short message, and a link to the Dashboard, and the 500 page SHALL not depend on context processors that can fail under an exception.

#### Scenario: Login page is minimal

- **WHEN** an unauthenticated user opens the login page
- **THEN** it renders a centered card with the app name and the login form and no sidebar

#### Scenario: Error pages link back to the dashboard

- **WHEN** a user encounters a 403, 404, or 500 error
- **THEN** a simple error page renders with the site header, a short message, and a link to the Dashboard

### Requirement: Messages render as toasts

Django framework messages SHALL render as toast-style notices at the top right of the page, readable in both themes; success messages SHALL auto-dismiss, and error messages SHALL remain until dismissed.

#### Scenario: Success toasts auto-dismiss

- **WHEN** a success message is emitted and the next page renders
- **THEN** it appears as a toast at the top right and disappears automatically

#### Scenario: Error toasts persist

- **WHEN** an error message is emitted and the next page renders
- **THEN** it appears as a toast at the top right and remains until the user dismisses it

### Requirement: Destructive actions confirm first

Destructive or status-changing actions (deleting a borrower, marking an installment paid, changing account status, acknowledging/resolving/dismissing alerts) SHALL require confirmation through the shared confirm modal before the action is submitted, while the action's endpoint and effect SHALL remain unchanged.

#### Scenario: Destructive action requires confirmation

- **WHEN** a user triggers a destructive or status-changing action
- **THEN** a confirmation modal appears and the action is only submitted after the user confirms

#### Scenario: Confirmation does not change the action

- **WHEN** a user confirms a destructive action in the modal
- **THEN** the request is sent to the same endpoint with the same parameters and produces the same effect as before

### Requirement: Dark mode

The system SHALL support a light and a dark theme selected through a `class` strategy, persist the choice in `localStorage`, apply the saved choice before first paint to avoid a flash, and SHALL keep every page readable in both themes.

#### Scenario: Choice persists across visits

- **WHEN** a user toggles the theme and reloads or revisits any page
- **THEN** the saved theme is applied before first paint without a flash

#### Scenario: Every page is readable in both themes

- **WHEN** any page is rendered in light and in dark theme
- **THEN** text and backgrounds meet WCAG AA contrast in both themes

### Requirement: Accessibility

All interactive elements SHALL show a visible focus ring, the active sidebar item SHALL carry `aria-current="page"`, table headers SHALL use `th scope`, sortable columns SHALL expose `aria-sort`, icon-only buttons SHALL have `aria-label`, and modals SHALL trap focus and close on Escape; tables with more than three columns SHALL have a caption or `aria-label`.

#### Scenario: Keyboard users can navigate

- **WHEN** a user navigates with the keyboard through the sidebar, filters, tables, and modals
- **THEN** every interactive element is reachable and shows a visible focus ring

#### Scenario: Modal closes on Escape and traps focus

- **WHEN** a confirmation modal is open and the user presses Escape
- **THEN** the modal closes and focus returns to the triggering element, and while open, focus is trapped within the modal
