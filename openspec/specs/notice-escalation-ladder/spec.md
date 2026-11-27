# notice-escalation-ladder Specification

## Purpose

Guides the timed, officer-issued escalation of delinquent accounts through a sequence of notices — each stage raising severity, each stage having a duration until the next — until the account cures, an arrangement is approved, or the officer reaches the terminal stage and recommends Legal Action or Foreclosure.

## Requirements

### Requirement: Escalation ladder has ordered stages with durations

The system SHALL provide a fixed escalation ladder of ordered stages, where each stage has a position, a label, a duration in days until the next notice, and a flag marking whether it is the terminal stage. The system SHALL record the ladder template as a reusable definition, not as per-account data.

#### Scenario: Ladder uses the fixed stage template

- **WHEN** the system determines an account's next escalation notice
- **THEN** it uses the fixed stage template's ordered stages and the current stage's configured duration to determine the next stage and its due date

#### Scenario: Terminal stage is distinguishable

- **WHEN** an account reaches the stage marked terminal in the template
- **THEN** the system treats it as the last escalation stage rather than advancing to a further notice

### Requirement: Each account tracks one escalation position

The system SHALL track, per loan account, at most one active escalation state carrying the current stage, the date the stage started, the computed next-notice due date, and a status from the allowed set (PENDING, ACTIVE, PAUSED, CLOSED).

#### Scenario: First delinquency creates a pending position

- **WHEN** an account first becomes delinquent and has no escalation state
- **THEN** the system creates an escalation state in PENDING status at the first stage

#### Scenario: An account holds only one open escalation state

- **WHEN** an escalation state already exists for an account
- **THEN** the system does not create a second open one for that account

### Requirement: Issuing a notice advances the position and sets the next due date

The system SHALL let an officer issue a notice manually. Issuing a notice SHALL record the notice, move the escalation state to the next stage (or to CLOSED if the stage is terminal), and compute the next-notice due date as the notice issue date plus the current stage's duration.

#### Scenario: Issuing a non-terminal notice advances to the next stage

- **WHEN** an officer issues a notice for an account at a non-terminal stage
- **THEN** the escalation state moves to the next stage, records the issued notice, and sets the next-notice due date from the new stage's duration

#### Scenario: Issuing at the terminal stage closes the ladder

- **WHEN** an officer issues a notice while the account is at the terminal stage
- **THEN** the escalation state transitions to CLOSED and no further notice is scheduled

#### Scenario: The system never advances without an officer action

- **WHEN** the next-notice due date passes with no officer action
- **THEN** the escalation state remains at its current stage and the system raises an overdue alert instead of auto-advancing

### Requirement: Ladder pauses only while a promise to pay is pending

The system SHALL pause a PAUSED-state-eligible escalation ladder only while a pending promise-to-pay exists on the account's contact log, and SHALL resume the ladder at the same stage once the promise is no longer pending. Honoring or breaking a promise SHALL NOT change the escalation stage or reset the ladder.

#### Scenario: Pending promise to pay pauses the ladder

- **WHEN** a promise-to-pay is recorded pending on a contact activity for the account
- **THEN** the escalation state is set to PAUSED while the promise remains pending

#### Scenario: Resuming returns to the same stage

- **WHEN** a pending promise-to-pay is resolved for an account whose escalation state is PAUSED
- **THEN** the escalation state returns to ACTIVE at the same stage it held before the pause

#### Scenario: Honored promise does not reset the ladder

- **WHEN** a promise-to-pay is honored but the account's delinquency is not cleared in full
- **THEN** the escalation state remains at its current stage and the ladder is not reset or advanced

### Requirement: Escalation closes on cure, arrangement approval, or terminal recommendation

The system SHALL close an account's escalation state when (a) the account's status returns to performing, (b) an approved compromise or restructuring arrangement exists for the account, or (c) the officer reverses the terminal stage by recommending Legal Action or Foreclosure, which SHALL create an active RemedialStrategy of the corresponding type. A ladder closed because of an approved arrangement SHALL remain closed if that arrangement is later rescinded; the account escalates through a direct strategy recommendation rather than reopening the ladder.

#### Scenario: Cured account closes the ladder

- **WHEN** the account's mirrored status becomes performing while an escalation state is open
- **THEN** the escalation state is closed with reason "cured"

#### Scenario: Approved arrangement closes the ladder

- **WHEN** a compromise or restructuring arrangement is approved for the account
- **THEN** the escalation state is closed with reason "arrangement" and no further notices are scheduled

#### Scenario: Terminal stage creates a legal or foreclosure strategy

- **WHEN** an officer reaches the terminal stage and recommends Legal Action or Foreclosure
- **THEN** the system closes the escalation state and creates an active RemedialStrategy of type Legal Action or Foreclosure on the account

#### Scenario: Rescinded arrangement keeps the ladder closed

- **WHEN** an arrangement that closed an account's ladder is later rescinded with approval
- **THEN** the escalation state remains closed and no notices are scheduled for the account
