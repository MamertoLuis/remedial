# Spec Delta

## Purpose

Guarantees accurate create/update semantics for borrower and loan-account identity upserts, so callers can rely on the returned `created` flag when reporting imported vs updated records.

## ADDED Requirements

### Requirement: Borrower upsert reports accurate result

The system SHALL create or update a Borrower identified by `borrower_id` and return an accurate boolean indicating whether a new Borrower was created.

#### Scenario: New borrower returns created

- **WHEN** an upsert targets a borrower_id that does not yet exist
- **THEN** a Borrower is created and the upsert returns `created == True`

#### Scenario: Existing borrower returns updated

- **WHEN** an upsert targets a borrower_id that already exists
- **THEN** the existing Borrower's fields are updated and the upsert returns `created == False`

### Requirement: Loan-account upsert reports accurate result

The system SHALL create or update a LoanAccount identified by `loan_id` and return an accurate boolean indicating whether a new LoanAccount was created.

#### Scenario: New account returns created

- **WHEN** an upsert targets a loan_id that does not yet exist
- **THEN** a LoanAccount is created and the upsert returns `created == True`

#### Scenario: Existing account returns updated

- **WHEN** an upsert targets a loan_id that already exists
- **THEN** the existing LoanAccount's fields are updated and the upsert returns `created == False`