# Remedial — Demo User Manual

A guided tour of the Remedial loan-remedial-management demo, written for
everyone who will sit in front of it — from the person running the server to
the board member reviewing reports.

The demo runs on **fake data only**: 10 fabricated borrowers and loan accounts
whose delinquency, status, and provisions are produced by the same rules the
production system uses. Nothing here is real, and nothing real should ever be
loaded into it (see "Running the demo" below).

---

## 1. Logging in

The demo has four login accounts — one per production role. The password is
the same for all of them:

| Username | Role | See it to demo |
|---|---|---|
| `admin` | System Administrator | The admin site, full control panel |
| `demo-officer` | Account Officer | Day-to-day loan work: escalations, litigation, strategies, collection |
| `demo-manager` | Manager | Approvals: the approval queue, litigation decisions |
| `demo-board` | Board Member | Portfolio reports and analysis |

Every account signs in from the login page with `demo-password-123`.

> If you are the person hosting the demo, see **Section 8** for how to (re)seed
> the database and reset passwords.

---

## 2. The vocabulary you will see (plain-language glossary)

Medium-technical terms appear all over the screens. Here is what they mean:

- **Days past due (DPD)** — how many days the borrower is late on the
  scheduled repayment. Drives everything else.
- **Aging bucket** — a range label for lateness: `Current`, `1-30`, `31-60`,
  `61-90`, `91-120`, `121-180`, `181-360`, `Over 360`.
- **Classification** — a credit-grade code derived from DPD: `C` (current),
  `SM` (specially mentioned / watchlist), `SS` (substandard), `D` (doubtful),
  `L` (loss).
- **Account status** — the account-level state shown everywhere.
  The ladder:
  `PERFORMING` (fine) → `PAST_DUE` (late) → `NPL` (non-performing, over 90
  days late) → `WRITEOFF` / `CLOSED`. Status is **derived** from DPD, never
  typed in by hand.
- **NPL** — "non-performing loan": over 90 days past due.
- **ECL provision** — the Expected-Credit-Loss reserve the system books for a
  loan. It is calculated from the classification and the outstanding balance,
  tier by tier: performing loans reserve little, loss loans reserve 100%.
- **Escalation ladder** — a per-account collection track. An account *starts*
  the ladder when it becomes delinquent, moves through stages as notices are
  issued, and *closes* when cured, an arrangement is approved, or it reaches
  the terminal stage.
- **Remedial strategy** — a formal plan for a troubled account (e.g.
  Restructuring, Compromise, Legal Action, Foreclosure) that then drives a
  list of actions to execute.
- **Litigation entry** — an account-level record that a loan is going to
  legal action. An officer raises it; a manager approves or rejects it.
- **Compromise agreement** — a negotiated repayment arrangement (with an
  installment schedule) for a struggling borrower.
- **Alert** — a rule-driven flag (e.g. a large account just turned NPL) that
  shows on the alerts screen until acknowledged or resolved.

---

## 3. The parts every user shares

These are available to all four roles from the top navigation bar.

**Dashboard** — the landing page. Shows portfolio totals by status
(`PERFORMING` / `PAST_DUE` / `NPL` / `WRITEOFF` / `CLOSED`), a "needs
attention" list (recently delinquent or NPL accounts), and quick links.

**Search** — the search box in the header. Type a loan ID (e.g. `ACC002`),
a borrower name, or a borrower ID (e.g. `BRW001`) to jump straight to the
account or borrower.

**Borrowers & Accounts** — table views of the whole portfolio. Every row links
to a detail page:

- **Account detail** is the heart of the demo. It shows the borrower, loan
  terms, current status, the latest exposure (balance + DPD), the ECL
  provision, the delinquency history chart/table, the escalation ladder panel,
  remedial strategies, collection activities, and any litigation entry.
- **Borrower detail** shows the person/company profile and their loans.

**Compromise Agreements** — the list of negotiated repayment arrangements
(which accounts have one, approval level, status, installment schedules).

**Alerts** — the flag list with acknowledge / resolve / dismiss actions.

**Profile** — self-service name/email editing (no role changes here).

> A note on permissions: any user can *look* — dashboards, lists, details,
> reports. Only specific role holders can *act* (raise, decide, approve,
> edit). If a button is missing, you are seeing exactly what your role allows.

---

## 4. System Administrator (`admin`)

The admin is the setup role. Two surfaces exist:

**The Django admin site** (`/admin/` after logging in as `admin`) — the
"behind the scenes" panel:
- **Users**: create, edit roles, and reactivate demo accounts. The system
  enforces `is_staff` matching the System Administrator role — you cannot
  accidentally make an officer staff.
- **All models**: borrowers, accounts, exposures, delinquency, strategies,
  alerts, ECL history — browse and correct anything.

**The in-app control panel** (only the admin sees the create/edit buttons):
- **Create borrowers and accounts** — the entry point for the demo portfolio.
- **Update accounts** — edit loan terms and status after they are created.
- **Record exposures and delinquency manually** — where an operator would
  correct a snapshot by hand (the demo normally relies on the seeder).

**ECL generation** — regenerate the provisioning for an account from its
delinquency data; useful to show how provisions react to a data change.

> Demo tip: point out that the role invariant is enforced — officers/managers
> simply cannot reach the admin site.

---

## 5. Account Officer (`demo-officer`)

The officer is the working role: the person who watches the portfolio and
starts the remediation wheels turning.

**Day-to-day screens**
- Dashboard + *needs attention* list — where the day starts.
- Account and borrower detail pages — the story of each loan.
- **Collection activities** — log a follow-up call/visit on an account
  (activity type, staff, next action date, optional promise-to-pay).

