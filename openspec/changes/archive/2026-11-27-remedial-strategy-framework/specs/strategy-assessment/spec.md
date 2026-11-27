# Spec Delta

## Purpose

Records the decision inputs that justify a remedial strategy recommendation for a delinquent account, frozen at decision time and re-captured on every escalation.

## ADDED Requirements

### Requirement: Assessment snapshot captures the seven decision inputs

The system SHALL record, for each strategy recommendation, an assessment snapshot dated as of the recommendation that captures delinquency (days past due, aging bucket, classification), outstanding exposure, borrower financial condition, willingness to pay, guarantor information, a collection history summary, and a recovery assessment, together with the recommending officer's rationale.

#### Scenario: Snapshot recorded on recommendation

- **WHEN** a loan officer recommends a remedial strategy for an account
- **THEN** the system records an assessment snapshot for that recommendation carrying all seven decision inputs as of the recommendation date

#### Scenario: Delinquency and exposure reflected as of the snapshot date

- **WHEN** an assessment snapshot is recorded for an account
- **THEN** its delinquency and outstanding exposure values reflect the account's records as of the snapshot date

#### Scenario: Recommendation requires an officer rationale

- **WHEN** a loan officer recommends a remedial strategy without providing a rationale
- **THEN** the system rejects the recommendation and requires a rationale before the strategy can be created

### Requirement: Structured judgments for subjective inputs

The system SHALL capture borrower financial condition, willingness to pay, and recovery assessment as structured judgments chosen from ordered scales, each with an optional supporting note, rather than free text only.

#### Scenario: Willingness to pay recorded on an ordered scale

- **WHEN** a loan officer records the borrower's willingness to pay on an assessment
- **THEN** the system stores a value from an ordered scale (for example HIGH, MEDIUM, LOW) with any supporting note provided

#### Scenario: Recovery assessment records expected recovery

- **WHEN** a loan officer records a recovery assessment on an assessment
- **THEN** the system stores the expected recovery value or outcome judgment and the basis for it

### Requirement: Guarantor captured as a data entity

The system SHALL record guarantor information for an assessment as data entities carrying the guarantor's identity, the guarantee amount, and the type of guarantee.

#### Scenario: Guarantor details recorded on the assessment

- **WHEN** a loan officer records a guarantor for an account's assessment
- **THEN** the system stores the guarantor's identity, the guarantee amount, and the guarantee type

### Requirement: Snapshot re-captured on escalation

The system SHALL create a fresh assessment snapshot whenever a new strategy is recommended for an account after a previous strategy exited, and SHALL preserve prior snapshots unchanged for history.

#### Scenario: Escalated account gets a fresh snapshot

- **WHEN** a new strategy is recommended for an account whose previous strategy has exited
- **THEN** the system records a new assessment snapshot dated as of the new recommendation

#### Scenario: Prior snapshot remains unchanged

- **WHEN** a new assessment snapshot is recorded for an account
- **THEN** any previously recorded snapshot for that account remains intact and attributable to its original recommendation
