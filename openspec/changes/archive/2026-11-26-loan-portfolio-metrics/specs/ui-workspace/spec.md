# Spec Delta

## MODIFIED Requirements

### Requirement: Dashboard triage layout

The dashboard SHALL present a KPI strip (NPL Ratio, Total NPL, Total Past Due, Past Due Ratio, Total Loan Portfolio, followed by strategy counts) where only NPL and past-due values use `critical` red, a needs-attention table of the 20 most past-due accounts sorted by days past due descending with a View all link, and an alerts panel that shows an empty state when no open alerts exist. Total Past Due and Past Due Ratio SHALL follow the umbrella past-due definition (including NPL) specified by the portfolio-metrics capability.

#### Scenario: Dashboard shows the KPI strip

- **WHEN** an authenticated user opens the dashboard
- **THEN** the KPI strip shows the portfolio and strategy KPIs with NPL and past-due values in red and other values in neutral or brand colors

#### Scenario: Past Due Ratio tile is shown

- **WHEN** an authenticated user opens the dashboard
- **THEN** the KPI strip includes a Past Due Ratio tile computed from the umbrella past-due definition

#### Scenario: Needs-attention table is a triage queue

- **WHEN** the dashboard renders the needs-attention table
- **THEN** it lists up to 20 accounts ordered by days past due descending with borrower, account number, outstanding amount, days past due, strategy, assigned officer, status chip, and an action, plus a View all link to the accounts list

#### Scenario: Alerts panel has an empty state

- **WHEN** the authenticated user has no open alerts on the dashboard
- **THEN** the alerts panel shows a "No open alerts" empty state instead of an empty list
