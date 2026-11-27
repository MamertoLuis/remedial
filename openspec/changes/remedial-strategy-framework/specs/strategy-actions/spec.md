# Spec Delta

## Purpose

Provides each strategy type's action catalog and tracked execution records, gating commitments to the bank through a manager-only approval workflow with recorded conditions.

## ADDED Requirements

### Requirement: Each strategy type provides an action catalog

The system SHALL provide, per strategy type, a fixed catalog of available action templates drawn from the remediation action lists, each with a name and a flag indicating whether selecting the action requires manager approval.

#### Scenario: Intensive Collection catalog covers communication and field actions

- **WHEN** the Intensive Collection catalog is presented
- **THEN** it includes calls, SMS and reminders, collection letters and demand notices, personal visits, field collection, guarantor collection, and agency engagement

#### Scenario: All six strategy types expose their action lists

- **WHEN** the catalogs for all six strategy types are reviewed
- **THEN** Restructuring exposes terms actions (extension, amortization, frequency, moratorium, interest or penalty revision, additional security, consolidation), Compromise exposes settlement actions (full, partial with condonation, installment, discounted, via asset sale proceeds), Collateral Recovery exposes recovery procedures (surrender, extrajudicial and judicial foreclosure, repossession, acquisition and disposal), Legal Action exposes legal procedures (final demand, counsel referral, filings, foreclosure proceedings, judgment enforcement, asset execution), and Write-Off exposes write-off and post-write-off actions (approval, agency endorsement, continued collection, recovery monitoring)

#### Scenario: Active strategy exposes only its own catalog

- **WHEN** an account has an ACTIVE strategy
- **THEN** the officer can select actions from that strategy type's catalog only

#### Scenario: Approval flag distinguishes action classes

- **WHEN** the catalog is presented for a strategy type
- **THEN** each action template shows whether committing to it requires manager approval, with financial, legal, and contractual commitments flagged as approval-gated and communication and field actions flagged as not

### Requirement: Selected actions are tracked as execution records

The system SHALL record every action selected for a strategy as an execution record carrying its template, status, assigned staff, due date, and outcome. Non-approval-gated actions SHALL be executed and recorded directly by the officer.

#### Scenario: Officer executes a non-gated action directly

- **WHEN** an officer carries out a communication or field action that is not approval-gated
- **THEN** the system records the action with its outcome, assignee, and date without requiring approval

#### Scenario: Action record status advances with execution

- **WHEN** an action has been executed and its outcome entered
- **THEN** the system records the completed status, outcome, and executing staff for the action

### Requirement: Approval-gated actions await manager approval

The system SHALL hold any selected action flagged as approval-gated in a pending approval state and SHALL prevent its execution until the manager approves it. A rejected action is not executed.

#### Scenario: Gated action cannot be executed before approval

- **WHEN** an officer selects an approval-gated action for a strategy and attempts to execute it before any approval is recorded
- **THEN** the system blocks execution while the action is pending approval

#### Scenario: Manager approval releases the action

- **WHEN** a manager approves a pending approval-gated action
- **THEN** the action becomes eligible for execution and records the approver and decision

#### Scenario: Rejected action stays unexecuted

- **WHEN** a manager rejects a pending approval-gated action
- **THEN** the action is recorded as rejected and is not executed

### Requirement: Manager is the sole approver and board is read-only

The system SHALL let only users with the MANAGER role approve or reject actions (including rescind and write-off approvals, with board-level authority delegated to the manager), and SHALL give BOARD_MEMBER users read-only access to strategies, assessments, actions, and approvals.

#### Scenario: Non-manager approval attempt is rejected

- **WHEN** a user whose role is not MANAGER attempts to approve a pending action
- **THEN** the system rejects the attempt and leaves the action pending

#### Scenario: Board member views without deciding

- **WHEN** a BOARD_MEMBER user accesses strategy records
- **THEN** the system grants read-only access to strategies, assessments, actions, and approvals with no decision capability

### Requirement: Approval records carry conditions

The system SHALL record each approval with the approver, decision, date, and any conditions attached to the approval, and SHALL let a loan officer declare that conditions attached to an approval were not met.

#### Scenario: Approval recorded with conditions

- **WHEN** a manager approves a gated action with conditions (for example, a downpayment requirement)
- **THEN** the system stores the approval together with the recorded conditions

#### Scenario: Unmet conditions are declared by the officer

- **WHEN** conditions attached to an approval are not met and a loan officer declares them unmet
- **THEN** the system records the declaration as the basis for marking the related agreement unsuccessful
