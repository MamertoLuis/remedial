Below is a **complete AI-agent UI guide** for building data-heavy, internal **business UIs** in **Django server-rendered HTML** (optionally HTMX), optimized for **speed, accuracy, and auditability**. You can paste this into `UI_GUIDE.md` and hand it to any coding agent.

---

# AI Agent UI Guide for Business Apps (Django HTML Views)

## 0) Goal and Non-Goals

### Primary goals

1. **Speed**: users complete tasks with minimal clicks and typing.
2. **Accuracy**: reduce mis-clicks and wrong-record edits.
3. **Traceability**: changes are attributable and reviewable.
4. **Consistency**: same patterns everywhere; users learn once.

### Non-goals

* Pixel-perfect marketing design
* Complex SPA behavior
* Heavy modal workflows
* Novel UI patterns

---

## 1) Product Mental Model

### Entity-driven navigation

Users think in **entities**, not pages:

* Borrower → Loan Account → Exposure Snapshot (date) → Delinquency → Provision → Remedial Strategy → Activities

Design UI around **“workspaces”**:

* A workspace is the “home” for one entity (Borrower workspace, Loan workspace).
* Users should never feel “lost” in the app.

### Three layers of information

Every workspace must separate information into:

1. **Orientation**: “What record am I in?”
2. **Decision**: “What do I do next?”
3. **Investigation**: “Why / history / evidence”

Never mix all three in one long scroll.

---

## 2) Global Layout Standard

### Required page structure

All pages follow this layout:

1. **Topbar** (global)

* Search
* Quick create
* Notifications
* Profile/logout

2. **Context Header** (sticky)

* Entity identifier(s)
* Status badges
* Key metrics (3–6)
* Primary actions (1–3)

3. **Main content**

* Decision area (cards / forms)
* Investigation area (tabs / collapses)

4. **Footer** (optional)

* build/version, help links

### Sticky context header rule

On any detail/workspace page, the context header must remain visible while scrolling.

---

## 3) Navigation Patterns

### Breadcrumbs (mandatory)

Always show breadcrumb trail:

* Dashboard → Borrowers → Juan Dela Cruz → Loan LN-0045 → Snapshot 2025-12-31

### Primary navigation style

* Lists open detail/workspace pages.
* Avoid “jumping around menus” once in a workflow.

### URL conventions (predictable REST-ish)

* `/borrowers/`
* `/borrowers/<id>/`
* `/borrowers/<id>/loans/`
* `/loans/<id>/`
* `/loans/<id>/snapshots/<date>/`

---

## 4) Workspace Pattern

### Default workspace layout

**Loan Workspace** example:

A) Sticky Context Header

* Loan ID, Borrower name, balance, DPD, classification, strategy, officer

B) Decision Cards (editable)

* Delinquency State
* Provision for Losses
* Remedial Strategy
* Next Action

C) Investigation Tabs (read-only heavy content)

* Summary (default)
* Financial History
* Collection Activities
* Legal
* Documents

#### Rule: “Decision first”

Decision cards must appear above investigative tables.

---

## 5) Progressive Disclosure (Anti-Overwhelm Rules)

### Hard limits per screen (default view)

* Max **5 cards** visible
* Max **1 primary table**
* Max **3–6 KPIs**
* Max **5 rows** shown before “View all”

### Collapse & expand

* If content is > 1 screen: make it collapsible.
* Default state shows summaries, not full tables.

### “Recent first”

History displays default to:

* last 30/60/90 days, or
* last 10 events
  Provide filters to expand.

---

## 6) Tabs vs Subpages vs Modals

### Use tabs for: “same object, different lens”

Example: Loan workspace tabs for financial/collection/legal.

### Use subpages for: “deep workflows”

* Filing legal case
* Uploading many documents with tags
* Creating a compromise schedule

### Avoid modals for:

* multi-field edits
* anything requiring validation feedback
* anything that might need bookmarking or revisiting

Modals allowed only for:

* quick confirmations
* tiny single-field edits
* view-only popovers

