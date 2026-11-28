# Spec Delta

## ADDED Requirements

### Requirement: Manager approves litigation entries from the approval queue

The system SHALL show PENDING_APPROVAL account-level litigation entries in the manager approval queue, alongside approval-gated strategy actions, so a manager can reach them from one manager screen. The system SHALL let a manager approve or reject a pending litigation entry inline from that queue, reusing the same approve/reject semantics (manager-only, APPROVED or REJECTED) as the standalone decision flow. Non-manager users SHALL not see decision controls for litigation entries.

#### Scenario: Pending litigation entry appears in the approval queue

- **WHEN** a manager opens the approval queue and an account-level litigation entry is PENDING_APPROVAL
- **THEN** the queue surfaces the entry under a Litigation Entries view alongside any approval-gated strategy actions

#### Scenario: Inline approve from the queue

- **WHEN** a manager approves a pending litigation entry directly from the approval queue
- **THEN** the entry transitions to APPROVED and the account satisfies the Legal Action / Foreclosure gate

#### Scenario: Inline reject from the queue

- **WHEN** a manager rejects a pending litigation entry directly from the approval queue
- **THEN** the entry transitions to REJECTED and remains eligible to be re-raised

#### Scenario: Non-manager has no decision control

- **WHEN** a non-manager user views the approval queue containing pending litigation entries
- **THEN** the entries are not decidable by that user