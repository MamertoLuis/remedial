# Proposal

## Why

The remedial app currently receives data only through manually generated CSV files that operators push by hand (download the file, then run `manage.py import_*`). That couples two manual points to every refresh, so loan status and ECL provisioning are only as fresh as the last file someone pulled — data lands stale. The iAccs core-banking MySQL database is the authoritative source for loan identity, balances, and delinquency; connecting to it directly removes the intermediate file and makes refresh on-demand and trustworthy.

## What Changes

- Add a single-hop `import_from_iaccs` Django management command that connects **read-only** to the iAccs core-banking MySQL and upserts `Borrower`, `LoanAccount`, and `Exposure` rows through the existing service layer (`upsert_borrower` / `upsert_loan_account` / `upsert_exposure`), so the existing derivation cascade (`DelinquencyStatus` → `LoanAccount.status` → rule-based ECL provisioning) runs unchanged.
- Establish the **iAccs 5-key loan key** (`BR_CODE, SLC_CODE=12, SLT_CODE, REF_NO, CLIENTID`) as the source of truth for loan identity, replacing the ad-hoc id shapes seen in the CSV pipeline. Borrower identity comes from the `client` key (`ClientIDBrCode`, `ClientID`).
- Ingest **DPD computed by the aggregate-shortfall schedule method** (walk `amortsched` installments vs. principal repaid, per the confirmed rule in the URBD scripts analysis) into `Exposure.days_past_due`. Classification and account status remain derived by the app's existing rules.
- Keep ECL provisioning rule-based (Django's IFRS-9 tiering). Bank-booked allowance (`LoanProvisionAMT`) is explicitly **not** matched.
- No changes to the existing CSV import commands; the new path is additive.

## Capabilities

### New Capabilities

- `iaccs-sync`: Synchronizes the remedial portfolio with the iAccs core-banking source. Owns the canonical identity mapping (loan 5-key → `loan_id`, client key → `borrower_id`), point-in-time exposure/delinquency ingestion, and the single-hop import command contract. Future automation (scheduled refresh) extends this capability.

### Modified Capabilities

- None. Existing specs inventory is empty and no current behavior's requirements change.

## Impact

- `account_master`: new management command (`import_from_iaccs`), new mapping/extraction module (identity + DPD computation), MySQL connection settings via environment (`MYSQL56_*` convention).
- Dependency: add `pymysql` to the Django project (`pyproject.toml`) — currently only a dependency of the separate URBD scripts repo.
- MySQL access is read-only (`SELECT` only); all writes stay in the Django database.
- No DB migrations expected (`loan_id` canonical form ≤ 18 chars fits the existing `max_length=20`; verified against live data — see design). Confirmed during implementation.
- Existing CSV pipeline, alerting, reporting, and the ECL cascade are unaffected.
