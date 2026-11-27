# Tasks

## 1. Provenance foundation

- [x] 1.1 Add a `source` field with choices `IACCS`/`CSV` to `Exposure` and `DelinquencyStatus`, with a migration backfilling existing rows as `CSV`; verify `migrate` succeeds and pre-existing rows read `CSV`
- [x] 1.2 Tag `IACCS` on rows written by the iaccs loader and `CSV` on every other writer (CSV commands, dummy loaders); verify with a test that an iaccs-imported exposure is tagged `IACCS` and a CSV-written one `CSV`

## 2. Shared contract module

- [x] 2.1 Extract the aggregate-shortfall days-past-due computation from `services/iaccs/loader.py` into a reusable helper the loader and the CSV path share; verify the loader tests still pass and both paths produce identical DPD given the same schedule
- [x] 2.2 Implement contract validation primitives in `services/csv_import/` — exact-header allow-lists, ISO-only date parsing, strict decimal and choice parsing (no coercion), within-file uniqueness — with unit tests covering each rejection
- [x] 2.3 Implement the two-phase write orchestration: validate every row (types, referential integrity, provenance conflicts) before any write, then commit all rows in a single transaction; verify a test in which one invalid row writes nothing and exits non-zero, and a clean file writes every row

## 3. Command rewrites

- [x] 3.1 Rewrite `import_borrowers` onto the contract module (strict recognized `borrower_type`, no PERSON fallback, `--dry-run`, `--skip-existing`); verify tests reject an unrecognized borrower type and import a clean file idempotently
- [x] 3.2 Rewrite `import_accounts` onto the module (reject a `status` column; `loan_security` required and validated); verify tests reject a legacy file with a `status` column and accept a compliant one
- [x] 3.3 Rewrite `import_exposures` onto the module (reject a `days_past_due` column; DPD computed from the iAccs schedule; reject rows colliding with `IACCS`-tagged same-date records); verify tests for legacy-column rejection, provenance-conflict rejection, and CSV-tagged correction allowed
- [x] 3.4 Delete `load_delinquency_csv.py`; verify the command is no longer registered (`manage.py help` output) and no code imports it

## 4. Reference data and documentation

- [x] 4.1 Update `sample_exposures.csv`, the README common-commands section, and `loader.sh` to the new contract (no `days_past_due`/`status` columns); verify the documented commands run against the updated sample

## 5. Integration

- [x] 5.1 Rewrite `tests_commands_import.py` around the contract (two-phase rejection, provenance conflicts, legacy-column rejection, idempotent re-run, dry-run) and run `make audit`; verify the full suite passes alongside the rewritten import tests

## Workflow follow-up

- Archive the change after review requirements are satisfied.
- Verify the archived result.