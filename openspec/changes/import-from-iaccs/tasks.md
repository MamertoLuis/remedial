# Tasks

## 1. Dependency & Scaffolding

- [x] 1.1 Add `pymysql` to `pyproject.toml` dependencies and run `uv sync` — verify `uv run python -c "import pymysql"` succeeds
- [x] 1.2 Create the loader package layout under `account_master/services/iaccs/` (e.g. `connection.py`, `loader.py`, `mapper.py` with module docstrings referencing the URBD mapping doc) — verify `uv run python manage.py check` passes

## 2. MySQL Connection & Read-Only Access

- [x] 2.1 Implement env-based connection settings (`MYSQL56_HOST/PORT/USER/PASS/DB`), `.env` loading, and a `pymysql` connect helper (`DictCursor`, `utf8mb4`) restricted to `SELECT` — verify with a read-only integration query against the running `iaccs-mysql` container (port 32768) returning rows
- [x] 2.2 Fail fast on connection error before any Django write — verify a unit test simulating connection refusal raises a clear `CommandError` and no rows are written

## 3. Identity Mapping

- [x] 3.1 Implement borrower mapping: `client.ClientID` → `borrower_id`, `CLIENTID` link per loan, via `upsert_borrower` — verify unit tests cover create, update-in-place, and reuse across loans (spec: "Borrower identity from the client key")
- [x] 3.2 Implement loan-account mapping: render `loan_id` from the five-part key `{BR:02d}-12-{SLT:02d}-{REF}-{CLIENTID}`, map master fields (`LoanTR_DATE`/`LoanMAT_DATE`/`LoanPAMT`/`LoanINT_RATE`/product description) — verify unit tests cover create and update-in-place (spec: "Canonical loan identity"), and a live-data test asserts max rendered `loan_id` length ≤ 20
- [x] 3.3 Implement the source queries: `loan` join `client`/`sltype`/`cts_type` and `sldtl` per-loan aggregates scoped by branch and `SLC_CODE=12` — verify an integration test returns rows for branch 1 matching the full five-part key (REF alone is not unique)

## 4. Exposure & DPD Ingestion

- [x] 4.1 Compute principal outstanding as `SUM(sldtl.AMT)` over `SLE_CODE=11` per loan key — verify a unit test agrees with the URBD-verified convention (disbursements positive, repayments negative; 0 negative totals for live loans)
- [x] 4.2 Implement aggregate-shortfall DPD from `amortsched` (oldest uncovered installment, `(cutoff - due).days` floored at 0, 0 when covered) — verify unit tests cover the spec scenarios: current loan → 0 DPD, installment due 95 days before cutoff → 95 DPD
- [x] 4.3 Write snapshot exposures via `upsert_exposure(account, cutoff, {…, days_past_due})` — verify a unit test asserts the Exposure row is upserted per (account, as_of_date) (spec: "Point-in-time exposure")

## 5. Cascade Integration

- [x] 5.1 End-to-end import (borrower + account + exposure) triggers delinquency derivation, `LoanAccount.status` update, and rule-based ECL provisioning — verify an integration test imports a 95-DPD loan and asserts status `NPL` plus an `ECLProvisionHistory` row for the cutoff (spec: "Existing derivation cascade runs unchanged")
- [x] 5.2 Confirm the iAccs `cts_type` never overrides the derived classification — verify a unit test imports a loan whose source status differs from the derived classification and asserts the derived classification wins

## 6. Command Contract

- [x] 6.1 Implement `import_from_iaccs` with required `--cutoff`, optional `--branch`, and `--dry-run`; per-loan `transaction.atomic()` with collected row errors and non-zero exit on any failure — verify unit tests cover dry-run (no writes) and single-row failure isolation (spec: "Import command contract", "Read-only source access")
- [x] 6.2 Verify branch filtering — an integration test importing with `--branch 1` imports only branch 1 loans
- [x] 6.3 Document the command (including the stored- vs computed-DPD semantic shift) and verify `uv run python manage.py import_from_iaccs --help` presents the documented options

## 7. Integration Verification

- [x] 7.1 Run a full `--dry-run` against the live `iaccs-mysql` container for branch 1 at a chosen cutoff — verify the report matches `loan_data.py` counts (9,141 loans) with no rows written, and sample-compare DPD values against the URBD extractor on the same loans
- [ ] 7.2 Run the full test suite (`uv run python manage.py test`) and `make audit` — verify all pass with 100% compliance

## Workflow follow-up

- Archive the change after the project's review requirements are satisfied.
- Verify the archived result.
