# Spec Delta

## MODIFIED Requirements

### Requirement: Entry gates for Legal Action and Foreclosure

The system SHALL allow a Legal Action recommendation only when the account has reached the escalation ladder's terminal stage, or an agreement was rescinded with approval, or an account-level litigation entry was approved. The system SHALL allow a Foreclosure recommendation only when the account is SECURED and the same gate is satisfied.

#### Scenario: Ladder terminal satisfies the legal action gate

- **WHEN** an account is at the escalation ladder terminal stage and the officer recommends Legal Action
- **THEN** the system creates the Legal Action strategy

#### Scenario: Approved rescind satisfies the gate without an open ladder

- **WHEN** an agreement was rescinded with approval and the officer recommends Legal Action or Foreclosure
- **THEN** the system creates the strategy directly, without requiring an open escalation ladder

#### Scenario: Approved litigation entry satisfies the gate without a ladder

- **WHEN** an account has an approved account-level litigation entry and the officer recommends Legal Action or Foreclosure
- **THEN** the system creates the strategy directly, without requiring a terminal-stage ladder or an approved rescind

#### Scenario: Ungated legal action is blocked

- **WHEN** an officer recommends Legal Action for an account that has neither reached the terminal stage, nor had an approved rescind, nor an approved litigation entry
- **THEN** the system blocks the recommendation