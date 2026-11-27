# strategy-lifecycle Specification

## Purpose

Sequences remedial strategy recommendations — exactly one active strategy per account at a time — and governs completion, officer-declared failure, agreement rescind, and escalation to the next strategy.

## Requirements

### Requirement: Recommendation activates the strategy and its action menu

The system SHALL create a remedial strategy in ACTIVE status directly from a loan officer's recommendation, without a strategy-level approval, and SHALL make that strategy's action catalog available to the recommending officer. The system SHALL allow at most one ACTIVE strategy per account at a time.

#### Scenario: Recommended strategy is active immediately

- **WHEN** a loan officer recommends a remedial strategy for an account
- **THEN** the strategy is created in ACTIVE status and its action catalog becomes available

#### Scenario: Competing active strategy is not permitted

- **WHEN** an officer attempts to create an ACTIVE strategy for an account that already has an ACTIVE strategy
- **THEN** the system keeps at most one ACTIVE strategy per account and the previously active strategy is superseded

### Requirement: Strategy completes only on its type's completion condition

The system SHALL consider a strategy COMPLETED only when its strategy type's completion condition is met: Intensive Collection cures the account, Restructuring is honored and the account cures, Compromise is fully paid, Collateral Recovery liquidates or recovers the collateral, Legal Action concludes with judgment or closure, and Write-Off books the write-off.

#### Scenario: Compromise completes when fully paid

- **WHEN** a Compromise strategy's agreement is fully paid
- **THEN** the strategy transitions to COMPLETED

#### Scenario: Intensive Collection completes on cure

- **WHEN** an account under an Intensive Collection strategy returns to performing status
- **THEN** the strategy transitions to COMPLETED

### Requirement: Officer-declared failure and agreement rescind

The system SHALL let a loan officer declare a strategy failed. For agreement-carrying strategies (Compromise and Restructuring) a declared failure marks the agreement unsuccessful, which makes a rescind action available. The rescind action requires manager approval; once approved, the agreement is RESCINDED and the strategy transitions to CANCELLED.

#### Scenario: Unmet approval conditions open the rescind action

- **WHEN** a loan officer declares a compromise unsuccessful because its approval conditions were not met
- **THEN** the system marks the agreement unsuccessful and makes the rescind action available for that strategy

#### Scenario: Approved rescind closes the strategy

- **WHEN** a manager approves the rescind action for an unsuccessful agreement
- **THEN** the system sets the agreement to RESCINDED and the strategy to CANCELLED

#### Scenario: Rejected rescind keeps the strategy active

- **WHEN** a manager rejects the rescind action for an unsuccessful agreement
- **THEN** the agreement remains in effect and the strategy remains ACTIVE with the rescind action still pending

#### Scenario: Non-agreement strategy failure closes without rescind

- **WHEN** a loan officer declares a strategy without an agreement (for example Intensive Collection or Legal Action) failed
- **THEN** the system cancels the strategy directly, recording the declared outcome, with no rescind action involved

### Requirement: Entry gates for Legal Action and Foreclosure

The system SHALL allow a Legal Action recommendation only when the account has reached the escalation ladder's terminal stage or an agreement was rescinded with approval. The system SHALL allow a Foreclosure recommendation only when the account is SECURED and the same gate is satisfied.

#### Scenario: Ladder terminal satisfies the legal action gate

- **WHEN** an account is at the escalation ladder terminal stage and the officer recommends Legal Action
- **THEN** the system creates the Legal Action strategy

#### Scenario: Approved rescind satisfies the gate without an open ladder

- **WHEN** an agreement was rescinded with approval and the officer recommends Legal Action or Foreclosure
- **THEN** the system creates the strategy directly, without requiring an open escalation ladder

#### Scenario: Ungated legal action is blocked

- **WHEN** an officer recommends Legal Action for an account that has neither reached the terminal stage nor had an approved rescind
- **THEN** the system blocks the recommendation

### Requirement: Escalation follows exit

The system SHALL allow the next strategy recommendation for an account only after the current strategy has exited (COMPLETED or CANCELLED), and SHALL record a fresh assessment snapshot for that next recommendation.

#### Scenario: Next recommendation follows an exited strategy

- **WHEN** the current strategy for an account has exited and the officer recommends the next strategy
- **THEN** the system creates the next strategy with a new assessment snapshot

#### Scenario: Recommendation blocked while a strategy is active

- **WHEN** an account still has an ACTIVE strategy and the officer attempts to start a next strategy
- **THEN** the system declines the new recommendation as premature
