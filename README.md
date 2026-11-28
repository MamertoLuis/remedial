# Remedial

Loan remedial management system built with Django: borrowers, loan accounts,
delinquency tracking, ECL provisioning, collection activities, remedial
strategies, compromise agreements, alerting and portfolio reporting.

## Requirements

- Python 3.12.12 (see `.python-version`)
- [uv](https://docs.astral.sh/uv/) for dependency management
- SQLite for local development; PostgreSQL for production
- On Linux, the PDF stack (`xhtml2pdf` → `svglib` → `rlpycairo` → `pycairo`)
  is built from source and needs the Cairo headers before `uv sync`:

  ```bash
  sudo apt-get install -y pkg-config libcairo2-dev
  ```

## Setup

```bash
cp .env.example .env      # fill in the values you need
uv sync                   # install dependencies from uv.lock
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

The app is served at <http://127.0.0.1:8000/>.

### User accounts and roles

Role assignment is restricted to the administrator. The user model enforces
the invariant `is_staff == (role == SYSTEM_ADMINISTRATOR)` in the Django admin
UI:

- Only System Administrator accounts hold `is_staff` (and usually
  `is_superuser`); the Account Officer, Manager, and Board Member roles are
  never staff and can never access `/admin/`.
- A role is assigned once at account creation and changed only through Django
  admin by the System Administrator. The self-service profile page
  (`/profile/`) edits only name and email and exposes no role control.

Two account-creation paths:

- `uv run python manage.py createsuperuser` — the SYSTEM_ADMINISTRATOR role is
  assigned automatically by data migration `0003` for superuser accounts.
- Django admin (Users → Add user) with the role set to System Administrator —
  `is_staff` is set automatically; saving an account whose role and `is_staff`
  disagree is rejected.

## Configuration

Settings are split by environment and selected with `DJANGO_SETTINGS_MODULE`:

| Module | Purpose |
|--------|---------|
| `remedial.settings.base` | Shared defaults |
| `remedial.settings.development` | Local development (`DEBUG=True`, SQLite) |
| `remedial.settings.production` | Deployed environment (env-driven, PostgreSQL) |

`manage.py` defaults to `remedial.settings.development`.

Production reads `.env` and **requires** `SECRET_KEY`, `DATABASE_URL` and
`ALLOWED_HOSTS` — startup fails if any of them is missing. Real environment
files are never committed; only `.env.example` is tracked.

## Common commands

```bash
uv run python manage.py check          # system checks
uv run python manage.py test           # test suite
uv run python manage.py import_borrowers <file.csv>
uv run python manage.py import_accounts <file.csv>
uv run python manage.py import_exposures --cutoff YYYY-MM-DD <file.csv>
```

CSV imports follow the `csv-import` contract (see
`openspec/specs/csv-import/spec.md`): the whole file is validated before any
row is written, dates are ISO `YYYY-MM-DD`, and columns that the system
derives — `status`, `classification`, `aging_bucket`, `npl_flag`, `npl_date`,
and exposure `days_past_due` — are rejected. Exposure imports compute days
past due from the iAccs repayment schedule, so they require the `MYSQL56_*`
connection and a `--cutoff` date. The legacy `load_delinquency_csv` command
was removed with this contract.

### CSV imports

Repository sample files compatible with the contract: `sample_borrowers.csv`,
`sample_accounts.csv`, and `sample_exposures.csv`. Import them in order
(borrowers → accounts → exposures) because accounts reference borrowers and
exposure `loan_id`s must already exist as loan accounts:

```bash
uv run python manage.py import_borrowers sample_borrowers.csv
uv run python manage.py import_accounts sample_accounts.csv
uv run python manage.py import_exposures --cutoff 2026-03-14 sample_exposures.csv
```

**Borrowers** — required: `borrower_id`, `full_name`; optional: `borrower_type`
(`PERSON`/`CORP`/`COOP`, default `PERSON`), `primary_address`, `mobile`,
`borrower_group`. Flags: `--skip-existing`, `--dry-run`.

**Accounts** — required: `loan_id`, `borrower_id`, `booking_date`,
`maturity_date`, `original_principal`, `interest_rate`, `loan_type`,
`account_officer_id`, `loan_security` (`SECURED`/`UNSECURED`); optional:
`transaction_type`. A `status` column is rejected: account status is always
derived from delinquency. The referenced `borrower_id` must already exist.
Flags: `--skip-existing`, `--dry-run`.

**Exposures** — required: `loan_id`, `as_of_date`, `principal_outstanding`,
`accrued_interest`, `accrued_penalty`; optional: `shouldbepay`, `actualpay`.
A `days_past_due` column is rejected: days past due is computed from the
iAccs repayment schedule through the read-only `MYSQL56_*` connection, so the
command also requires `--cutoff` (as-of date). Rows for an account/date that
already carries an iAccs-tagged snapshot are rejected. Flags: `--snapshot-type
EVENT|MONTH_END` (default `EVENT`), `--dry-run`.

All three commands validate the entire file first — exact headers, types,
referential integrity, within-file uniqueness — and write nothing when any
row is invalid (the exit code is non-zero). Re-importing an identical file is
idempotent: nothing changes and the command exits zero.

## Demo database

For a cloud-hosted, open-play demo the app ships a fake-data seeder that
provisions a complete demo database in one command (small and bounded, no
real data):

```bash
uv run python manage.py seed_demo [--seed 42]
```

It seeds role users, the foundational portfolio, and per-account exposure
timelines written **through the normal derivation cascade**, so account
status, NPL, escalation ladders, and ECL provisions are coherent — accounts
cross 90 DPD and become NPL, ladders open and cure, ECL tiers move.

Demo logins (password `demo-password-123` for all):

| Username | Role | Shows |
|---|---|---|
| `admin` | System Administrator | everything, admin UI |
| `demo-manager` | Manager | approval queue, litigation decisions |
| `demo-officer` | Account Officer | raising entries, escalations |
| `demo-board` | Board Member | portfolio reports |

Without `--seed` the generated values vary per run (open play); the same
`--seed` reproduces an identical database. Re-running replaces the demo data.

> **Fake-only guardrail**: `seed_demo` refuses to run when the database holds
> exposure or delinquency rows outside the demo portfolio, and real imports
> (`import_from_iaccs`, CSV imports) must never run on a demo host. The demo
> database is fabricated data only.

## Deployment

`deploy/gunicorn.conf.py` and `deploy/nginx.conf` contain the reference
Gunicorn/Nginx configuration. Nginx terminates TLS and forwards
`X-Forwarded-Proto: https`; Django trusts that header in production settings.

## Project layout

```
remedial/               Django project (settings, urls, wsgi/asgi)
account_master/         Core domain: borrowers, accounts, exposure,
                        delinquency, strategies, alerts, ECL services
compromise_agreement/   Compromise agreements and installment schedules
reporting/              Portfolio and loan-officer reports
users/                  Custom user model with roles
deploy/                 Gunicorn + Nginx reference configuration
```
