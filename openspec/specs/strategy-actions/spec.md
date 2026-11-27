# strategy-actions Specification

## Purpose

Provides each strategy type's action catalog and tracked execution records, gating commitments to the bank through a manager-only approval workflow with recorded conditions.

## Requirements

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

### Requirement: Action planning fields stay editable until the action is terminal

The system SHALL let an officer edit an action's assigned staff and due date while the action is in a non-terminal status (SELECTED, PENDING_APPROVAL, or APPROVED), and SHALL reject editing those fields once the action is EXECUTED, SKIPPED, or REJECTED.

#### Scenario: Planning fields editable while the action is in flight

- **WHEN** an officer edits the assigned staff or due date on a SELECTED, PENDING_APPROVAL, or APPROVED action
- **THEN** the fields are updated on the action

#### Scenario: Editing is rejected after the action is terminal

- **WHEN** an officer attempts to edit the assigned staff or due date on an EXECUTED, SKIPPED, or REJECTED action
- **THEN** the system rejects the edit and the fields remain unchanged

### Requirement: Outcome is written only by execution or skip and then locked

The system SHALL write an action's outcome only when the action is executed or skipped, and SHALL NOT provide an editing path that changes an executed or skipped action's recorded outcome.

#### Scenario: Outcome is captured at execution

- **WHEN** an action is executed
- **THEN** its outcome is recorded as entered

#### Scenario: No path edits a recorded outcome

- **WHEN** an officer attempts to change the outcome of an EXECUTED or SKIPPED action through the editing path
- **THEN** the system rejects the change and the recorded outcome stands

### Requirement: Officer can skip a non-pending action with a reason

The system SHALL let an officer skip a non-pending action by recording a reason, which SHALL leave the action SKIPPED, and SHALL reject skipping an action that is PENDING_APPROVAL, REJECTED, EXECUTED, or SKIPPED. A non-approval-gated action is skippable while SELECTED; an approval-gated action is skippable once APPROVED.

#### Scenario: Non-gated selected action is skipped with a reason

- **WHEN** an officer skips a SELECTED non-approval-gated action, recording a reason
- **THEN** the action is recorded SKIPPED with that reason

#### Scenario: Approved gated action is skipped after approval

- **WHEN** an officer skips an APPROVED approval-gated action, recording a reason
- **THEN** the action is recorded SKIPPED with that reason

#### Scenario: Pending-approval action is not skippable

- **WHEN** an officer attempts to skip a PENDING_APPROVAL action
- **THEN** the system rejects the skip

#### Scenario: Executed action is not skippable

- **WHEN** an officer attempts to skip an EXECUTED action
- **THEN** the system rejects the skip

### Requirement: Collection activity may cite the strategy action it fulfills

The system SHALL let a collection activity optionally reference a strategy action of the account's ACTIVE strategy as the action it fulfills, SHALL treat the reference as informational evidence only, and SHALL NOT change the action's status as a result of the link.

#### Scenario: Activity cites the action it fulfills

- **WHEN** an officer logs a collection activity for an account with an ACTIVE strategy and selects an action from that strategy as the fulfilled action
- **THEN** the activity is recorded with the action link

#### Scenario: Activity is logged without an action link

- **WHEN** an officer logs a collection activity for an account with no ACTIVE strategy or does not select an action
- **THEN** the activity is recorded with no action link

#### Scenario: Linking evidence does not execute the action

- **WHEN** an officer links a collection activity to a SELECTED action
- **THEN** the action remains SELECTED and execution still requires the officer's explicit execute action

### Requirement: Evidence links are restricted to the account's active strategy actions

The system SHALL allow linking a collection activity only to actions whose strategy belongs to the same account and is ACTIVE, and SHALL reject any attempt to link an activity to an action of another account or of a strategy that is not ACTIVE.

#### Scenario: Link to a different account is rejected

- **WHEN** an officer attempts to link a collection activity to an action whose strategy belongs to a different account
- **THEN** the system rejects the link

#### Scenario: Actions of an exited strategy cannot be newly linked

- **WHEN** a strategy is not ACTIVE
- **THEN** its actions cannot be newly linked as evidence, while links recorded while the strategy was active remain as history

### Requirement: Action execution can log and link its evidence activity

The system SHALL provide, when executing a strategy action, a one-step path that creates a collection activity for the strategy's account, links it to the action as evidence, and records the action as EXECUTED with the entered outcome in the same operation.

#### Scenario: Log-and-execute creates a linked evidence activity

- **WHEN** an officer executes an action using the log-and-execute path with an outcome
- **THEN** the system creates a collection activity for the account linked to the action and marks the action EXECUTED with the outcome
