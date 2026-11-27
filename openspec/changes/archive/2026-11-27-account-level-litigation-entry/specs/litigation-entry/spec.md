# Spec Delta

## Purpose

Records an account-level, officer-raised, manager-approved entry to legal action, holding at most one active entry per account and feeding the Legal Action and Foreclosure strategy recommendation gate.

## ADDED Requirements

### Requirement: Officer raises an account-level litigation entry

The system SHALL let an account officer raise an account-level litigation entry on a loan account, carrying a target strategy type (Legal Action or Foreclosure), a litigation start date, and an officer rationale. The entry SHALL be created in PENDING_APPROVAL status and SHALL never be derived automatically from delinquency or any other data signal.

#### Scenario: Officer records that an account is entering litigation
- **WHEN** an account officer records an account-level litigation entry with a rationale for an account already in legal proceedings
- **THEN** the system creates the entry in PENDING_APPROVAL status with the target strategy type, start date, and officer rationale

#### Scenario: The entry is never auto-derived
- **WHEN** an account's delinquency snapshot changes
- **THEN** the system does not create or alter a litigation entry based on that change

### Requirement: Manager approves or rejects the litigation entry

The system SHALL let only a MANAGER decide an account-level litigation entry, transitioning it to APPROVED or REJECTED. Only an APPROVED entry counts toward the strategy entry gate; a REJECTED entry does not and may be re-raised.

#### Scenario: Approval unlocks legal action
- **WHEN** a manager approves an account-level litigation entry
- **THEN** the entry transitions to APPROVED and the account may be recommended for the entry's target strategy type

#### Scenario: Rejection blocks and allows re-raise
- **WHEN** a manager rejects an account-level litigation entry
- **THEN** the entry transitions to REJECTED, does not satisfy the strategy gate, and the officer may raise a new entry

### Requirement: At most one active litigation entry per account

The system SHALL hold at most one active litigation entry per account at a time, where active covers PENDING_APPROVAL and APPROVED. A REJECTED entry does not count as active.

#### Scenario: Only one pending or approved entry is allowed
- **WHEN** an account already holds a PENDING_APPROVAL or APPROVED litigation entry and an officer attempts to raise another
- **THEN** the system declines the new entry while the existing one remains active

### Requirement: Approved litigation entry satisfies the legal action gate

The system SHALL treat an APPROVED active litigation entry on an account as satisfying the Legal Action and Foreclosure recommendation gate, with no requirement for the escalation ladder to be at its terminal stage or for an approved agreement rescind. A Foreclosure recommendation SHALL still require a SECURED account.

#### Scenario: Entry gates a legal action recommendation
- **WHEN** an account has an APPROVED litigation entry and the officer recommends Legal Action
- **THEN** the system allows the recommendation without a terminal-stage ladder or an approved rescind

#### Scenario: Foreclosure still requires secured collateral
- **WHEN** an account has an APPROVED litigation entry but is not SECURED and the officer recommends Foreclosure
- **THEN** the system blocks the Foreclosure recommendation for lack of security