---

## 7) Tables: The Most Important Component

### Standard table behavior

Every operational table should support:

* Sorting (server-side)
* Filtering/search (server-side)
* Pagination (server-side)
* Row click to open workspace/detail
* “Actions” column for explicit operations

### Column rules

* Leftmost column: primary identifier (Borrower name / Loan ID)
* Always show critical status columns (DPD, classification, stage)
* Keep columns stable across pages (same order, same meaning)

### “Actions” column rules

* Place “Actions” at far right.
* Prefer explicit buttons/links vs hidden row menus.
* Use verbs: View, Edit, Add Activity, Upload Doc.

### Long tables

Do not render 500 rows on initial view.

* Show summary counts
* Show first page only
* Provide filters

---

## 8) Forms & Editing Patterns

### Default pattern: Display → Inline Edit

* Show read-only card with values
* “Edit” swaps to form
* Save returns to display mode with success message

### Form design rules

* Put **labels above inputs**
* Provide help text sparingly, only where needed
* Prefer dropdowns/radios over free typing for controlled fields
* Use sane defaults
* Use consistent button placement: **Save** (primary), **Cancel** (secondary)

### Validation rules

* Validate server-side always
* Show errors inline under the field
* Show a summary alert at top only if many errors

### High-risk field change confirmation

For critical changes (classification/provision/strategy):

* require a reason
* show before/after
* confirm intent

Example confirm block:

* “You are changing classification: Substandard → Doubtful”
* Reason field
* Confirm button

---

## 9) Historical Data: Snapshots & Audit

### Snapshots are immutable by default

Exposure snapshots should be:

* append-only
* time-stamped
* created by system or authorized user action

Never silently overwrite snapshot history.

### Audit log is mandatory for:

* delinquency changes
* classification changes
* provision changes
* strategy changes
* legal case state changes

Audit view pattern:

* Activity timeline (reverse chronological)
* shows who/when/what changed + reason

---

## 10) Status Badges and Color Rules

### Color is reserved for risk signals

Do not use color for decoration.

Recommended status palette logic (conceptual):

* Current = neutral
* Especially Mentioned = info
* Substandard = warning
* Doubtful = danger
* Loss = critical/dark danger

### Badge rules

* Badges should be short (1–2 words)
* Put key badges in the sticky header
* Do not stack more than 5 badges

---

## 11) The “Case Console” Panel (Always Visible)

On any Loan workspace, include a compact “Risk Panel” showing:

* DPD
* Classification
* Provision %
* Strategy
* Last payment date
* Next action
* Assigned officer

This is the user’s mental anchor.

---

## 12) The “Summary First” Pattern (Default Tab)

Default tab (“Summary”) must answer:

* What is the current state?
* What changed recently?
* What should I do next?

Recommended components:

* KPIs (3–6)
* “Recent activity” (last 5)
* “Next action” card
* “Alerts” (policy or deadline flags)

Avoid long tables on Summary.

---

## 13) Investigation Tabs: How to Group Models

Group by **user question**, not by database table.

### Financial History tab

Answers: “Is the borrower paying and exposure moving?”
Includes:

* exposure snapshots
* payment history
* DPD progression

### Collection Activities tab

Answers: “What did we do to collect?”
Includes:

* call/visit logs
* letters/SMS
* promised-to-pay tracking

### Legal tab

Answers: “Are we escalating and what’s the status?”
Includes:

* demand letters
* cases, filings, court dates
* foreclosure steps

### Documents tab

Answers: “What evidence do we have?”
Includes:

* contracts
* IDs
* letters
* pleadings
  Never mix documents into decision cards.

---

## 14) Searching and Filtering

### Global search

Topbar search should support:

* Borrower name
* Loan ID / Account number
* Case number (legal)
* Document tag

### Contextual search

Within a workspace tab, allow filtering for:

* date range
* activity type
* status

Default filters:

* last 30 days
* latest first

---

## 15) Messaging & Alerts

### Feedback types

