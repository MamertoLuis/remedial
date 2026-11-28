# demo-data Specification

## Purpose

Provisions a complete fake demo database in one step: role users and a small portfolio of accounts whose delinquency, status, escalation, and ECL states are produced through the normal derivation cascade, so a cloud demo behaves like production while holding bounded, fake-only data.

## Requirements

### Requirement: One command seeds the demo database

The system SHALL expose a `seed_demo` management command that, on a fresh database, creates the demo role users, the foundational portfolio, and each account's exposure timeline in one run. Re-running the command SHALL replace only the artifacts it created, leaving no duplicates. An optional `--seed` integer SHALL make the generated values reproducible.

#### Scenario: Fresh database seeded in one run
- **WHEN** `seed_demo` runs on a database with no real data
- **THEN** the demo users, accounts, and timelines exist after the single command

#### Scenario: Re-run replaces without duplicates
- **WHEN** `seed_demo` runs a second time on the same database
- **THEN** the seeded artifacts are replaced and no duplicate accounts or users accumulate

#### Scenario: Seeded run is reproducible
- **WHEN** `seed_demo` runs twice with the same `--seed` value
- **THEN** the two databases hold identical generated values

### Requirement: Account state is produced by the derivation cascade

The system SHALL drive each account's exposure timeline through the normal service cascade, so account status, classification, NPL flag, escalation ladder, and ECL provisions are derived from the seeded days-past-due snapshots rather than hardcoded. The last snapshot SHALL be the account's displayed state.

#### Scenario: Delinquency crosses into NPL
- **WHEN** a seeded account's timeline passes 90 days past due
- **THEN** its derived status becomes NPL, the ladder opens, and the ECL tier reflects the derived classification

#### Scenario: Cure closes the ladder
- **WHEN** a seeded account's timeline returns to zero days past due after being delinquent
- **THEN** the account returns to a performing state and the ladder is recorded as cured

### Requirement: Designed account narratives

The seeded portfolio SHALL include accounts that follow distinct designed narratives — a performing account, a deteriorating account, a cured account, a chronic NPL account, a written-off account, and an account with an approved litigation entry — so open-play exploration shows a realistic mix.

#### Scenario: Portfolio shows a designed mix
- **WHEN** a visitor browses the seeded portfolio
- **THEN** accounts exhibit the different narrative states rather than a uniform profile

### Requirement: Demo role users

The system SHALL create demo users for every production role — account officer, manager, board member, and system administrator — with deterministic, documented credentials, so role-gated screens are demonstrable.

#### Scenario: Manager screens are reachable
- **WHEN** a visitor signs in as the demo manager
- **THEN** manager-only areas such as the approval queue are accessible

### Requirement: Bounded fake-only dataset

The demo dataset SHALL contain only fabricated data, bounded to a small fixed portfolio size and a fixed number of snapshots per account, to keep resource use low and avoid any real personal or exposure data.

#### Scenario: Portfolio size is bounded
- **WHEN** `seed_demo` completes
- **THEN** the number of borrowers, accounts, and snapshots per account is fixed and small

### Requirement: Demo database stays organic-data-free

The `seed_demo` command SHALL refuse to run when any iAccs-sourced exposure or delinquency record exists, and the project documentation SHALL state that real imports never run on a demo host.

#### Scenario: Refusal when real data exists
- **WHEN** `seed_demo` runs on a database holding iAccs-tagged rows
- **THEN** it refuses with a clear message and writes nothing