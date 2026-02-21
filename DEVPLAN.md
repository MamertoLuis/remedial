# Development Plan

This document tracks the development plan and accomplishments.

## Current Status

### Completed (MVP 1: Account Master)
- [x] Borrower list view
- [x] Add search functionality to Borrower list view
- [x] Core Django models for all entities (Borrower, LoanAccount, Exposure, Delinquency, etc.)
- [x] Full CRUD operations with role-based permissions
- [x] Basic Django templates with Bootstrap 5
- [x] HTMX integration for dynamic updates
- [x] Audit fields for tracking changes

### Completed (Phase 1: Foundation & Workspace Pattern) - ✅ DONE
- [x] Enhanced `base.html` with 3-zone layout structure
- [x] Added global search functionality to topbar (view and URL)
- [x] Standardized navigation with icons and proper URL names
- [x] Added quick create dropdown in navigation
- [x] Enhanced user menu with role display and icons
- [x] Created `layout.css` with all necessary styles (sticky headers, status badges, etc.)
- [x] Created `partials/_breadcrumbs.html` component
- [x] Created `partials/_status_badge.html` component (color-coded classification badges)
- [x] Created `partials/_context_header.html` component (sticky entity headers)
- [x] Created `partials/_decision_card.html` component (editable decision cards)
- [x] Created `partials/_risk_panel.html` component (always visible risk panel)
- [x] Created search view with comprehensive search results template
- [x] Updated dashboard, borrower, and account views to provide breadcrumb context
- [x] Added entity type context to detail views for proper context headers
- [x] Fixed URL name mismatches throughout templates
- [x] Verified Django checks pass (0 errors)
- [x] Verified base template loads correctly with all components

## Future Development Phases

### Phase 1: Foundation & Workspace Pattern (Priority: HIGH) - ✅ COMPLETED
**Goal**: Implement the core workspace pattern with sticky context headers

#### Features ✅ COMPLETED
- [x] Enhance base template with 3-zone layout (topbar, sticky context header, scrollable work area)
- [x] Add global search functionality to topbar
- [x] Standardize breadcrumb navigation across all pages
- [x] Create standard context header component (`partials/_context_header.html`)
- [x] Make context headers sticky using Bootstrap's `sticky-top` class
- [x] Include KPI panel (always visible risk panel)
- [x] Convert existing detail pages to workspace pattern
- [x] Implement "Decision first" layout (decision cards above investigation content)
- [x] Add consistent primary action buttons

### Phase 2: Enhanced Dashboard & KPIs (Priority: HIGH)
**Goal**: Create a dashboard that answers "What do I need to do today?"

#### Features
- [ ] Dashboard redesign with portfolio KPI cards (total exposure, NPL ratio, etc.)
- [ ] Add "Recent Activity" timeline (last 5 activities)
- [ ] Create "Alerts" section for policy violations or deadlines
- [ ] Add "Next Actions" widget for pending tasks
- [ ] Implement Summary Tab pattern with KPIs, recent activity, and alerts
- [ ] Make Summary tab the default for all workspaces

### Phase 3: Tabbed Interface & Timeline Components (Priority: MEDIUM)
**Goal**: Replace tables with user-friendly tabbed interfaces and timelines

#### Features
- [ ] Create Tab Navigation component (`partials/_tabs.html`)
- [ ] Implement Bootstrap tabs for different data views
- [ ] Build Timeline component (`partials/_timeline.html`)
- [ ] Replace table-based activity logs with visual timeline
- [ ] Implement filtering by date and activity type
- [ ] Create standard tab set:
  - [ ] Summary Tab: KPIs, recent activity, alerts
  - [ ] Financial History Tab: Exposure snapshots, payment history, DPD progression
  - [ ] Collection Activities Tab: Call/visit logs, letters, promise-to-pay tracking
  - [ ] Legal Tab: Demand letters, case filings, court dates
  - [ ] Documents Tab: Upload, view, and organize documents

### Phase 4: Inline Editing & Enhanced Forms (Priority: MEDIUM)
**Goal**: Implement faster editing workflows

#### Features
- [ ] Create display and form card components (`partials/_card_display.html`, `partials/_card_form.html`)
- [ ] Implement HTMX-based inline editing (display ↔ form swap)
- [ ] Add validation feedback directly in forms
- [ ] Implement vertical forms with labels above inputs
- [ ] Add consistent button placement (Save primary, Cancel secondary)
- [ ] Add confirmation dialogs for high-risk changes

### Phase 5: Advanced Filtering & Search (Priority: MEDIUM)
**Goal**: Improve data discovery and navigation

#### Features
- [ ] Enhance global search to include: Borrower name, Loan ID, Case number, Document tags
- [ ] Add search results display with relevant entity types
- [ ] Add date range filters to timeline views
- [ ] Implement status-based filtering for lists
- [ ] Add "Recent first" default sorting with expandable history

### Phase 6: Visual Design Polish (Priority: LOW)
**Goal**: Implement the visual design system consistently

#### Features
- [ ] Implement color-coded classification badges (Current, Especially Mentioned, Substandard, Doubtful, Loss)
- [ ] Add status badges to sticky context headers
- [ ] Create template helper for consistent badge display
- [ ] Add mini design system CSS (colors, typography, spacing)
- [ ] Implement consistent card styling
- [ ] Add timeline and table styling improvements

## Success Metrics

### User Experience Goals
- Users can identify account in <1 second (sticky context headers)
- Decision-making happens without scrolling (decision-first layout)
- Reduced navigation confusion (consistent workspace pattern)
- Faster task completion (inline editing, better workflows)

### Technical Implementation Strategy
- Progressive Enhancement: Build on existing Django views and templates
- Component-Based: Create reusable partial templates for consistency
- HTMX for UX: Use HTMX for dynamic updates without full page reloads
- Server-Side First: Keep pagination, sorting, and filtering on the server

## Implementation Order
1. **Phase 1** - ✅ COMPLETED: Foundation changes affect all pages
2. **Phase 2** - Next: Immediate value to users
3. **Phase 3** - Core functionality improvement
4. **Phase 4** - Nice-to-have enhancements
5. **Phase 5** - Advanced features
6. **Phase 6** - Visual polish

---

## Phase 1 Completion Summary ✅

### What Was Accomplished:
Phase 1 successfully implemented the foundational 3-zone layout pattern that will support all future development. The core infrastructure is now in place:

1. **Layout Architecture**: Implemented the 3-zone layout (topbar, sticky context header, scrollable work area) that provides consistent structure across all pages.

2. **Navigation Enhancement**: Enhanced navigation with proper icons, global search, quick create dropdown, and user-friendly menus.

3. **Component System**: Created reusable partial templates for breadcrumbs, status badges, context headers, decision cards, and risk panels.

4. **Search Infrastructure**: Implemented global search that works across entity types (borrowers, loan accounts) with proper highlighting and categorization.

5. **Visual Design**: Added comprehensive CSS for sticky headers, color-coded status badges, decision cards, and responsive layout.

6. **Template Enhancement**: Updated all core views to provide proper breadcrumb context and entity type information.

### Technical Benefits:
- **Consistent User Experience**: All pages now follow the same layout pattern
- **Scalable Architecture**: New pages can easily adopt the workspace pattern
- **Component Reusability**: Partial templates can be reused across different entity types
- **Responsive Design**: Layout works properly on different screen sizes
- **Performance**: Server-side pagination and filtering maintained

### Ready for Next Phase:
The foundation is now solid and ready for Phase 2 (Enhanced Dashboard & KPIs). The layout system will support more advanced features like decision cards, inline editing, and enhanced workspace patterns.