1. Success (after save)
2. Warning (policy risk)
3. Error (validation/system)
4. Info (read-only hints)

### Placement rules

* Success message near the edited component (and optionally top flash)
* Validation errors inline on fields
* Critical warnings in Summary tab and/or sticky header

---

## 16) Performance and Rendering Rules (Django)

### Server-side first

* Pagination is server-side
* Sorting is server-side
* Filtering is server-side

### Avoid expensive joins on every detail view

* Precompute summaries
* Load heavy history via tab navigation (not on initial render)

### Lazy-load heavy sections (optional HTMX)

* Default tab renders immediately
* Other tabs load on click
* Large tables can load after filter selection

---

## 17) HTMX Patterns (Optional but Recommended)

Use HTMX for:

* inline edit swaps (display ↔ form)
* tab content loading
* adding timeline activities without full page reload
* updating KPI cards after saves

Do not use HTMX for:

* complex client-side state management
* offline workflows

---

## 18) Access Control & Safety UX

### Visible permissions

* Hide actions user cannot perform (or disable with tooltip)
* Show “Read-only” banner where applicable

### Destructive actions

* Require confirmation
* Provide clear consequences
* Prefer “Archive” over “Delete”
* Always log who did it

---

## 19) Consistency Checklist (Agent Must Enforce)

For every new page:

* ✅ Breadcrumb present
* ✅ Sticky context header on detail/workspace
* ✅ Primary action buttons consistent placement
* ✅ One main table max on default view
* ✅ “View all” for long lists
* ✅ Audit log for critical changes
* ✅ Server-side pagination/sort/filter
* ✅ No giant scroll walls

---

## 20) Recommended Page Templates (Standard Set)

Minimum templates the agent should implement:

* `base.html` (topbar, layout shell)
* `partials/_breadcrumbs.html`
* `partials/_context_header.html`
* `partials/_kpi_row.html`
* `partials/_card_display.html`
* `partials/_card_form.html`
* `partials/_tabs.html`
* `partials/_table.html`
* `partials/_timeline.html`
* `partials/_filters.html`

---

## 21) Concrete Layout for Your Flow

### Landing/Dashboard

* KPI cards (portfolio totals)
* Alerts (overdue thresholds)
* Recent activity

### Borrower Detail (Workspace)

* Sticky borrower header
* Tabs: Summary / Loans / Documents / Activities

### Loan Workspace (Primary)

* Sticky loan header (risk panel)
* Decision cards: delinquency, provision, strategy, next action
* Tabs: Summary / Financial History / Collection / Legal / Documents

### Exposure Snapshot

* Read-only snapshot facts
* Link back to Loan workspace
* Historical snapshots table under Financial tab only

### Delinquency/Provision/Strategy

* Edit via decision cards (inline edit)
* History via timeline

### Collection Activities

* Add activity form (quick)
* Timeline list default (latest first)
* Filter by type/date

---

## 22) Definition of “Done” for a Feature

A module is complete only if:

* List + detail/workspace exist
* Filters/sort/pagination work
* Inline edit works with validation
* Audit log entry on changes
* “Recent” summaries exist
* Navigation is consistent
* Page is not scroll-heavy

---
**text wireframe** 

---

# Loan Workspace — Sample Wireframe

---

## 1) Global Frame

```
+----------------------------------------------------------------------------------+
| TOPBAR:  Logo | Global Search | +New | Alerts | User Menu                        |
+----------------------------------------------------------------------------------+
| Breadcrumbs: Dashboard > Borrowers > Juan Dela Cruz > Loan LN-0045              |
+----------------------------------------------------------------------------------+
| STICKY CONTEXT HEADER                                                            |
| Borrower: Juan Dela Cruz         Loan: LN-0045        Officer: A. Reyes          |
| Balance: 118,000                 DPD: 147             Last Payment: Oct 12       |
| Classification: [ DOUBTFUL ]     Strategy: [ RESTRUCTURE ]                       |
| Next Action: Demand Letter       Provision: 50%                                   |
+----------------------------------------------------------------------------------+
```

