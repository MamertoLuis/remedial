# Design

## Context

Seeding a demo host currently needs seven manual commands whose slices disagree: `load_dummy_exposure` writes zero-DPD exposures through direct model writes (no auto-delinquency), `load_dummy_delinquency` writes random snapshots on dates that miss the exposure dates so the post-save ECL signal finds no exposure, and account status is hardcoded, so NPL/ECL/ladder state never coheres with the exposure story. The derivation cascade (exposure → delinquency → status → ladder → ECL) already exists in the services; the csv-import work added `source` provenance for every exposure/delinquency row. `start_escalation` opens a PENDING ladder at stage 1; sentinel principals 1.00/0.00 produce WRITEOFF/CLOSED. See `proposal.md - Why`; the `demo-data` delta in `specs/demo-data/spec.md` is the behavior contract.

## Goals / Non-Goals

**Goals:**
- One `seed_demo` command builds a complete fake demo database, idempotently.
- Timeline state is produced through the normal cascade so status, ECL, and ladders are coherent with the exposure story.
- Deterministic demo users across all four roles; optional `--seed` for reproducible data.
- A hard organic-data boundary: the command refuses on DBs carrying non-demo exposures/delinquency.

**Non-Goals:**
- No changes to existing domain specs, services, or the csv-import contract.
- No schema changes or new dependencies.
- Not a production/bootstrap path: it never runs on real-data hosts and never touches iAccs or CSV imports.
- The existing ad-hoc dummy loaders stay untouched and usable independently.

## Decisions

**D1 — Composition, not duplication.** `seed_demo` is a thin orchestrator: (1) seed users, (2) `call_command("load_dummy_data")` for the ACC001–ACC010 foundation, (3) run the timeline engine over those accounts, (4) `call_command` the three enrichment loaders (collection activities, remedial strategies, compromise), (5) create one approved litigation entry for the litigation arc. The enrichment loaders keep working ad hoc.

**D2 — Timeline through the cascade.** Each account's arc is a designed DPD series over ~16 weekly snapshots ending today; snapshots are written in date order via `upsert_exposure` → `_auto_create_delinquency_status` → `_update_loan_account_status` → `sync_escalation_on_snapshot` → post-save ECL. The cascade overwrites `load_dummy_data`'s hardcoded statuses, so the last snapshot owns each account's displayed state. Arcs: performing (DPD 0), deteriorating (0→30→70→95→120, NPL at 91, Stage-2→3 ECL), cured (0→60→0, ladder closed with reason cured), chronic NPL (30→180+ plateau), written-off (final principal 1.00 sentinel → WRITEOFF), litigation (approved entry via `litigation_service`, so the strategy gate is satisfied). Alternative rejected: writing Exposure/DelinquencyStatus tables in parallel (today's behavior — incoherent demo).

**D3 — Deterministic users, seeded data.** Users: `demo-officer` (ACCOUNT_OFFICER), `demo-manager` (MANAGER), `demo-board` (BOARD_MEMBER), plus existing `admin` (SYSTEM_ADMINISTRATOR, created by `start_db.sh`); `is_staff` only for the administrator, per the role invariant. Passwords are documented in the README. `--seed N` builds a `random.Random(N)` used by the timeline AND re-seeds the global PRNG before the enrichment loaders, so a seeded run reproduces the whole database; without `--seed`, random jitter differs per run (open-play variety). Alternative considered: fully hardcoded tables — rejected because open play values variety.

**D4 — Organic-data guard.** `seed_demo` refuses (writes nothing, non-zero) when `Exposure` or `DelinquencyStatus` rows exist for accounts outside the demo set (ACC001–ACC010), which covers both iAccs-sourced rows and CSV-host imports regardless of provenance tag. Re-runs replace only the demo set: snapshots for demo accounts are deleted first, enrichment loaders already delete-and-recreate their slices, and demo users are `get_or_create` (passwords reset). `load_dummy_compromise` deletes all agreements globally — acceptable here since the command never runs on real data.

**D5 — Ordered, bounded writes.** ~16 snapshots × 10 accounts ≈ 160 exposure rows plus derived rows — a bounded, low-resource dataset by design. The timeline loop runs per account; no job queues or background workers.

## Risks / Trade-offs

- **[Open-play randomness vs reproducible walks]** → `--seed` pins timeline + enrichment values; without it, variety. Documented so a rehearsed walk uses `--seed`.
- **[Refusal guard cannot detect CSV-written rows on demo accounts themselves]** → The guard keys on accounts outside the demo set; someone deliberately running real imports onto ACC001–ACC010 is outside the threat model — the README states real imports never run on demo hosts.
- **[Reusing load_dummy_compromise's global delete]** → Safe only because the guard ensures the DB is demo-only; the command order (guard before writes) enforces that.
- **[ECL signal swallows errors]** → Not a risk here: every delinquency snapshot's date has a matching exposure by construction (both are written by the same upsert).
- **[Demo diverges from production behavior of loaders]** → The enrichment loaders are unchanged; only their orchestration and the timeline are new.

## Migration Plan

No schema or dependency changes. Rollback: revert the feature commits; nothing persists beyond the demo database itself.

## Open Questions

None — the open items (open play vs rehearsal, determinism, guard scope, user roles) were resolved during exploration and are recorded above.