# Spec Delta

## MODIFIED Requirements

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
