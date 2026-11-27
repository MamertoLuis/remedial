# Spec Delta

## ADDED Requirements

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