# Proposal

## Why

An account officer can raise a litigation entry (pending manager approval), but a manager has no way to discover or act on it in the UI. The litigation entry queue and decision screens exist as standalone routes, yet nothing links to them: the manager-only `approval_queue` page lists only strategy-*action* approvals, the sidebar has no approvals entry, and the litigation queue is otherwise unreachable. A raised entry sits PENDING_APPROVAL with no manager surface, so the Legal Action / Foreclosure gate stays blocked. This change makes the existing manager approval queue the hub that surfaces pending litigation entries with inline approve/reject.

## What Changes

- Extend the manager `approval_queue` page with a **segmented toggle** — "Strategy Approvals" and "Litigation Entries" — so the two decision queues share one manager hub.
- Surface pending account-level litigation entries on the **Litigation Entries** tab with **inline approve/reject** (reusing the existing `approve_litigation_entry` / `reject_litigation_entry` service functions), instead of requiring the manager to reach a separate page.
- Cross-link the standalone litigation queue/decision screens back to the hub so both entry paths converge; the existing standalone screens remain reachable as deep links.
- Keep the existing `_check_entry_gates` and approval semantics unchanged.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `litigation-entry`: the manager approval behavior changes so that pending litigation entries are surfaced and decidable inline from the manager approval queue, rather than only through a standalone, unlinked queue.

## Impact

- `account_master/views/remedial_strategy.py`: `approval_queue` view passes pending litigation entries alongside pending actions.
- `account_master/templates/account_master/approval_queue.html`: segmented toggle + Litigation Entries tab with an inline decide form.
- `account_master/views/litigation.py` and `litigation_entry_queue`/`decide_litigation_entry` templates: cross-link to the approval hub; optionally a thin redirect so the hub remains the canonical decision surface.
- Reuse `account_master/services/litigation_service.py` (`get_pending_entries`, `approve_litigation_entry`, `reject_litigation_entry`); no model change.
- Tests: extend `tests_litigation_entry.py` navigation/decision cases.