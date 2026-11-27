# Design

## Context

Today the manager-only `approval_queue` route (`views/remedial_strategy.py::approval_queue`) renders `approval_queue.html` with pending approval-gated strategy actions and inline approve/reject. Pending account-level litigation entries (from the `litigation-entry` capability) live on a separate, unlinked screen: `litigation_entry_queue` (`views/litigation.py`) lists them and `decide_litigation_entry` handles the decision, redirecting back to `litigation_entry_queue`. A raised entry is therefore invisible to the manager through normal navigation. See proposal.md for motivation and the `litigation-entry` spec delta for the required behavior.

The `ui-workspace` spec constrains the change: every existing URL name, view, template context variable, form field/method/action, and GET/POST parameter must be preserved.

## Goals / Non-Goals

**Goals:**
- Make the manager approval queue the single hub for both approval-gated strategy actions and pending litigation entries.
- Provide inline approve/reject for litigation entries on the hub, reusing the existing service functions.
- Keep every existing route, form field, and parameter working unchanged.

**Non-Goals:**
- Changing litigation-entry approval semantics, the strategy gate, the ActionStatus machine, or the strategy action approval workflow.
- Adding manager notifications/alerts for newly raised entries (deferred).
- Removing the standalone litigation queue/decision screens (kept as deep links).

## Decisions

1. **One hub page with a segmented toggle driven by a query parameter.** The `approval_queue` view keeps serving action approvals and additionally passes `pending_entries`. The template shows a toggle whose active tab is read from `?tab=` (`strategy` default, `litigation` for the litigation queue). A query parameter (not JS state) gives a deep-linkable, no-JS-friendly fallback, consistent with the `ui-workspace` requirement that pages work with and without scripting.
   - Alternative: a JS-only tab abstraction — rejected because it breaks deep-linking and the no-JS contract.

2. **Inline forms post to the existing `decide_litigation_entry` view.** The hub's Litigation Entries tab renders each pending entry with a small Approve/Reject form posting to `decide_litigation_entry` (already `@manager_required` and using `approve_litigation_entry` / `reject_litigation_entry`). We change only that view's success redirect from `litigation_entry_queue` to `approval_queue` so decisions return to the hub.
   - Alternative: duplicate approve/reject dispatch in the `approval_queue` POST handler — rejected; it would duplicate the service dispatch and the AuthenticationGate logic for one screen.

3. **`?tab=litigation` deep link from the litigation queue screens.** The standalone `litigation_entry_queue` header "Back to Approval Queue" link becomes `approval_queue?tab=litigation` so a manager landing there returns to the correct tab.

4. **The strategy-action inline approve/reject block on the hub stays untouched** — only a sibling tab and its forms are added, preserving every existing field and parameter.

## Risks / Trade-offs

- **Tab state diverges from a page reload** → the `?tab=` query parameter drives the active tab so reloads and direct links preserve it; no shared mutable JS state.
- **Form POST target shared by two surfaces** → `decide_litigation_entry` becomes the single POST handler for both inline and standalone; the redirect change is global but harmless because both flows now converge on the hub.
- **Two tabs could hide the other queue's items** → the strategy default tab preserves today's first impression; the toggle makes both visible, and if one queue is empty its tab shows the existing empty-state pattern.

## Open Questions

None.