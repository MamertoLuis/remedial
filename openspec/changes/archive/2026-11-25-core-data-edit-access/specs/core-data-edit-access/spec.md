# Spec Delta

## Purpose

Restricts UI-driven creation, update, and deletion of core-mirrored records (Borrower, LoanAccount, Exposure) to the SYSTEM_ADMINISTRATOR role, so mirrored core data is edited only by administrators while the refresh pipeline remains the primary writer and all other roles read it read-only.

## ADDED Requirements

### Requirement: System administrator role exists on the user model

The system SHALL provide a SYSTEM_ADMINISTRATOR role as one of the choices on the User role field, distinct from the Account Officer, Manager, and Board Member roles.

#### Scenario: User can be assigned the system administrator role

- **WHEN** a user is created or edited through Django admin
- **THEN** the SYSTEM_ADMINISTRATOR role is available as an assignable role choice

#### Scenario: Existing roles remain unchanged

- **WHEN** a user is created or edited
- **THEN** the Account Officer, Manager, and Board Member role choices continue to be available and unchanged

### Requirement: Only system administrators edit core-mirrored records through the UI

The system SHALL allow only users with the SYSTEM_ADMINISTRATOR role to create, update, or delete Borrower, LoanAccount, and Exposure records through the user-facing views, SHALL return a 403 forbidden response to any other authenticated user requesting those actions, and SHALL leave the write paths used by imports and the service layer (refresh pipeline) ungated.

#### Scenario: Administrator can create a borrower

- **WHEN** a user with the SYSTEM_ADMINISTRATOR role submits the create-borrower form
- **THEN** the Borrower is created and the request completes successfully

#### Scenario: Non-administrator is forbidden from creating a borrower

- **WHEN** a user with a role other than SYSTEM_ADMINISTRATOR submits the create-borrower form
- **THEN** the request is rejected with a 403 forbidden response and no Borrower is created

#### Scenario: Non-administrator is forbidden from updating a loan account

- **WHEN** a user with a role other than SYSTEM_ADMINISTRATOR submits the update-account form
- **THEN** the request is rejected with a 403 forbidden response and the LoanAccount is unchanged

#### Scenario: Non-administrator is forbidden from creating or editing an exposure

- **WHEN** a user with a role other than SYSTEM_ADMINISTRATOR submits the create-exposure or update-exposure form
- **THEN** the request is rejected with a 403 forbidden response and no Exposure is created or changed

#### Scenario: Non-administrator is forbidden from deleting a borrower

- **WHEN** a user with a role other than SYSTEM_ADMINISTRATOR submits the delete-borrower action
- **THEN** the request is rejected with a 403 forbidden response and the Borrower is not deleted

#### Scenario: Non-administrator is forbidden from changing account status directly

- **WHEN** a user with a role other than SYSTEM_ADMINISTRATOR calls the account-status update endpoint
- **THEN** the request is rejected with a 403 forbidden response and the LoanAccount status is unchanged

#### Scenario: Refresh pipeline writes are not gated

- **WHEN** the iAccs import command or a CSV import command writes Borrower, LoanAccount, or Exposure rows
- **THEN** the writes succeed without requiring the SYSTEM_ADMINISTRATOR role

### Requirement: Non-administrators view core-mirrored records read-only

The system SHALL render all list and detail views of Borrower, LoanAccount, and Exposure for every authenticated user, and SHALL NOT present create, edit, or delete controls for those records to users without the SYSTEM_ADMINISTRATOR role.

#### Scenario: Non-administrator sees read-only detail view

- **WHEN** a user with a role other than SYSTEM_ADMINISTRATOR opens a Borrower or LoanAccount detail page
- **THEN** the page renders the record data without create, edit, or delete actions for it

#### Scenario: Administrator sees edit controls

- **WHEN** a user with the SYSTEM_ADMINISTRATOR role opens the same detail page
- **THEN** the page renders the create, edit, or delete actions for the record