This section must remain visible while scrolling.

---

## 2) Decision Area (Primary Working Section)

```
+----------------------------------------------------------------------------------+
| DECISION CARDS                                                                   |
+----------------------------------------------------------------------------------+

+--------------------------+  +--------------------------+  +--------------------+
| DELINQUENCY              |  | PROVISION                |  | STRATEGY           |
| Status: Doubtful         |  | Level: 50%               |  | Restructure        |
| Reason: No payment 3 mos |  | Basis: 147 DPD           |  | Type: Compromise   |
|                          |  |                          |  |                    |
| [ Edit ]                 |  | [ Edit ]                 |  | [ Edit ]           |
+--------------------------+  +--------------------------+  +--------------------+

+--------------------------+  +-----------------------------------------------+
| NEXT ACTION              |  | QUICK ADD ACTIVITY                            |
| Demand Letter            |  | Type: [Call ▼]                                |
| Due: Tomorrow            |  | Notes: __________________________             |
|                          |  | [ Add Activity ]                               |
| [ Mark Done ]            |  +-----------------------------------------------+
+--------------------------+
```

Rules:

* Edit swaps card into form (HTMX partial)
* No historical tables here
* This is the “what do I do” zone

---

## 3) Investigation Area (Tabs)

```
+----------------------------------------------------------------------------------+
| TABS                                                                             |
| [ Summary ] [ Financial History ] [ Collection Efforts ] [ Legal ] [ Documents ] |
+----------------------------------------------------------------------------------+
```

---

## 4) Summary Tab (Default View)

```
SUMMARY

+---------------------+---------------------+----------------------+
| Missed Payments: 5  | Broken Promises: 2  | Contact Attempts: 7  |
+---------------------+---------------------+----------------------+

Recent Activity
------------------------------------------------------------
Mar 10  Call – unreachable
Mar 05  SMS Reminder sent
Mar 01  Classification changed to Doubtful

Alerts
------------------------------------------------------------
⚠ No contact in 30 days
⚠ Past restructuring failed
```

Rule: Never more than ~1 screen tall.

---

## 5) Financial History Tab

```
FINANCIAL HISTORY

Latest Snapshot
------------------------------------------------------------
Principal: 118,000
Interest: 3,200
DPD: 147
Classification: Doubtful

Exposure Movement
------------------------------------------------------------
Date        Balance   DPD   Class
Mar 31      118,000   147   Doubtful
Feb 28      120,000   92    Substandard
Jan 31      120,000   35    Especially Mentioned
[ View All ]

Payments
------------------------------------------------------------
Date        Amount    Method
Feb 10      2,000     Cash
Jan 12      2,000     Cash
[ View All ]
```

Rule: Show only recent rows + “View All”

---

## 6) Collection Efforts Tab

```
COLLECTION EFFORTS

+ Add Activity
Type: [Call ▼]  Officer: [Auto]
Notes: __________________________
[ Save ]

Timeline
------------------------------------------------------------
Mar 10  Call – unreachable
Mar 08  Field Visit – borrower absent
Mar 05  SMS Reminder sent
Mar 02  Demand Letter prepared
```

Timeline replaces long tables.

---

## 7) Legal Tab

```
LEGAL

Case Status: Pre-Legal

+---------------------+----------------------+
| Demand Letter       | Small Claims Case    |
| Sent: Mar 02        | Not Filed            |
| Received: No        |                      |
| [ Upload Proof ]    | [ File Case ]        |
+---------------------+----------------------+

Court Events
------------------------------------------------------------
(no entries)
```

---

## 8) Documents Tab

```
DOCUMENTS

[ Upload Document ]

Type        Filename              Date
------------------------------------------------
ID          id_scan.pdf           Jan 05
Contract    promissory_note.pdf   Jan 05
Letter      demand_letter.pdf     Mar 02
```

Documents never mixed with workflow screens.

---

# Borrower Detail Wireframe (Simpler Workspace)