**The escalation ladder** (per account)
- Open an account's **Escalation Ladder** panel and then **Issue Notice** to
  move a delinquent account through the track. The ladder shows the current
  stage and when the next notice is due.
- The demo's `ACC003` is the *cured* story: notice how the ladder closed with
  reason **cured** once the account returned to performing.

**Remedial strategies**
- **Create / update a strategy** for an account (recommending Restructuring,
  Compromise, Legal Action, or Foreclosure) and open its detail page.
- Each strategy carries **actions**. You can **select** which actions belong
  to the plan and, once they are approved, **execute** them and attach
  evidence (a dated note) to each.
- The Legal Action / Foreclosure **entry gate** is worth showing: the system
  refuses such a recommendation until the account has a terminal ladder, an
  approved rescind, or (in this demo) an **approved litigation entry**.

**Litigation entries** (the demo's officer flow)
- On a troubled account (try `ACC006`), click **Raise Litigation Entry**.
- Fill in the target (Legal Action or Foreclosure), the litigation start
  date, and the officer's rationale.
- The entry is created `PENDING_APPROVAL` — it is **never** auto-derived from
  delinquency, and only one active entry may exist per account.
- Hand over to the manager (Section 6) to approve or reject it.

> Demo tip: `ACC006` already has an approved litigation entry from the
> seeder — the Legal Action gate on that account reads as *satisfied*.

---

## 6. Manager (`demo-manager`)

The manager is the approval role. One screen ties it together:

**The Approval Queue** — the single manager hub, with two tabs:

- **Strategy Approvals** — pending strategy actions awaiting the manager's
  yes/no before an officer can execute them.
- **Litigation Entries** — pending litigation entries waiting for a decision.

**Litigation decisions (two ways)**
1. **Inline from the queue** — on the Litigation Entries tab, each pending
   entry has Approve / Reject buttons with a **decision notes** field.
   Approving moves the entry to `APPROVED` (and the account satisfies the
   Legal Action / Foreclosure gate); rejecting moves it to `REJECTED`
   (the officer may raise a fresh one).
2. **Standalone decision page** — a manager can also open an entry directly
   and decide there. Both paths land back on the approval queue.

**Escalation oversight** — view account ladders: which are `ACTIVE`, which
are `PAUSED` (a promise-to-pay is open), which closed and why.

> Demo tip: after approving an entry on `ACC006`-style accounts, show the
> account detail again — the strategy gate now accepts a Legal Action
> recommendation.

---

## 7. Board Member (`demo-board`)

The board role is read-only and reports-centric. The **Reports** menu carries
five analyses, all built from the demo data:

1. **Loan Portfolio Breakdown** — the book by product/status.
2. **Past Due Aging Summary** — how deep the lateness runs (the aging buckets).
3. **NPL Portfolio Analysis** — the non-performing slice, by classification.
4. **Top 20 NPL Accounts** — who is driving the NPL number (expect
   `ACC002`, `ACC004`, `ACC006`, `ACC010` among them).
5. **Loan Officer Performance Summary** — how the demo officers' books look.

Also available: the **portfolio summary** (portfolio-level totals), **alerts**
(the portfolio's red flags), and the dashboard's portfolio-by-status bar.

> Demo tip: the seeded mix is deliberately varied — a reviewer sees current
> loans, watchlist names, NPL names, a written-off account (`ACC005`), and a
> cured story (`ACC003`), so every report has something to show.

---

## 8. Running and refreshing the demo (for the host)

**Fresh start (after a database wipe):**

```bash
uv run python manage.py migrate
uv run python manage.py seed_demo --seed 42
```

- `--seed` makes the generated values reproducible — rerun with the same
  number and you get the same database. Omit it for random variety.
- Re-running `seed_demo` is safe: it replaces only the demo data it owns
  (no duplicates accumulate) and **refuses to run** if it detects exposures or
  delinquency rows for accounts outside the demo set.

**Demo logins** are reset to `demo-password-123` on every seed run.

**One hard guardrail:** the demo database is fake-only. Never run
`import_from_iaccs` or the CSV import commands on it — `seed_demo` is the only
seeder it accepts.

**Where the demo data came from** — the seeder writes 16 weekly snapshots per
account *through the same derivation cascade as production*, so status, NPL,
escalation ladders, and ECL provisions all move on their own:

| Account | Story (arc) | Ended as |
|---|---|---|
| `ACC001` | healthy | PERFORMING |
| `ACC002` | deteriorating (0 → 120 DPD) | **NPL** — ladder open |
| `ACC003` | delinquent then cured | PERFORMING — ladder closed (cured) |
| `ACC004` | chronic NPL (plateau ~240 DPD) | **NPL** |
| `ACC005` | charged off | **WRITEOFF** |
| `ACC006` | in litigation | **NPL** + approved litigation entry |
| `ACC007` | healthy | PERFORMING |
| `ACC008` | deteriorating | **NPL** |
| `ACC009` | cured | PERFORMING |
| `ACC010` | chronic NPL | **NPL** |

---

## 9. Quick troubleshooting

| Symptom | What it means | Fix |
|---|---|---|
| "403 - not authorized" / missing buttons | The role gate is working | Sign in with the matching role from the login table |
| Can't reach `/admin/` | `is_staff`/role invariant | Only `admin` has staff access |
| Notices / ladder unchanged | Ladder needs *Issuing a notice* through the account's escalation panel | Use `demo-officer` |
| ECL looks stale | Provision reprojects only when delinquency changes | Trigger a delinquency refresh on the account (admin screen) or re-seed |
| Data looks different than a handout | Seeder was run without (or with a different) `--seed` | Re-run `seed_demo --seed 42` for the canonical demo |