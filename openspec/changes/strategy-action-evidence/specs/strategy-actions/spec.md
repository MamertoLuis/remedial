# Spec Delta

## ADDED Requirements

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
