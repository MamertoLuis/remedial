# portfolio-metrics Specification

## Purpose

Defines the business definitions of portfolio risk metrics: the umbrella past-due rule (any loan with days past due of at least one day, NPL included), the 90-day NPL threshold, the Past Due and NPL ratios and their shared active-portfolio denominator, and the umbrella-nested portfolio-by-status breakdown.

## Requirements

### Requirement: Past due loan definition

A loan SHALL be considered past due when its days past due is at least 1, where days past due is derived from the loan's repayment schedule and therefore already captures unpaid amortizations; past due SHALL include every non-performing loan, which is past due by definition.

#### Scenario: Loan with one day past due is past due

- **WHEN** a loan has exactly 1 day past due
- **THEN** the loan is counted as past due

#### Scenario: NPL loans are counted as past due

- **WHEN** a loan is non-performing (more than 90 days past due)
- **THEN** the loan is also counted as past due

#### Scenario: Current loan is not past due

- **WHEN** a loan has 0 days past due
- **THEN** the loan is not counted as past due

#### Scenario: Total past due balance includes NPL

- **WHEN** the Total Past Due balance KPI is computed
- **THEN** it sums the outstanding principal of every past due loan, including the outstanding principal of NPL loans

### Requirement: NPL loan definition

A loan SHALL be classified as non-performing (NPL) when its days past due is more than 90 days; a loan with exactly 90 days past due SHALL NOT be classified NPL and SHALL remain counted as past due.

#### Scenario: Exactly 90 days is not NPL

- **WHEN** a loan has exactly 90 days past due
- **THEN** the loan is not classified NPL and remains counted as past due

#### Scenario: Below 90 days is not NPL

- **WHEN** a loan has 89 days past due
- **THEN** the loan is not classified NPL

#### Scenario: More than 90 days is NPL

- **WHEN** a loan has 91 or more days past due
- **THEN** the loan is classified NPL

### Requirement: Past Due Ratio

The system SHALL report a Past Due Ratio equal to the number of past due loans (including NPL) divided by the number of accounts in the active portfolio, expressed as a percentage; the active portfolio SHALL exclude CLOSED and WRITEOFF accounts.

#### Scenario: NPL loans are in the ratio numerator

- **WHEN** the Past Due Ratio is computed
- **THEN** NPL loans are included in the past due count that forms the numerator

#### Scenario: Denominator is the active portfolio

- **WHEN** the Past Due Ratio is computed
- **THEN** CLOSED and WRITEOFF accounts are excluded from the denominator

#### Scenario: All active loans past due

- **WHEN** every account in the active portfolio is past due
- **THEN** the Past Due Ratio is 100%

#### Scenario: No active loan past due

- **WHEN** no account in the active portfolio is past due
- **THEN** the Past Due Ratio is 0%

### Requirement: NPL Ratio shares the active-portfolio denominator

The NPL Ratio SHALL equal the number of NPL loans divided by the same active-portfolio denominator as the Past Due Ratio, so both ratios use one denominator definition that excludes CLOSED and WRITEOFF accounts.

#### Scenario: Written-off accounts excluded from NPL ratio

- **WHEN** the NPL Ratio is computed
- **THEN** WRITEOFF accounts are excluded from the denominator

#### Scenario: Same denominator as Past Due Ratio

- **WHEN** the NPL Ratio is computed
- **THEN** its denominator is the same active-portfolio denominator used by the Past Due Ratio

### Requirement: Portfolio-by-status breakdown

The portfolio-by-status breakdown SHALL present Current, Past Due, and Written Off slices, where the Past Due slice covers the umbrella definition (including NPL) and NPL is shown as a nested subset of Past Due.

#### Scenario: NPL is nested under Past Due

- **WHEN** the portfolio-by-status breakdown is rendered
- **THEN** the Past Due slice includes the NPL balance and NPL is displayed as a subset of Past Due

#### Scenario: Slices cover the portfolio

- **WHEN** the portfolio-by-status breakdown is rendered
- **THEN** the Current, Past Due, and Written Off slices together account for the full portfolio