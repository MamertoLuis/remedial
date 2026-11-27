# Design

## Context

The metric semantics are implemented in three places today, and they disagree:

- `account_master/services/main.py` (`_derive_classification`, `_derive_aging_bucket`, `_update_loan_account_status`) — the current iAccs pipeline: 1-90 days -> `SM` -> `PAST_DUE`, 91+ -> `SS`/`D`/`L` -> `NPL`.
- `account_master/management/commands/update_delinquency.py` and `load_dummy_delinquency.py` — legacy: >= 90 days -> `SS` -> `NPL` (single-boundary bucket labels 30/60/90/180/360).
- `reporting/views.py` and `account_master/services/dashboard_service.py` — read `LoanAccount.status`: Total Past Due sums `status="PAST_DUE"` only; NPL ratio denominator excludes only `CLOSED`; `past_due_aging_summary` selects `PAST_DUE` only while rendering buckets up to "Over 360" (unreachable); portfolio-by-status slices are disjoint Current / Past Due / NPL / Written Off.

`escalation_service.DELINQUENT_STATUSES` and the dashboard needs-attention feed already union `PAST_DUE` and `NPL`. See proposal.md for the business rules and motivation.

## Goals / Non-Goals

**Goals:**
- One source of truth for classification, aging bucket, and status mapping, with the NPL boundary at exactly 90 days past due.
- Dashboard metrics follow the umbrella past-due definition: Total Past Due includes NPL; a new Past Due Ratio exists.
- One active-portfolio denominator (excluding `CLOSED` and `WRITEOFF`) shared by the Past Due and NPL ratios.
- Portfolio-by-status chart and per-officer summary use the umbrella-nested layout (Current / Past Due incl. NPL / Written Off).
- The Past Due Aging Summary report includes NPL accounts so the 91+ buckets populate.
- Existing 90-day rows are backfilled so metrics are correct immediately.

**Non-Goals:**
- No change to the unpaid-amortization trigger (schedule-derived days past due already covers it).
- No retroactive rewrite of historical ECL provision records.
- No new provision-rate policy beyond the classification boundary effect at 90 days.
- No change to the operational `PAST_DUE` / `NPL` status ladder: they remain the operational stages for triage, escalation, and provisioning; the umbrella rule is a metric-level contract.
- No behavior change to escalation, alert rules, or the needs-attention feed (they already treat both statuses as delinquent).

## Decisions

1. **NPL boundary at more than 90 days (91+).** The canonical `_derive_classification` stays: 0 -> `C`, 1-90 -> `SM`, 91-180 -> `SS`, 180-360 -> `D`, 360+ -> `L`; a loan with exactly 90 days past due is `PAST_DUE`, not NPL. The legacy commands' >= 90 rule is the divergence and is removed by unification. Alternative (>= 90) was rejected per the corrected business rule (NPL = more than 90 days).

2. **Umbrella at the metric layer, not a new status.** "Past due" is a computed predicate: `status IN (PAST_DUE, NPL)`. The two statuses stay as-is. Alternative (introduce a nested status) was rejected as invasive with no consumer benefit.

3. **Single derivation module.** Extract `derive_classification(days_past_due)`, `derive_aging_bucket(days_past_due)`, and `derive_status(classification, outstanding_balance)` into `account_master/services/classification.py`, used by `main.py`, `update_delinquency.py`, and `load_dummy_delinquency.py`. Reporting keeps reading the stored `DelinquencyStatus` snapshot fields. Alternative (leave duplicated logic) was rejected - the duplication already produced the 90-vs-91 divergence this change fixes.

4. **Shared active-portfolio denominator.** Both ratios divide by `LoanAccount.objects.exclude(status__in=["CLOSED", "WRITEOFF"]).count()`. Alternative (exclude `CLOSED` only, as NPL ratio does today) was rejected: written-off loans are off-book and belong in neither denominator.

