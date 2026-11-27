# Tasks

## 1. Data Model Foundation

- [ ] 1.1 Add `Guarantor` model (account FK, identity, guarantee amount, guarantee type, enforceability) in `account_master`; verify migrations create the table and model tests cover create/read
- [ ] 1.2 Add `Collateral` model (account FK, description, type, appraised value, as-of date) in `account_master`; verify migrations and a model test
- [ ] 1.3 Add `StrategyAssessment` model (strategy one-to-one, as_of_date, officer rationale, structured judgment fields for financial condition/willingness to pay/recovery assessment with notes, copied delinquency/exposure/collection-history summary values); verify migrations and snapshot-preservation test (spec: `strategy-assessment` "Snapshot re-captured on escalation" / "Prior snapshot remains unchanged")
- [ ] 1.4 Add `StrategyActionCatalogEntry` template model (strategy_type, code, name, ordering, `requires_approval`); verify migrations and a test that the six strategy types each expose catalog entries (spec: `strategy-actions` "Each strategy type provides an action catalog")
- [ ] 1.5 Add `StrategyAction` instance model (catalog_entry FK, strategy FK, status, assignee, due_date, outcome) with the status machine from design D3; verify status-transition tests cover SELECTED→PENDING_APPROVAL→APPROVED/REJECTED→EXECUTED/SKIPPED and non-gated direct execution (specs: `strategy-actions` "Selected actions are tracked", "Approval-gated actions await manager approval")
- [ ] 1.6 Add `StrategyApproval` model (action FK, approver, decision, decided_at, comments, conditions); verify tests that only an APPROVED record releases a gated action and that conditions are stored (spec: `strategy-actions` "Approval records carry conditions")
- [ ] 1.7 Add `UNSUCCESSFUL` to `CompromiseAgreement` statuses and gate agreement activation on approval under the new flow while preserving existing ACTIVE agreements; verify migration is additive and existing-agreement tests still pass (spec: `strategy-lifecycle` "Officer-declared failure and agreement rescind")

## 2. Catalog Seeding

- [ ] 2.1 Add data migration seeding the six action catalogs from the proposal's action lists (Intensive Collection, Restructuring, Compromise, Collateral Recovery, Legal Action, Write-Off) with correct `requires_approval` flags; verify seeded counts match the proposal lists and every approval-gated classification follows D3's rule
- [ ] 2.2 Register catalog, action, approval, assessment, guarantor, and collateral models in Django admin; verify each is browsable and editable in admin with no broken URLs

## 3. Strategy Service (Transitions & Side Effects)

- [ ] 3.1 Create `strategy_service` module and implement recommendation creation: strategy created ACTIVE with a required `StrategyAssessment`, one ACTIVE per account preserved; verify unit tests per spec (`strategy-lifecycle` "Recommendation activates the strategy", "Competing active strategy is not permitted", `strategy-assessment` "Recommendation requires an officer rationale")
- [ ] 3.2 Implement action selection and execution rules: gated actions blocked from execution until approved, non-gated actions executed directly; verify tests (`strategy-actions` "Gated action cannot be executed before approval", "Officer executes a non-gated action directly")
- [ ] 3.3 Implement approval workflow: MANAGER-only approve/reject, BOARD_MEMBER read-only; verify permission tests for both roles (`strategy-actions` "Manager is the sole approver", "Board member views without deciding")
- [ ] 3.4 Implement officer failure declaration: agreement strategies mark agreement UNSUCCESSFUL and open the rescind action; approve → agreement RESCINDED + strategy CANCELLED, reject → unchanged; non-agreement strategies cancel directly with outcome; verify tests for all three scenarios of `strategy-lifecycle` "Officer-declared failure and agreement rescind"
- [ ] 3.5 Implement remaining approval side effects: approved write-off action sets account WRITEOFF; approved compromise settlement activates the agreement; verify service tests per design D6/D7

## 4. Lifecycle Gates & Escalation

- [ ] 4.1 Enforce entry gates at strategy creation: Legal Action allowed on (ladder CLOSED with reason TERMINAL) OR (approved rescind); Foreclosure additionally requires SECURED; otherwise blocked; verify tests (`strategy-lifecycle` "Entry gates for Legal Action and Foreclosure")
- [ ] 4.2 Update escalation close handling so an arrangement rescind never reopens a closed ladder; verify test per `notice-escalation-ladder` "Rescinded arrangement keeps the ladder closed"
- [ ] 4.3 Implement completion transitions per strategy type (cure, schedule honored, fully paid, liquidated, judgment/closure, write-off booked); verify tests (`strategy-lifecycle` "Strategy completes only on its type's completion condition")
- [ ] 4.4 Implement escalation: next recommendation allowed only after exit, recording a fresh assessment; verify tests (`strategy-lifecycle` "Escalation follows exit", `strategy-assessment` "Snapshot re-captured on escalation")

## 5. UI & Permissions

- [ ] 5.1 Add assessment capture to the strategy creation flow (seven inputs, rationale, structured scales); verify creating a strategy requires an assessment and the recommendation reflects the snapshot date
- [ ] 5.2 Extend strategy detail with action selection/execution (catalog menu, statuses, assignee, outcome) and show approval state; verify an officer can select and execute non-gated actions and that gated ones sit pending approval
- [ ] 5.3 Add manager approval queue (pending gated actions with conditions entry) and approve/reject actions; verify end-to-end via an authenticated MANAGER user walkthrough
- [ ] 5.4 Apply permission gating: BOARD_MEMBER sees read-only strategy pages; verify non-managers cannot approve via views API tests
- [ ] 5.5 Refine strategy type display labels to the six recommended names (stored values unchanged); verify labels render on list/detail pages and no stored value changes in migration

## 6. Integration Verification

- [ ] 6.1 Add one end-to-end integration test: recommend → assessment → select actions → approve gated action → execute → officer declares failure → rescind approved → escalate to next strategy with fresh assessment; verify the full flow passes (covers all four spec deltas)
- [ ] 6.2 Run `make audit`, full test suite, and `openspec validate` on the change; verify the change validates (non-strict at minimum) and every test passes with no regressions

## Workflow follow-up

- After implementation and review, archive the change with `/opsx-archive` and verify the archived result.
