# Spec Delta

## Purpose

Keeps at most one active repayment arrangement per loan account by making an active remedial strategy supersede any other active compromise agreement on the same account.

## ADDED Requirements

### Requirement: Active strategy supersedes active compromise agreements

When a RemedialStrategy is saved with status ACTIVE, the system SHALL set every active CompromiseAgreement for the same account that is not linked to that strategy to status SUPERSEDED.

#### Scenario: Active strategy supersedes an existing active compromise agreement

- **WHEN** an ACTIVE RemedialStrategy is saved for an account that has an active CompromiseAgreement linked to a different strategy
- **THEN** that CompromiseAgreement's status becomes SUPERSEDED

#### Scenario: Strategy does not supersede its own compromise agreement

- **WHEN** an ACTIVE RemedialStrategy is saved for an account
- **THEN** any CompromiseAgreement linked to that same strategy is left at its current status

#### Scenario: No active compromise agreement means no change

- **WHEN** an ACTIVE RemedialStrategy is saved for an account with no active CompromiseAgreements
- **THEN** no CompromiseAgreement status is modified