5. **Past Due Ratio is count-based.** `count(status IN (PAST_DUE, NPL)) / active portfolio * 100`, mirroring the existing count-based NPL ratio (not balance-weighted).

6. **Portfolio-by-status layout A (umbrella-nested).** Slices: Current, Past Due (which includes the NPL balance, NPL rendered as a nested subset), Written Off. Implemented by computing the operational `PAST_DUE` and `NPL` balances separately and presenting NPL inside the umbrella Past Due slice. Alternative (disjoint slices) was rejected for definitional consistency with decision 2.

7. **Repair legacy-written rows via an idempotent management command** (e.g., `repair_legacy_npl_rows`): for each `DelinquencyStatus` with `days_past_due == 90` and `classification == "SS"`, set `classification = "SM"` and `npl_flag = False`; then recompute `LoanAccount.status` for affected accounts via the shared `derive_status` (preserving the `WRITEOFF`/`CLOSED` sentinels). The current pipeline never writes 90 as `SS`, so this is a safety net for rows the legacy commands left behind. Command supports `--dry-run`, clears the dashboard cache, and is rerunnable. Alternative (accept drift until the next snapshot) was rejected - the change is about metric correctness, so numbers must be right immediately.

8. **One aging-bucket taxonomy.** Unify on the range buckets already used by `main.py` and the reporting view: 1-30, 31-60, 61-90, 91-120, 121-180, 181-360, Over 360; retire the legacy single-boundary labels. Accepted quirk: the "61-90" bucket straddles the 90-day NPL boundary (a 90-DPD loan sits in "61-90" while being NPL) - buckets are descriptive, not definitional.

9. **Reporting fixes.** `past_due_aging_summary` filters `status__in=["PAST_DUE", "NPL"]` so every bucket can populate; per-officer `portfolio_summary` past-due balance = `PAST_DUE` + `NPL` balances (umbrella), with the NPL portion still available for display.

## Risks / Trade-offs

- [Legacy-written 90-DPD rows carry `SS` classification and provision history] -> The repair command flips status and `npl_flag` to match the rule; historical `ECLProvisionHistory` records are left untouched per the non-goals, and no boundary-driven provision-rate change occurs at exactly 90 days.
- [Backfill modifies production rows] -> Command is idempotent, scoped to `days_past_due == 90` / `classification == "SM"`, has `--dry-run`, and clears the dashboard cache on completion.
- [NPL ratio value changes because `WRITEOFF` leaves the denominator] -> Expected and intended; both ratios now share one definition; call it out in the change summary and any release notes.
- [Repaired 90-DPD rows flip `NPL` -> `PAST_DUE`, shifting them between status-based buckets in charts/reports] -> They remain inside the umbrella Past Due slice and the union-based feeds (escalation, needs attention); boundary tests cover the 90/91 boundary.
- [Bucket-taxonomy unification may affect templates that hardcode legacy labels] -> Audit reporting templates for hardcoded bucket strings during implementation; the shared `derive_aging_bucket` becomes the only producer.

## Migration Plan

1. Add the shared derivation module and switch `main.py` and the legacy commands to it (the legacy commands' >= 90 behavior changes to > 90; `main.py` behavior is unchanged).
2. Update dashboard/reporting queries and templates; add the Past Due Ratio tile.
3. Update boundary and metric tests.
4. Run the repair command: `--dry-run`, review any affected 90-DPD `SS` rows, then real run (clears dashboard cache); skip entirely if none exist.
5. Verify dashboard KPIs, portfolio-by-status chart, and aging report against a known sample.

**Rollback:** Revert the code commits; the backfill is forward-only but the point-in-time `DelinquencyStatus` snapshots remain, so statuses can be recomputed from history by re-running the prior derivation on the next snapshot cycle. No destructive data change.

## Open Questions

- Where the per-classification provision rate is configured (ProvisionRate records) — verify during implementation; does not change the specs or approach.
- Whether the per-officer portfolio summary template should also display the NPL subset row — cosmetic; settle during implementation.
