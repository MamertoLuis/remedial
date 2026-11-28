# Tasks

## 1. Service layer

- [x] 1.1 Implement `services/demo_seed.py` user seeding: create-or-reset `demo-officer` (ACCOUNT_OFFICER), `demo-manager` (MANAGER), `demo-board` (BOARD_MEMBER) with documented deterministic passwords, `is_staff` only for the administrator; verify a test asserts roles and that staff flags match the role invariant
- [x] 1.2 Implement the arc definitions (performing, deteriorating, cured, chronic NPL, written-off, litigation) with a bounded ~16-week DPD series per account; verify tests assert every arc's derived status/classification from its final snapshot
- [x] 1.3 Implement the timeline writer that upserts snapshots in date order through `upsert_exposure` (including the 1.00 sentinel for written-off and the litigation entry via `litigation_service`); verify tests assert the cascade consequences — NPL status at >90 DPD, ladder opened then cured, ECL provisions exist at each snapshot date
- [x] 1.4 Wire `--seed` determinism: a `random.Random(seed)` drives the timeline jitter and re-seeds the global PRNG before enrichment loaders; verify two seeded runs produce identical snapshot values

## 2. Command

- [x] 2.1 Implement `seed_demo` command wiring users → `load_dummy_data` → timeline → enrichment loaders (`load_dummy_collection_activities`, `load_dummy_remedial_strategies`, `load_dummy_compromise`) → litigation entry; verify a run against a fresh test DB leaves users, accounts, snapshots, ECL rows, ladder states, strategies, activities, and one approved litigation entry
- [x] 2.2 Implement the organic-data guard: refuse with a clear message and write nothing when Exposure or DelinquencyStatus rows exist for accounts outside the demo set (ACC001–ACC010); verify a test seeds an IACCS-tagged row on another account and asserts refusal and zero writes
- [x] 2.3 Make re-runs idempotent: delete demo-account snapshots before re-seeding and reset demo-user passwords; verify a second run replaces without accumulating duplicates or new accounts

## 3. Documentation

- [x] 3.1 Add a README demo section: the `seed_demo` one-liner, the login table (admin/demo-officer/demo-manager/demo-board), the `--seed` option, and the guardrail that real imports never run on a demo host; verify the documented one-liner runs against a fresh database
- [x] 3.2 Add the same fake-only guardrail note to `loader.sh`; verify the note is visible in the script

## 4. Integration

- [x] 4.1 Add seed tests to the suite (cascade consequences, guard, idempotency, `--seed` reproducibility) and run `make audit`; verify the full suite passes alongside the new seed tests

## Workflow follow-up

- Archive the change after review requirements are satisfied.
- Verify the archived result.