```
HEADER
Borrower: Juan Dela Cruz
Total Balance: 420,000
Active Loans: 3
Risk Level: HIGH

TABS
[ Summary ] [ Loans ] [ Activities ] [ Documents ]

Loans Tab
------------------------------------------------
Loan ID   Balance   DPD   Class    Officer
LN-0045   118,000   147   Doubtful Reyes
LN-0033   200,000   0     Current  Cruz
```

---

# Design Rules Embedded in This Wireframe

1. Context always visible
2. Decisions above history
3. History grouped by question
4. One major table per tab
5. Recent-first display
6. Edit inline, not new page
7. Timeline replaces audit confusion

---

**Bootstrap-5 specific guide** 


Design principle:

> Simulate “interaction” using layout and navigation — not JavaScript.

---

## 1. Layout Foundation

Use a permanent 3-zone layout:

```
Topbar (global navigation)
Sticky Context Header (record identity)
Scrollable Work Area
```

### base.html skeleton

```html
<body class="bg-light">

<nav class="navbar navbar-dark bg-dark navbar-expand-lg">
  <!-- global navigation -->
</nav>

<div class="container-fluid">

  <!-- Breadcrumb -->
  <div class="row mt-2">
    <div class="col">
      {% include "partials/breadcrumbs.html" %}
    </div>
  </div>

  <!-- Sticky Context Header -->
  <div class="row">
    <div class="col">
      <div class="card sticky-top shadow-sm" style="top: 60px; z-index: 100;">
        {% block context_header %}{% endblock %}
      </div>
    </div>
  </div>

  <!-- Main Work Area -->
  <div class="row mt-3">
    <div class="col-lg-9">
      {% block main %}{% endblock %}
    </div>
    <div class="col-lg-3">
      {% block sidebar %}{% endblock %}
    </div>
  </div>

</div>
</body>
```

---

## 2. Context Header Pattern (Most Important Component)

Use badges heavily.

```html
<div class="card-body d-flex flex-wrap gap-4 align-items-center">

  <div>
    <div class="fw-bold fs-5">{{ loan.borrower }}</div>
    <div class="text-muted small">{{ loan.account_no }}</div>
  </div>

  <span class="badge bg-danger">Doubtful</span>
  <span class="badge bg-warning text-dark">147 DPD</span>
  <span class="badge bg-secondary">Restructure</span>

  <div class="ms-auto text-end">
    <div class="fw-semibold">Balance</div>
    <div class="fs-5">{{ loan.balance }}</div>
  </div>

</div>
```

Rule:

> The user must identify the account in < 1 second.

---

## 3. Decision Cards (Editable Without HTMX)

Instead of inline swap, use **collapse edit panels**.

### Display mode

```html
<div class="card">
  <div class="card-body">

    <div class="d-flex justify-content-between">
      <div>
        <div class="text-muted small">Provision</div>
        <div class="fs-5">50%</div>
      </div>

      <button class="btn btn-sm btn-outline-primary"
              data-bs-toggle="collapse"
              data-bs-target="#editProvision">
        Edit
      </button>
    </div>

    <div class="collapse mt-3" id="editProvision">
      <form method="post">
        {% csrf_token %}
        {{ form.provision }}

        <div class="mt-2">
          <button class="btn btn-primary btn-sm">Save</button>
          <button type="button" class="btn btn-secondary btn-sm"
                  data-bs-toggle="collapse"
                  data-bs-target="#editProvision">
            Cancel
          </button>
        </div>
      </form>
    </div>

  </div>
</div>
```

This replaces HTMX inline edit cleanly.

---

## 4. Tabs Instead of Multiple Pages

Bootstrap Tabs = your best friend.

