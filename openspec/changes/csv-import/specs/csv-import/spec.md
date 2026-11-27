# Spec Delta

## Purpose

Contracts the admin CSV import path: files carry loan master data and exposure observations only, are validated whole before any write, and never decide classification, NPL, account status, ECL, or escalation, which derive from computed days past due.

## ADDED Requirements

### Requirement: Whole-file validation before any write

The system SHALL validate every row of a CSV import against its declared contract — exact headers, field types, and referential integrity — before writing any row, and SHALL reject the whole file with a non-zero exit when any row is invalid, writing nothing.

#### Scenario: Clean file imports fully
- **WHEN** every row of a CSV file passes header, type, and referential validation
- **THEN** the importer writes the rows and exits with status zero

#### Scenario: One invalid row rejects the file
- **WHEN** a single row of a CSV file fails validation
- **THEN** no row from the file is written and the importer exits non-zero with a report of the failure

### Requirement: Account import carries master data only

The accounts import SHALL accept only identity, booking and maturity dates, original principal, interest rate, loan type, loan security, and account officer columns. A file containing a status column SHALL be rejected, because account status is always derived.

#### Scenario: Status column is rejected
- **WHEN** an accounts file contains a status column
- **THEN** the importer rejects the file before writing any account

#### Scenario: Master fields update the account
- **WHEN** an accounts file passes validation
- **THEN** the importer updates the account's identity, dates, principal, rate, type, security, and officer fields only

### Requirement: Loan security is required and validated

The accounts import SHALL require a recognized loan security value on every row; a missing or unrecognized security value SHALL fail validation.

#### Scenario: Missing security fails validation
- **WHEN** an accounts row omits or misspells its loan security value
- **THEN** the file is rejected and no account defaults to UNSECURED

#### Scenario: Recognized security is applied
- **WHEN** an accounts row carries a recognized security value
- **THEN** the account records that security value

### Requirement: Exposure import carries observations, days past due is computed

The exposure import SHALL accept principal outstanding, accrued interest, accrued penalty, and optional should-pay and actual-pay columns only. A days_past_due column SHALL be rejected, and days past due SHALL be computed from the repayment schedule by the aggregate-shortfall rule, as in the iaccs import.

#### Scenario: Days past due column is rejected
- **WHEN** an exposure file contains a days_past_due column
- **THEN** the importer rejects the file rather than trusting file-supplied days past due

#### Scenario: Computed days past due drives the cascade
- **WHEN** an exposure row passes validation
- **THEN** the importer computes days past due from the repayment schedule and derives delinquency, status, and escalation from it

### Requirement: Classification fields are never accepted from a file

No CSV import SHALL accept classification, aging bucket, NPL flag, or NPL date columns; those values SHALL be derived from computed days past due by the shared classification rules.

#### Scenario: Classification column is rejected
- **WHEN** a file contains a classification, aging bucket, NPL flag, or NPL date column
- **THEN** the importer rejects the file before writing any row

#### Scenario: Derived classification is written
- **WHEN** a delinquency datum is written by any CSV import
- **THEN** the classification, aging bucket, and NPL flag are those derived from computed days past due

### Requirement: No silent coercion

The importer SHALL fail a row whose required values cannot be parsed as their declared types or recognized choices, and SHALL NOT substitute default values silently.

#### Scenario: Unrecognized borrower type is rejected
- **WHEN** a borrower row carries a borrower type the system does not recognize
- **THEN** the file is rejected rather than defaulting the borrower to an individual

#### Scenario: Unparseable value is rejected
- **WHEN** a row carries a value that cannot be parsed as its declared type
- **THEN** the file is rejected and no default value is substituted

### Requirement: One date format

Dates in CSV files SHALL use the ISO YYYY-MM-DD format; any other date representation, including slash-delimited and Excel serial values, SHALL fail validation.

#### Scenario: ISO date is accepted
- **WHEN** a row carries a date in ISO YYYY-MM-DD format
- **THEN** the importer parses it and proceeds

#### Scenario: Ambiguous date format is rejected
- **WHEN** a row carries a slash-delimited or Excel serial date
- **THEN** the file is rejected rather than guessing the date layout

### Requirement: Within-file duplicate keys reject the file

A CSV file SHALL be rejected when it contains more than one row for the same natural key — borrower id, loan id, or account and as-of date — because the intended target row is ambiguous.

#### Scenario: Duplicate borrower id in one file
- **WHEN** a borrowers file lists the same borrower id twice
- **THEN** the importer rejects the whole file before writing any row

### Requirement: Re-import is idempotent

Re-importing a file identical to one already applied SHALL change nothing and exit successfully.

#### Scenario: Identical file re-applied
- **WHEN** a previously applied file is imported again
- **THEN** no record changes and the importer exits with status zero

### Requirement: Dry-run and exit contract

The importer SHALL report what it would write and write nothing under dry-run, and SHALL exit with status zero only when the file was fully applied.

#### Scenario: Dry-run writes nothing
- **WHEN** the importer runs in dry-run mode against a valid file
- **THEN** it reports the rows it would write and writes no rows

#### Scenario: Partial application is never reported as success
- **WHEN** any part of a file is not applied
- **THEN** the importer exits non-zero

### Requirement: CSV never modifies iaccs-tagged records

The system SHALL tag every exposure and derived delinquency record with its import source — iaccs or CSV. A CSV file that would modify a record tagged iaccs for the same account and as-of date SHALL be rejected in validation, writing nothing.

#### Scenario: CSV collides with an iaccs snapshot
- **WHEN** a CSV file would write an exposure or delinquency row for an account and as-of date already tagged as iaccs
- **THEN** the file is rejected during validation and nothing is written

#### Scenario: Correcting a CSV-written snapshot is allowed
- **WHEN** a CSV file would rewrite a row that a previous CSV import tagged as CSV for the same account and as-of date
- **THEN** the importer permits the correction and updates that row