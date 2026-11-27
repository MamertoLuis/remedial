# Spec Delta

## Purpose

Governs user account self-service and role administration: users edit only profile data (name/email) on their own account, roles are assigned by the System Administrator through Django admin, and Django admin access is held exclusively by the System Administrator role.

## ADDED Requirements

### Requirement: Self-service profile updates exclude role

The system SHALL let each authenticated user update only their first name, last name, and email through the self-service profile page, SHALL NOT present a role control on that page, and SHALL leave the account's role unchanged regardless of any role value submitted with the update.

#### Scenario: User updates profile details

- **WHEN** an authenticated user submits their profile page with new first name, last name, or email values
- **THEN** those profile fields are updated on their account

#### Scenario: Profile page hides the role control

- **WHEN** an authenticated user opens the self-service profile page
- **THEN** the page renders no control for changing the account role

#### Scenario: Submitted role value is ignored

- **WHEN** an authenticated user submits a profile update carrying a role value such as MANAGER or SYSTEM_ADMINISTRATOR
- **THEN** the account's role remains unchanged and no privilege change occurs

### Requirement: Only System Administrator accounts hold Django admin access

The system SHALL restrict Django admin site access to accounts whose role is SYSTEM_ADMINISTRATOR and whose is_staff flag is set, and SHALL reject any Django admin save that would create a user whose role and is_staff flag disagree: a non-admin role with is_staff set, or the SYSTEM_ADMINISTRATOR role without is_staff.

#### Scenario: Non-admin account cannot be saved as staff

- **WHEN** an operator saves a user with a role other than SYSTEM_ADMINISTRATOR and is_staff set in Django admin
- **THEN** the save is rejected with a validation error and the account keeps its previous flags

#### Scenario: Assigning the System Administrator role grants admin access

- **WHEN** an operator assigns the SYSTEM_ADMINISTRATOR role to a user in Django admin
- **THEN** the account's is_staff flag is set so the account can access the Django admin site

#### Scenario: Demoting a System Administrator removes admin access

- **WHEN** an operator changes a SYSTEM_ADMINISTRATOR account to a different role in Django admin
- **THEN** the account's is_staff flag is cleared so the account no longer has Django admin access
