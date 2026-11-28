# Proposal

## Why

The four CSV import commands (`import_borrowers`, `import_accounts`, `import_exposures`, `load_delinquency_csv`) are the admin path for correcting and backfilling loan data, but no spec governs them. They trust file-supplied `days_past_due`, `classification`, `status`, and `npl_flag` values, letting a CSV contradict the derivation engine that the iaccs import treats as authoritative — a file can silently reclassify an account, flip NPL/account status, drive ECL rates and the escalation ladder off file data, and partially write rows before failing.

## What Changes

- Specify a single CSV-import contract (`csv-import`): the file supplies observations and master data; classification, aging bucket, NPL, account status, ECL, and escalation always derive from computed days past due.
- **BREAKING** `import_exposures` rejects a `days_past_due` column; days past due is computed by the aggregate-shortfall rule, exactly as the iaccs loader does.
- **BREAKING** `import_accounts` rejects a `status` column; account status is derived, never file-written. `loan_security` becomes required and validated (no silent `UNSECURED` default).
- **BREAKING** `load_delinquency_csv` is retired: `classification`, `aging_bucket`, `npl_flag`, `npl_date` are never accepted from a file.
- Two-phase validation: the whole file (headers, types, referential integrity, within-file duplicates, provenance conflicts) is validated before any row is written; any invalid row rejects the file with nothing written and a non-zero exit.
- CSV files SHALL NOT modify exposure/delinquency records tagged as iaccs-written for the same account and as-of date; a `source` provenance field (`IACCS`/`CSV`) on `Exposure` and `DelinquencyStatus` distinguishes writers.
- Forbidden silent coercion: unknown `borrower_type`, unparseable dates, and invalid decimals fail their row rather than defaulting.
- One date format: ISO `YYYY-MM-DD` only; ambiguous slash formats and Excel serial dates are rejected.
- Within-file duplicate natural keys reject the file; re-importing an identical file changes nothing; `--dry-run` reports without writing; exit 0 means fully applied.
- **BREAKING** migration: old-style files are rejected with clear column-level messages on day one (hard break, no compat flag); `sample_exposures.csv`, README, and `loader.sh` are updated in this change.
- Access posture is unchanged: any user with shell access may run the commands.

## Capabilities

### New Capabilities
- `csv-import`: The durable contract for admin CSV ingestion — what a file may and may not carry, how it is validated and written (all-or-nothing, two-phase), which rows it may modify (provenance), and the outcome guarantees (exit codes, idempotency).

### Modified Capabilities
- (none — `iaccs-sync` and `account-upsert` keep their requirements; this change aligns the CSV path to the same derivation authority `iaccs-sync` already declares)

## Impact

- **Code**: `account_master/management/commands/import_borrowers.py`, `import_accounts.py`, `import_exposures.py`; deletion of `load_delinquency_csv.py`; `account_master/models.py` (`source` provenance fields + migration); `account_master/services/` (CSV paths call the shared upsert/derivation services; iaccs loader sets `IACCS` provenance); shared date/type validation helpers.
- **Tests**: `tests_commands_import.py` rewritten around the contract; new coverage for two-phase rejection, provenance conflicts, coercion rejection, and the deleted command.
- **Reference data**: `sample_exposures.csv` (drop `days_past_due`), README common-commands section, `loader.sh` commented examples.
- **Systems**: no dependency or runtime changes; Django data models acquire two columns plus a migration.