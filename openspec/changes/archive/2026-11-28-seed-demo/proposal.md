# Proposal

## Why

A cloud-hosted instance will be run as an open-play demo for users, so it must be seeded with fake, low-resource data. Today seeding is a manual seven-command sequence whose slices disagree with each other: exposures carry zero days past due, delinquency snapshots use dates that miss the exposure dates (so ECL history stays sparse), account status is hardcoded instead of derived, escalation ladders never start, and no role users exist to exercise officer/manager/board screens.

## What Changes

- Add a single `seed_demo` management command that provisions a complete fake demo database on a fresh install: role users, a foundational portfolio, and coherent account timelines.
- Timeline state is written **through the normal derivation cascade** (`upsert_exposure` → auto delinquency → account-status re-derivation → escalation ladder → post-save ECL), in date order, so the demo shows the domain actually working: accounts cross DPD 91 and become NPL, ladders open and cure, ECL tiers move.
- Each account follows a designed narrative arc (performing, deteriorating, cured, chronic NPL, written off, litigation-won) so the portfolio has texture for open play.
- Seed deterministic demo users for the four real roles (`demo-officer`, `demo-manager`, `demo-board`, plus existing `admin`), with documented credentials, so role-gated areas (approval queue, litigation decision, reports) are demonstrable.
- Idempotent re-runs (replaces only its own artifacts) and an optional `--seed` for reproducible walks.
- Demo/organic boundary guardrail: `seed_demo` refuses to run when iAccs-sourced rows exist, and the README states that real imports (`import_from_iaccs`, CSV imports) never run on a demo host — the demo database is fake-only.

## Capabilities

### New Capabilities
- `demo-data`: The durable contract for demo provisioning — a single command that builds a bounded, fake, coherent portfolio through the normal cascade, seeds role users, and guarantees the demo database never mixes in real-sourced data.

### Modified Capabilities
- (none — this is a new provisioning capability; existing domain specs are unchanged)

## Impact

- **Code**: new `account_master/management/commands/seed_demo.py`; new `account_master/services/demo_seed.py` (arc definitions, timeline writer, user seeding); reuse of existing `load_dummy_data`, `load_dummy_collection_activities`, `load_dummy_remedial_strategies`, `load_dummy_compromise` loaders; one approved litigation entry through `litigation_service` for the litigation arc.
- **Tests**: new seed tests asserting cascade consequences (status, ECL, escalation) and the refuse-on-iAccs guard.
- **Docs**: README demo section with the one-liner, the login table, and the fake-only guardrail; `loader.sh` note.
- **Systems**: no schema changes; SQLite/Postgres agnostic; no new dependencies.