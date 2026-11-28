# Design

## Context

The repo has two ingestion engines today: the spec'd iaccs loader (`services/iaccs/loader.py`), which upserts through the service layer and computes days past due from the iAccs `amortsched` schedule, and four ungoverned CSV commands that trust file-supplied DPD/classification/status, write per-row transactions with partial writes on failure, and drift from the service layer (`import_exposures` writes ORM directly). There is no local repayment-schedule model — the only schedule is `amortsched` in the read-only iAccs MySQL. See `proposal.md - Why` for motivation; the delta spec in `specs/csv-import/spec.md` defines the behavior contract.

## Goals / Non-Goals

**Goals:**
- One contract layer that validates a whole CSV file before any write and commits all-or-nothing.
- CSV path converges on the same services and derivation as the iaccs path; DPD is always computed, never file-supplied.
- Provenance (`source`) distinguishes iaccs-written rows, which CSV may not overwrite same-date.
- Strict, unambiguous parsing: ISO dates, exact headers, no silent coercion, within-file uniqueness.
- Hard-break migration: legacy files rejected with actionable messages on day one.

**Non-Goals:**
- No role-gating or access control changes (any shell user runs imports, as today).
- No changes to `iaccs-sync` or `account-upsert` requirements.
- No three-way provenance: the binary `IACCS`/`CSV` scheme is accepted as a deliberate simplification.
- The ECL post-save signal's error swallowing and the dummy-data dev loaders are out of scope (the loaders simply tag `CSV`).

## Decisions

**D1 — Two-phase validate-then-write.** Phase 1 parses the full file into typed, validated rows (headers, types, referential integrity, within-file uniqueness, provenance conflicts) and collects every error; phase 2 writes all rows in one transaction only when phase 1 is clean. Alternative considered: per-row transactions (today's behavior — rejected for partial writes); fail-fast (today's `import_accounts` — rejected, inconsistent grammar).

**D2 — Shared contract module; commands become thin wrappers.** A new `services/csv_import/` module owns dialect sniffing, header allow-lists, ISO date parsing, type validation, uniqueness/provenance checks, and the write phase calling the existing `upsert_*` services (killing `import_exposures`' direct-ORM drift). Each command keeps its CLI surface (`--dry-run`, `--skip-existing`) but delegates to the module. `load_delinquency_csv` is deleted — nothing it accepted is legal anymore.

**D3 — Provenance field `source` on Exposure and DelinquencyStatus** (choices `IACCS`/`CSV`). The iaccs loader tags `IACCS`; every other writer (CSV commands, app paths, dummy loaders) tags `CSV`, meaning "not iaccs." CSV validation rejects any row that would modify an `IACCS`-tagged record for the same account and as-of date. Legacy rows are backfilled as `CSV` — pre-production data is overwhelmingly CSV/dummy-written, and the iaccs loader remains able to overwrite anything (it is the authority), so the protection is fully effective for new iaccs writes from this change forward. Alternatives: backfill `IACCS` (over-restrictive — freezes legacy rows out of CSV correction); three-valued enum (rejected for simplicity, as the user accepted two values).

**D4 — CSV exposure DPD still comes from the iAccs schedule.** With no local schedule model, the exposure import computes DPD with the same aggregate-shortfall rule against `amortsched` via the existing read-only connection. The loader's DPD computation is extracted into a reusable helper both paths share. Consequences: a CSV exposure import requires iAccs reachability, and fails cleanly in validation when it is unavailable. Alternatives: trust file DPD (rejected — the contract's entire point); carry a schedule in the file (rejected — duplicates iAccs data and invites tampering); derive from prior local snapshots (rejected — reintroduces stale trust).

**D5 — Hard break, no compat flag.** The strict header allow-lists reject legacy `status`/`days_past_due`/`classification`/`npl_flag`/`npl_date` columns with messages naming the column and the fix. `sample_exposures.csv`, README, and `loader.sh` are updated in this change. Alternative: a `--legacy` stripping flag was offered and rejected by decision (the point is to stop trusting file DPD).

**D6 — Strict scalar rules.** Dates: ISO `YYYY-MM-DD` only (no slash formats, no Excel serials). `borrower_type`: the model's recognized choices only — the current normalization mapping (INDIVIDUAL→PERSON, etc.) is removed. Decimals must parse as `Decimal`.

## Risks / Trade-offs

- **[CSV exposure import now needs live iAccs]** → Validation-time error and dry-run report make the requirement explicit; README documents it. This is the honest cost of "no file DPD."
- **[Legacy rows tagged CSV can be overwritten by CSV correction]** → Accepted one-time trade-off, recorded in D3; iaccs remains authoritative over everything.
- **[Existing operator habit breaks (files with old columns fail)]** → Rejection messages name the exact column and fix; sample/README/loader.sh ship updated in the same change; tests encode the contract.
- **[Batch rejection is stricter than today's partial writes]** → Intended per the contract; a failed file leaves zero rows, and dry-run lets operators preview before committing.
- **[Removal of load_delinquency_csv reduces an escape hatch]** → Delinquency data now flows only through exposure imports (derived) or iaccs — the point of the contract.
- **[Two new model columns + migration in the data layer]** → Additive and reversible; ECL signal behavior unchanged.

## Migration Plan

1. Add `source` columns + migration (backfill `CSV`); tag `IACCS` in the iaccs loader and in the new write path.
2. Add `services/csv_import/` contract module; extract the shared DPD helper from the loader.
3. Rewrite the three commands onto the module; delete `load_delinquency_csv.py`.
4. Update `sample_exposures.csv`, README common-commands, and `loader.sh`.
5. Rewrite `tests_commands_import.py` around the contract; add tests for two-phase rejection, provenance conflicts, legacy-column rejection, and idempotent re-runs; run `make audit`.
6. Rollback: revert to the last committed state restores old behavior; the `source` columns are additive and can remain or be removed with the migration.

## Open Questions

None — the open items (legacy backfill value, CSV/iAccs coupling for DPD, hard break, access posture) were resolved with the user during exploration and are recorded above.