```html
<ul class="nav nav-tabs mb-3">
  <li class="nav-item">
    <a class="nav-link active" data-bs-toggle="tab" href="#summary">Summary</a>
  </li>
  <li class="nav-item">
    <a class="nav-link" data-bs-toggle="tab" href="#financial">Financial</a>
  </li>
  <li class="nav-item">
    <a class="nav-link" data-bs-toggle="tab" href="#collection">Collection</a>
  </li>
  <li class="nav-item">
    <a class="nav-link" data-bs-toggle="tab" href="#legal">Legal</a>
  </li>
</ul>

<div class="tab-content">
  <div class="tab-pane fade show active" id="summary">
    {% include "loan/tabs/summary.html" %}
  </div>
  <div class="tab-pane fade" id="financial">
    {% include "loan/tabs/financial.html" %}
  </div>
</div>
```

Important:

> Each tab answers one question only.

---

## 5. Tables (Operational Standard)

Always use:

```html
<table class="table table-sm table-hover align-middle">
```

Never large striped tables for operations — visual noise.

### Row click pattern

Make row clickable:

```html
<tr onclick="window.location='{{ obj.get_absolute_url }}'" style="cursor:pointer;">
```

Action buttons must stop propagation:

```html
<button onclick="event.stopPropagation();">
```

---

## 6. Timeline Instead of Giant Tables

Use list groups for activities.

```html
<ul class="list-group list-group-flush">

  <li class="list-group-item">
    <div class="d-flex justify-content-between">
      <div>Call — unreachable</div>
      <small class="text-muted">Mar 10</small>
    </div>
  </li>

</ul>
```

This dramatically improves readability.

---

## 7. Forms UX Rules

Use vertical forms.

```
Label
[ Input ]
help text
```

Never horizontal forms — terrible for dense data entry.

### Required settings

* `form-control-sm`
* `col-md-6` width max
* Group related inputs in cards

---

## 8. Alerts and Messages

Use Django messages framework:

```html
{% if messages %}
  {% for message in messages %}
    <div class="alert alert-{{ message.tags }} alert-dismissible fade show">
      {{ message }}
      <button class="btn-close" data-bs-dismiss="alert"></button>
    </div>
  {% endfor %}
{% endif %}
```

Rules:

* Success after save
* Warning for policy risk
* Danger only for blocking errors

---

## 9. Right Sidebar (Very Powerful in Bootstrap)

Use for decision summary.

```html
<div class="card">
  <div class="card-header">Account Health</div>
  <div class="card-body small">

    <div class="d-flex justify-content-between">
      <span>Missed Payments</span>
      <span class="fw-bold">5</span>
    </div>

    <div class="d-flex justify-content-between">
      <span>Broken Promises</span>
      <span class="fw-bold">2</span>
    </div>

  </div>
</div>
```

Users constantly glance here while working.

---

## 10. Performance Trick (No JS Needed)

Never load all related objects in detail view.

Instead:

* Summary tab: minimal queries
* Other tabs: load only needed data
* Use pagination everywhere

---

## Bootstrap Components You Should Use

| Component      | Purpose                |
| -------------- | ---------------------- |
| Navbar         | global navigation      |
| Card           | all content containers |
| Badge          | statuses               |
| Collapse       | edit forms             |
| Tabs           | data grouping          |
| List group     | timelines              |
| Table-sm hover | operations tables      |
| Alert          | feedback               |
| Sticky-top     | context                |

Avoid:

* Modals for forms
* Carousels
* Fancy dropdown menus
* Accordions for core workflow

---

## Golden Rule

> If a user must scroll more than one screen before deciding → redesign.

---
Great — now we’ll make a **mini design system** so every page in your Django app looks consistent without designers or JS frameworks.

You’ll end up with:

> predictable screens → less thinking → faster staff → fewer mistakes

You can copy this into:
`static/css/bank-theme.css`
and include it in `base.html`.

---

# Bootstrap 5 Mini Design System (Operations / Banking UI)

This is NOT branding design.
This is **operational clarity design**.

---

## 1) Color Philosophy

Color is only for **meaning**, never decoration.

| Meaning             | Use    |
| ------------------- | ------ |
| Neutral information | Gray   |
| Informational       | Blue   |
| Attention needed    | Yellow |
| Risk                | Orange |
| Critical            | Red    |
| Success/completed   | Green  |

---

## 2) Status Color Mapping (Important)

