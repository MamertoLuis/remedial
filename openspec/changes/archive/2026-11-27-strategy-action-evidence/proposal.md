# Proposal

## Why

Strategy actions function as a to-do checklist for a remedial strategy, but nothing ties a strategy action to the collection activity that carried it out — the proof of execution lives in the collection activity diary, which is otherwise unrelated to the action ledger. Officers therefore double-enter or lose the linkage between "the plan said call" and "the call was made" (and can only do so in two unlinked places). Collection activities must be optionally relatable to the strategy action they fulfill, while remaining usable for accounts with no strategy at all (for example an account one payment behind).

## What Changes

- **Model** Add an optional `action` foreign key on `CollectionActivityLog` to `StrategyAction`: a diary entry may cite the strategy action it fulfills (at most one action per activity; any number of activities may evidence one action). The link is nullable, so pre-strategy collection work is unaffected.
- **Integrity rule** Only actions from the **same account's ACTIVE strategy** are linkable: the account of the activity must equal the account of the action's strategy, enforced when creating or editing an activity.
- **Pure evidence** Linking an activity is informational — it does not change the action's status machine; execution remains an explicit officer action.
- **One-step convenience** The action execute flow gains a "log activity + mark executed" path that creates the collection activity, links it to the action as evidence, and executes the action in one save.
- **Tests** Regression tests for the link, the same-account rule, and the one-step execute path.

## Capabilities

### New Capabilities

(empty)

### Modified Capabilities

- `strategy-actions`: adds the evidence relationship between tracked strategy actions and collection activities (optional activity-to-action link with same-account enforcement, plus the log-and-execute convenience path).

## Impact

- `account_master/models.py` — nullable `action` FK on `CollectionActivityLog` (+ migration).
- `account_master/forms.py` / `account_master/services/` — link field and same-account validation; one-step log-and-execute service path.
- `account_master/views/remedial_strategy.py` / `collection_activity.py` and templates — activity link control and the execute-side convenience.
- `account_master/tests_*` — new and updated tests covering the link, the rule, and the convenience.
- No change to the strategy lifecycle, approval workflow, or escalation ladder; `strategy-assessment` snapshot text is unaffected.
