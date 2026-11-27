# Tasks

## 1. Unified classification derivation

- [x] 1.1 Create `account_master/services/classification.py` exposing `derive_classification(days_past_due)` (0->C, 1-90->SM, 91-180->SS, 181-360->D, 360+->L), `derive_aging_bucket(days_past_due)` (1-30, 31-60, 61-90, 91-120, 121-180, 181-360, Over 360, Current for 0), and `derive_status(classification, outstanding_balance)` (WRITEOFF/CLOSED sentinels, C->PERFORMING, SM->PAST_DUE, SS/D/L->NPL). Verify: unit tests in `tests_services_core_financial.py` pin the corrected boundaries — `derive_classification(90) == "SM"`, `derive_classification(91) == "SS"`, `derive_status("SS", ...) == "NPL"`, and the sentinel rules.
- [x] 1.2 Switch `account_master/services/main.py` (`_derive_classification`, `_derive_aging_bucket`, `_update_loan_account_status`) to the shared module and delete the local duplicates. Verify: existing snapshot/status tests plus the boundary tests pass; a 90-DPD upsert produces classification `SM` and status `PAST_DUE`, and a 95-DPD upsert produces `SS`/`NPL` (integration assertions in `tests_services_core_financial.py`).
- [x] 1.3 Switch `account_master/management/commands/update_delinquency.py` and `load_dummy_delinquency.py` to the shared module, retiring the legacy single-boundary bucket labels. Verify: a dry run of both commands against fixtures produces classification/bucket output consistent with `derive_*` (> 90 days -> NPL, exactly 90 -> PAST_DUE) and no crash.

## 2. Dashboard portfolio metrics

- [x] 2.1 Update `DashboardService.get_total_past_due_loans` to sum principal over `status__in=["PAST_DUE", "NPL"]`. Verify: unit test with one PAST_DUE and one NPL account asserts the KPI equals both balances combined (update `tests_dashboard_needs_attention.py` or a dashboard KPI test).
- [x] 2.2 Add `DashboardService.get_past_due_ratio` returning `count(status__in=["PAST_DUE","NPL"]) / count(status__not_in=["CLOSED","WRITEOFF"]) * 100`, rounded to 2 decimals, and add it to `get_portfolio_kpis` and `_get_default_kpis`. Verify: unit tests cover the 0%, 100%, and mixed cases with CLOSED/WRITEOFF accounts excluded from the denominator.
- [x] 2.3 Update `get_npl_ratio` to use the same active-portfolio denominator (exclude `CLOSED` and `WRITEOFF`), ideally via a shared helper. Verify: unit test asserts a WRITEOFF account is excluded from the NPL ratio denominator.
- [x] 2.4 Update `get_portfolio_by_status` to the umbrella-nested layout: Current, Past Due (PAST_DUE + NPL balance, NPL exposed as a nested subset), Written Off. Verify: unit test asserts the Past Due slice includes the NPL balance, the NPL subset is present, and the slices sum to the portfolio.
- [x] 2.5 Add the "Past Due Ratio" tile to the dashboard KPI strip template (after Total Past Due), reusing the shared `kpi_tile.html` partial. Verify: dashboard render test asserts the tile and its computed value appear (extend `tests_ui.py` or `tests_dashboard_needs_attention.py`).

## 3. Reporting

- [x] 3.1 Update `reporting/views.py: past_due_aging_summary` to query `status__in=["PAST_DUE", "NPL"]` so the 91-120 through Over 360 buckets can populate. Verify: unit test creates a 95-DPD NPL account and asserts it lands in the "91-120" bucket row.
- [x] 3.2 Update `reporting/views.py: portfolio_summary` per-officer `past_due_balance` to the umbrella definition (PAST_DUE + NPL balances), keeping the NPL balance available for display. Verify: unit test with known PAST_DUE and NPL balances asserts the umbrella past-due balance and that the NPL portion is still reported.

## 4. Backfill command

- [x] 4.1 Add a `repair_legacy_npl_rows` management command: for each `DelinquencyStatus` with `days_past_due == 90` and `classification == "SS"`, set `classification = "SM"` and `npl_flag = False`; then recompute each affected account's `LoanAccount.status` via `derive_status` (preserving WRITEOFF/CLOSED sentinels) and clear the dashboard cache. Support `--dry-run` (report affected rows, change nothing). Verify: unit test runs the command on a fixture with a legacy-written 90-DPD `SS` row and asserts reclassification to `SM`/`npl_flag` false, status recompute, cache clear, and that `--dry-run` leaves rows unchanged.

## 5. Integration checks

- [x] 5.1 Full verification: `openspec validate --changes` passes for `loan-portfolio-metrics`, the boundary/backfill tests pass, and `make audit` exits 0 (system checks + full test suite).
- [x] 5.2 Operational dry-run: execute the backfill command against the development database in `--dry-run` mode and confirm the reported affected-row count matches a manual query of 90-DPD `SS` rows. Verify: no rows changed by the dry run; output reviewed (expected zero affected rows when no legacy data exists).
