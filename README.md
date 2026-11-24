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
uv run python manage.py import_accounts --skip-existing <file.csv>
uv run python manage.py import_exposures <file.csv>
```

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
