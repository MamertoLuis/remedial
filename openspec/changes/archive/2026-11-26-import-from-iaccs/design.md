# Design

## Context

Data reaches the remedial app today only through CSV files that operators generate and push by hand, then apply with `manage.py import_*`. The authoritative data lives in the iAccs core-banking MySQL database, and a separate analysis repo (`URBD_Financial_Analytics`, `scripts/loan_data.py`) already contains validated extraction semantics: the five-part loan key, the aggregate-shortfall days-past-due rule, collection element codes, and the confirmed data conventions (documented in `references/loan-source-to-target-mapping.md`). See `proposal.md` — Why for motivation.

Live verification of source data (read-only queries against `iaccsuplandruralbank01`, MySQL 5.6):
- Single branch (`LoanBR_CODE = 1`), 9,141 loans; `LoanSLT_CODE` in 1..21 (12 in use).
- `LoanREF_NO` and `ClientIDLoan` are `mediumint(8)` but currently ≤ 4 digits each.
- Rendering `{BR:02d}-12-{SLT:02d}-{REF}-{CLIENTID}` therefore maxes at 18 chars — fits `LoanAccount.loan_id` (`max_length=20`, PK) with no migration.
- `client.ClientID` ≤ 4 digits (6,263 clients); borrower identity key is `(ClientIDBrCode, ClientID)`.

## Goals / Non-Goals

**Goals:**
- On-demand, single-hop refresh: read iAccs MySQL read-only, upsert `Borrower` / `LoanAccount` / `Exposure` through the existing service layer so the existing derivation cascade (`DelinquencyStatus` → `LoanAccount.status` → rule-based ECL) fires unchanged.
- Canonical identity: loan 5-key → `loan_id`, client key → `borrower_id`.
- Feed only schedule-based DPD; classification stays app-derived (decision 2a); ECL stays rule-based (no bank-allowance parity).

**Non-Goals:**
- Scheduled refresh / automation (future `iaccs-sync` work).
- Ingesting authoritative `cts_type` classification or PFRS9 stage from the source.
- Matching the bank-booked allowance (`LoanProvisionAMT`).
- Removing or changing the existing CSV import commands.
- DB migrations (not expected; confirm during implementation).
- Any writes to the iAccs MySQL database.

## Decisions

### D1. Single-hop Django management command (not a two-hop extract-then-load)

`manage.py import_from_iaccs` connects to iAccs MySQL and writes directly through the Django service functions, in one process.

- Why: removes the intermediate file (the root cause of staleness); the write path is byte-identical to the CSV path, so the cascade keeps its guarantees.
- Alternatives considered: (a) keep `loan_data.py` as a separate extractor writing a fresh CSV, then import it — rejected: reintroduces the file step and a second tool to operate; (b) a standalone ETL service — rejected: overkill for an on-demand refresh.

### D2. Identity mapping from the source (CSV mapping dropped)

- `loan_id = f"{BR_CODE:02d}-12-{SLT_CODE:02d}-{REF_NO}-{CLIENTID}"` — the canonical 5-key render already used by `loan_data.py`.
- `borrower_id = str(client.ClientID)` today; queries are always scoped by `ClientIDBrCode`, and the render can be widened (`{br}-{client}`) when multiple branches appear without breaking key length (2-digit branch + 1 + 8-digit client fits 20).
- Why: MySQL is the agreed source of truth for identity; the CSV ids (`0000002301-0002605-3`) cannot be joined to the source.
- Note: `REF_NO` alone is not unique — the full 5-key (incl. `SLT_CODE` and `CLIENTID`) is the identity, matching iAccs.

### D3. Extraction logic lives in the Django project

The loader reimplements the validated computations (outstanding from `SUM(sldtl.AMT)` on `SLE_CODE=11`, aggregate-shortfall DPD from `amortsched`, collections elements {10,12,15}, `SLC=12` filter) inside `account_master` (e.g. `services/iaccs/loader.py`, `mapper.py`), with a docstring/comment pointing at `URBD_Financial_Analytics/references/loan-source-to-target-mapping.md` as the shared source of conventions.