Use consistent classification colors everywhere.

| Classification       | Bootstrap |
| -------------------- | --------- |
| Current              | secondary |
| Especially Mentioned | info      |
| Substandard          | warning   |
| Doubtful             | danger    |
| Loss                 | dark      |

### Badge helper (Django template idea)

```
{% include "partials/class_badge.html" with status=loan.classification %}
```

---

## 3) Typography Rules

Users read numbers all day → prioritize readability.

Add to CSS:

```css
body {
    font-size: 0.92rem;
}

h1,h2,h3,h4 {
    font-weight: 600;
}

.table {
    font-size: 0.88rem;
}

.metric {
    font-size: 1.2rem;
    font-weight: 600;
}

.small-label {
    font-size: .72rem;
    color: #6c757d;
    text-transform: uppercase;
    letter-spacing: .03em;
}
```

Goal:

* Labels small
* Values prominent

---

## 4) Card System (Most Important)

Every screen should visually look the same.

```css
.card {
    border: none;
    box-shadow: 0 1px 2px rgba(0,0,0,.06);
}

.card-header {
    background: white;
    font-weight: 600;
    border-bottom: 1px solid #eee;
}

.card-section-title {
    font-size: .75rem;
    text-transform: uppercase;
    color: #6c757d;
    margin-bottom: .25rem;
}
```

Now every module visually matches automatically.

---

## 5) Sticky Context Header Style

```css
.context-header {
    background: #fff;
    border-left: 4px solid #0d6efd;
}
```

Visually anchors the page.

---

## 6) Table Standard

Operational tables must be calm and readable.

```css
.table {
    --bs-table-striped-bg: #fafafa;
}

.table thead th {
    font-size: .72rem;
    text-transform: uppercase;
    color: #6c757d;
    letter-spacing: .03em;
    border-bottom: 1px solid #dee2e6;
}

.table-hover tbody tr:hover {
    background: #f3f6f9;
}
```

No heavy borders. No visual noise.

---

## 7) Form Controls (Data Entry Optimized)

```css
.form-control,
.form-select {
    font-size: .9rem;
}

.form-label {
    font-size: .75rem;
    font-weight: 600;
    text-transform: uppercase;
    color: #6c757d;
}

input:focus,
select:focus {
    box-shadow: none !important;
    border-color: #0d6efd;
}
```

Prevents visual fatigue.

---

## 8) Decision Panel Style

Used in right sidebar.

```css
.kpi-row {
    display: flex;
    justify-content: space-between;
    margin-bottom: .4rem;
}

.kpi-label {
    color: #6c757d;
}

.kpi-value {
    font-weight: 600;
}
```

---

## 9) Timeline Style (Activity Logs)

```css
.timeline-item {
    border-left: 2px solid #dee2e6;
    padding-left: .6rem;
    margin-bottom: .7rem;
}

.timeline-date {
    font-size: .72rem;
    color: #6c757d;
}

.timeline-event {
    font-weight: 500;
}
```

Much easier than tables for history.

---

## 10) Buttons (Prevent Accidental Clicks)

Rules:

* Primary → Save
* Secondary → Cancel
* Outline → Edit
* Danger → irreversible actions

```css
.btn {
    padding: .25rem .6rem;
    font-size: .85rem;
}

.btn-danger {
    font-weight: 600;
}
```

---

## 11) Alerts Standard

Never overwhelm users with color.

```css
.alert {
    padding: .4rem .7rem;
    font-size: .85rem;
}
```

---

## 12) Spacing System

Consistent spacing makes UI feel “professional”.

Use only:

| Class | Usage         |
| ----- | ------------- |
| mb-1  | tight         |
| mb-2  | normal        |
| mb-3  | section       |
| mb-4  | major section |

Avoid random margins.

---

## 13) How Agents Should Use This System

When creating any page:

1. Wrap sections in cards
2. Put labels using `.small-label`
3. Show key numbers using `.metric`
4. Put history in timeline, not tables
5. Never invent new colors
6. Reuse components only

---


