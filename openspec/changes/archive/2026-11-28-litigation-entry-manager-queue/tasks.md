# Tasks

## 1. Hub view and data

- [x] 1.1 Update the `approval_queue` view (`account_master/views/remedial_strategy.py`) to also pass `pending_entries` (from `litigation_service.get_pending_entries`, select_related account/raised_by) and a `tab` value read from `request.GET` (default `strategy`, `litigation` otherwise); verify the view renders both `pending_actions` and `pending_entries` in its context.

## 2. Hub template with tabs and inline decide

- [x] 2.1 Add a segmented toggle to `approval_queue.html` with "Strategy Approvals" and "Litigation Entries" tabs, the active tab driven by the `?tab=` value, each tab linking to the same approval queue with the right query param; verify both tab links render and the strategy tab is the default.
- [x] 2.2 Render pending litigation entries under the Litigation Entries tab (account, borrower, strategy type, start date, raised by/at) with the shared table/status-chip components and an empty state when there are none; verify the tab lists pending entries.
- [x] 2.3 Add an inline Approve/Reject form per entry on the tab posting to the existing `decide_litigation_entry` route with a `decision_notes` field and `APPROVE`/`REJECT` decision buttons; verify a manager POST approves or rejects the entry and returns to the approval queue.

## 3. Cross-links and redirects

- [x] 3.1 Change `decide_litigation_entry` success/error redirects to point to `approval_queue` (retaining `?tab=litigation` for error returns) so inline and standalone decisions converge on the hub; verify decide POST redirects to the approval queue.
- [x] 3.2 Update the `litigation_entry_queue` header "Back to Approval Queue" link to `approval_queue?tab=litigation`; verify the link carries the litigation tab.

## 4. Tests

- [x] 4.1 Add tests in `tests_litigation_entry.py` covering: the approval queue renders a pending litigation entry, inline approve transitions to APPROVED, inline reject transitions to REJECTED, the `?tab=litigation` deep link returns to the litigation tab, and the default tab remains strategy; verify these pass alongside existing tests.

## 5. Integration

- [x] 5.1 Run the full account_master test suite and `make audit` and verify all existing approval/strategy/escalation tests still pass alongside the new litigation-queue tests.