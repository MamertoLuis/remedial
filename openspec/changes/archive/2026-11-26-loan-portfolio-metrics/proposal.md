# Proposal

## Why

The dashboard's "Total Past Due" KPI counts only loans with status `PAST_DUE` (1-90 days past due), treating past due and NPL as disjoint buckets. The business rule defines a past due loan as any loan with an unpaid balance of at least one day (or an unpaid amortization), which makes NPL (unpaid balance of more than 90 days) a subset of past due. The KPI therefore under-reports the past-due portfolio by the entire NPL book, no past-due ratio exists, and the NPL boundary disagrees with itself across the codebase (legacy commands treat 90+ days as NPL; the current pipeline starts NPL at 91).

## What Changes

- **Define past due as the umbrella**: past due = days past due >= 1; NPL is a subset (days past due > 90). The existing schedule-derived `days_past_due` already covers the "unpaid amortization" trigger, so no independent trigger is added.
- **Fix the NPL boundary at more than 90 days (91+)**: a loan with exactly 90 days past due is past due but not NPL. The current pipeline already derives 1-90 -> `SM` (`PAST_DUE`) and 91+ -> `SS`/`D`/`L` (`NPL`); the legacy commands that used 90+ are brought in line through the unified derivation module. `npl_flag` follows classification automatically.
- **Correct "Total Past Due" KPI**: sum principal for `status IN (PAST_DUE, NPL)` instead of `PAST_DUE` only.
- **Add a Past Due Ratio KPI**: count of past due loans (status `PAST_DUE` or `NPL`) divided by active portfolio (excluding `CLOSED` and `WRITEOFF`) as a percentage. The existing NPL ratio denominator changes to exclude `WRITEOFF` too, so both ratios share one denominator definition.
- **Portfolio-by-status chart and per-officer portfolio summary**: umbrella-nested layout - Current, Past Due (including NPL), Written Off, with NPL shown as a nested subset of Past Due.
- **Fix the Past Due Aging Summary report**: include NPL accounts so the 91+ day buckets can populate (they are unreachable today).
- **Repair legacy-written rows**: a management command fixes any rows the legacy path wrote at exactly 90 days as NPL (`SS` -> `SM`, `npl_flag` -> false) - a safety net, since the current pipeline never produced them.
- **Unify the derivation**: one module for classification, aging bucket, and status mapping, used by every pipeline (`main.py`, `update_delinquency.py`, `load_dummy_delinquency.py`) and reporting, replacing the three divergent implementations.
- Update tests that pin the old 90/91 boundary.

## Capabilities

### New Capabilities
- `portfolio-metrics`: Defines the business semantics of portfolio risk metrics - what makes a loan past due (umbrella rule), what makes it NPL (>= 90 days), the past-due ratio and its active-portfolio denominator, and how the portfolio-by-status breakdown is presented (umbrella-nested). This capability owns these definitions as the system evolves.

### Modified Capabilities
- `ui-workspace`: The "Dashboard triage layout" requirement changes - the KPI strip gains a "Past Due Ratio" tile and the "Total Past Due" tile reflects the umbrella past-due definition (its KPI semantics are specified by `portfolio-metrics`).

## Impact

- `account_master/services/main.py` - classification derivation boundary (90 vs 91) and extraction of a shared derivation module.
- `account_master/services/dashboard_service.py` - Total Past Due query, new Past Due Ratio, NPL ratio denominator, portfolio-by-status umbrella layout.
- New management command - backfill of existing 90-day delinquency rows.
- `reporting/views.py` - `past_due_aging_summary` (include NPL), per-officer `portfolio_summary` (umbrella past-due balance).
- Dashboard and reporting templates - new "Past Due Ratio" tile, chart layout.
- Tests - boundary assertions in `tests_services_core_financial.py`, dashboard/reporting metric tests.
- No classification shift occurs at 90 days, so there is no boundary-driven change to ECL provision rates; legacy-repaired rows may carry stale `SS` provision history, which is left untouched per the non-goals.
- `escalation_service` and the needs-attention feed already union `PAST_DUE` and `NPL` and are unaffected.
