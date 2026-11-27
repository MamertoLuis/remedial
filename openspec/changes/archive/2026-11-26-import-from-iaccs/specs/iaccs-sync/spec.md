# Spec Delta

## Purpose

Keeps the remedial portfolio synchronized with the iAccs core-banking source by providing canonical loan and borrower identity mapping and point-in-time exposure/delinquency ingestion through a single-hop, read-only import command.

## ADDED Requirements

### Requirement: Canonical loan identity from the iAccs loan key

The system SHALL map each iAccs loan, identified by the five-part loan key (BR_CODE, SLC_CODE=12, SLT_CODE, REF_NO, CLIENTID), to exactly one LoanAccount whose loan_id is rendered as `{BR_CODE:02d}-12-{SLT_CODE:02d}-{REF_NO}-{CLIENTID}`. Re-importing an existing loan key SHALL update the existing account and create no duplicate.

#### Scenario: New loan is created from its five-part key

- **WHEN** the importer encounters an iAccs loan key that has no matching LoanAccount
- **THEN** the system creates a LoanAccount whose loan_id is rendered from the five-part key

#### Scenario: Existing loan is updated in place

- **WHEN** the importer encounters an iAccs loan key that already has a matching LoanAccount
- **THEN** the system updates that account's fields and creates no duplicate

### Requirement: Borrower identity from the client key

The system SHALL map each iAccs client, identified by (ClientIDBrCode, ClientID), to exactly one Borrower whose borrower_id is derived from the client key, and SHALL link every imported LoanAccount to the borrower referenced by that loan's CLIENTID.

#### Scenario: Borrower is created and linked

- **WHEN** the importer processes a loan whose client has no matching Borrower
- **THEN** the system creates the Borrower, records its derived borrower_id, and links the LoanAccount to it

#### Scenario: Borrower is reused across loans

- **WHEN** the importer processes multiple loans that share the same client
- **THEN** all those LoanAccounts link to the same Borrower and no duplicate Borrower is created

### Requirement: Point-in-time exposure with schedule-based days past due

The system SHALL record, for each loan and cutoff date, a point-in-time Exposure snapshot containing principal outstanding and days past due. Days past due SHALL be computed by the aggregate-shortfall rule: walk the loan's `amortsched` installments in due-date order, find the oldest installment whose cumulative scheduled principal due exceeds total principal repaid, and take (cutoff minus that due date) in days — floored at 0, and 0 when that due date has not arrived.

#### Scenario: Snapshot is upserted per account and as-of date

- **WHEN** the importer imports an exposure for a loan and cutoff date that already has an Exposure row
- **THEN** the existing row is updated in place with the new balance and days past due

#### Scenario: Current loan reports zero days past due

- **WHEN** scheduled principal due through the cutoff is fully covered by repayments
- **THEN** the Exposure records 0 days past due

#### Scenario: Underpaid loan reports days past due

- **WHEN** the oldest installment whose cumulative principal due exceeds repayments fell due 95 days before the cutoff
- **THEN** the Exposure records 95 days past due

### Requirement: Existing derivation cascade runs unchanged

When the importer writes an Exposure, the system SHALL trigger the existing cascade that derives DelinquencyStatus (aging bucket, classification, NPL flag) from days past due, updates LoanAccount.status, and creates rule-based ECL provisioning through delinquency post-save handling. The authoritative iAccs classification (cts_type) SHALL NOT override the derived classification.

#### Scenario: Imported delinquency moves account to NPL and provisions

- **WHEN** an exposure with 95 days past due is imported for an account
- **THEN** the account's status becomes NPL and a rule-based ECL provision record is created for the exposure's as-of date

#### Scenario: Source classification does not override derivation

- **WHEN** a loan's iAccs status and the app's derived classification would differ
- **THEN** the app keeps the classification derived from days past due

### Requirement: Read-only source access with no partial writes on failure

The importer SHALL execute only read statements against the iAccs MySQL database, resolve connection settings from the environment (MYSQL56_* convention), and never modify the source database. Row-level failures SHALL be collected and reported without aborting the remaining loans, and the command SHALL exit non-zero when any row failed.

#### Scenario: Source database unreachable

- **WHEN** the importer cannot connect to the iAccs database
- **THEN** the command fails with a clear error and writes no data to the Django database

#### Scenario: A single loan fails mid-import

- **WHEN** one loan row fails validation while other loans succeed
- **THEN** the successful loans are written, the failure is reported, and the command exits non-zero

### Requirement: Import command contract

The system SHALL expose a management command `import_from_iaccs` that accepts a required cutoff date and an optional branch filter, and a `--dry-run` flag that reports what would be created or updated without writing rows.

#### Scenario: Dry run writes nothing

- **WHEN** the importer runs with `--dry-run`
- **THEN** it reports the borrowers, accounts, and exposures it would create or update and writes no rows

#### Scenario: Branch filter limits the import

- **WHEN** the importer runs with a branch filter
- **THEN** only loans of that branch are imported