- Why: the remedial app must be independently runnable/deployable; pulling in the URBD package couples two repositories with different lifecycles.
- Alternatives considered: importing the URBD package as a dependency — rejected (repo coupling, heavy analysis tooling in the app); copying `mysql56.py`/`loan_data.py` wholesale — the connection helper's env-based pattern is reused as a reference, not vendored.
- Trade-off: two implementations of the same conventions. Mitigated by unit tests mirroring the URBD-verified numbers (e.g. 0 negative-total accounts) and the mapping doc as the canonical reference.

### D4. DPD contract: aggregate-shortfall, no deferral offset

DPD = walk `amortsched` installments in due-date order, accumulate scheduled principal due; the oldest installment whose cumulative due exceeds total principal repaid gives the DPD anchor: `max(0, (cutoff - due_date).days)`; 0 when no installment is uncovered or the anchor date > cutoff. No `defer_days` offset — `deferdate` stores no duration (confirmed in the mapping doc). The loader writes this DPD into `Exposure.days_past_due`; Django's classification/status/ECL derivation takes over.

### D5. Read-only MySQL handling

`pymysql` with `charset=utf8mb4` and `DictCursor`, settings from environment `MYSQL56_HOST/PORT/USER/PASS/DB` (the same convention as `mysql56.py`), loaded from `.env` if present. All SQL is `SELECT`; no transactions, no writes, and the connection is closed after the run. Connection failure aborts before any Django write.

### D6. Write path reuses the existing service cascade

Per loan: `upsert_borrower` → `upsert_loan_account` → `upsert_exposure(account, cutoff, {principal_outstanding, …, days_past_due})`. `upsert_exposure` already auto-creates the `DelinquencyStatus` and its `post_save` handler recomputes `LoanAccount.status` and rule-based ECL provision. Loan master fields map from source columns per the mapping doc (`LoanTR_DATE` release, `LoanMAT_DATE`, `LoanPAMT`, `LoanINT_RATE`, `sltype` product description, `cts_type` kept out of the cascade per decision 2a).

### D7. Command contract and error semantics

- Required `--cutoff YYYY-MM-DD`; optional `--branch`; `--dry-run` preview.
- Per-loan `transaction.atomic()`; failures are collected, reported, and the command exits non-zero with any failure — matching the CSV commands' isolation semantics (see `specs/iaccs-sync/spec.md`).
- Dry-run performs no writes.

## Risks / Trade-offs

- [Duplicated extraction semantics across the remedial repo and URBD repo] → mapping doc remains the single source of conventions; loader tests mirror verified URBD numbers; code points back to the reference.
- [Schedule-based DPD re-segments loans differently than the CSV-era stored `days_past_due`] → classification is derived from whichever DPD lands; document the semantic shift (stored value → computed value) in the command help and migration notes; verification step compares a sample against `loan_data.py` output.
- [Existing cascade can silently skip ECL when exposure/ delinquency as-of dates mismatch] → the loader keys both by the same cutoff, and tests assert an ECL record exists after import rather than trusting the signal alone.
- [post_save signal swallows provisioning errors] → loader tests directly assert `ECLProvisionHistory` rows and status transitions for imported accounts.
- [Multi-branch growth outgrows `loan_id` `max_length=20`] → monitored via a tests/verification step asserting max rendered key length ≤ 20 per branch; widening the PK is intentionally out of scope until needed.
- [`pymysql` added to the Django dependency set] → pure-Python, no build risk; only the app's `pyproject.toml` changes.
- [Live comparison vs the URBD extractor at 2025-06-30] → balances agree on all 9,141 loans; DPD differs on 617 loans, all with outstanding == 0, because the reference extractor's `HAVING SUM(...) <> 0` drops settled loans from aggregates and then reports an inflated schedule DPD. The loader deliberately omits the HAVING clause so settled loans report DPD 0; documented in `loader.py`.

## Migration Plan

Additive change: add `pymysql` dependency, ship the command and tests. No data migration. Rollback = remove the command/dependency and do not run it; existing CSV pipeline is unaffected. Production note: the iAccs DB is reachable only on the analytics host (port 32768) — the command must run where `MYSQL56_*` resolves, not on a generic app host.

## Open Questions

- Exact `LoanAccount` master-field mapping for optional columns (`loan_security`, borrower `borrower_group`, etc.): follow `loan-source-to-target-mapping.md`; immaterial to the behavior contract, resolved during implementation.
- Default for `--branch` (currently all branches, i.e. branch 1): harmless to change later; recorded as an assumption in tasks.
