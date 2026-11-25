# Proposal

## Why

Workflow 1 of the intended recovery process — the **notice / escalation ladder** — does not exist in the system. Today `CollectionActivityLog` is a flat log where a "Demand Letter" is merely another row; there is no positioned, timed escalation: no notion of which severity stage an account is at, no computed due date for the next notice, and no enforcement when an officer lets the next notice slip. Officers need a guided, timed ladder — notice follows notice at a configured duration, severity climbs with each step, and the ladder terminates by recommending Legal Action or Foreclosure — so delinquent accounts are escalated deterministically instead of at the discretion of memory.

## What Changes

- Add a new **notice escalation ladder** in the judgment plane (mirrored core facts — `Borrower`, `LoanAccount`, `Exposure`, derived delinquency/status — are untouched; a snapshot still only refreshes the account's status, never an officer's escalation work).
- Introduce three new records:
  - `EscalationStage` — the fixed ladder template: ordered stages (e.g., First Demand → Warning → Legal Intent), each with a label, a duration (days) until the next notice, and a terminal flag. Stages are fixed, with durations configurable per stage.
  - `EscalationState` — one position record per account: current stage, stage started on, `next_notice_due`, and status `PENDING | ACTIVE | PAUSED | CLOSED` with a close reason.
  - `Notice` — history of issued notices: account, stage, issued on, method, issuing officer.
- **Officer-driven advancement only**: the system never fires a notice itself. An officer issues a notice; the system computes `next_notice_due = issued_on + duration(stage)` and surfaces the due/overdue state through the existing alert engine (reusing the `COLLECTION_INACTIVITY` rule type) as a prompt, not an automatic action.
- **Ladder lifecycle rules** (confirmed business rules):
  - Starts when an account becomes delinquent (mirrored fact).
  - **Pauses only on PTP**: while a promise-to-pay is pending on the contact log, the ladder state is `PAUSED`; it resumes at the *same* stage. Honored/broken PTP is recorded on the contact log and has **no** effect on the ladder (a single honored promise may not clear the delinquency in full).
  - **Ends only on cure / agreement / terminal stage**: an account returning to performing, an approved compromise/restructuring arrangement, or the officer reaching the terminal stage and creating a `Legal Action` / `Foreclosure` `RemedialStrategy` closes the ladder.
- Terminal-stage recommendation creates an ACTIVE `RemedialStrategy` of type Legal Action or Foreclosure through the existing strategy machinery (so the existing "one active strategy" invariants apply).
- Alerts: a past-due `next_notice_due` produces an alert (e.g., "next notice overdue") through the existing `AlertRule`/`Alert` machinery; no job queue is introduced — evaluation happens on officer workflow events and the alert refresh path.

## Capabilities

### New Capabilities

- `notice-escalation-ladder`: Owns the timed, officer-issued escalation ladder for delinquent accounts — stage template, per-account position and lifecycle (PENDING/ACTIVE/PAUSED/CLOSED), computed next-notice due dates, PTP pause, cure/agreement/terminal termination, and the terminal recommendation that creates a Legal Action or Foreclosure strategy.

### Modified Capabilities

- None. Existing capability requirements (`account-upsert`, `strategy-compromise-supersede`) are unchanged; the ladder composes with the strategy machinery without altering its requirements.

## Impact

- `account_master`: three new models (`EscalationStage`, `EscalationState`, `Notice`), service functions for ladder transitions (start, advance/issue, pause/resume on PTP, close on cure/agreement/terminal), alert hooks for due/overdue `next_notice_due`, admin registration, and officer-facing views to issue notices and view the ladder. No schema changes to existing mirrored/models (`Borrower`, `LoanAccount`, `Exposure`, `DelinquencyStatus`) — the mirror plane is deliberately untouched.
- `compromise_agreement`: read-only integration — an approved agreement is one of the ladder's close triggers (no requirement change).
- Alert engine: reuse of existing `ALERT`/`ALERT_RULE` machinery for the "next notice due/overdue" prompt; no new notification channels.
- No new dependencies; no job queue/scheduler. Celery remains unused.
