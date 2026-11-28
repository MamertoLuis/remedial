# Tasks

## 1. Web image

- [x] 1.1 Write `Dockerfile` on a Python 3.12 base that installs/reconciles the pinned `3.12.12` and runs `uv sync --frozen` against `uv.lock` — verify the image reports Python `3.12.12` and passes `uv run python manage.py check`
- [x] 1.2 Add `.dockerignore` excluding `.git`, `.venv`, `db.sqlite3`, local env files, and build caches — verify a `docker build --no-cache` context excludes secrets and stays small
- [x] 1.3 Make the image serve the app: production settings, `collectstatic`, and a gunicorn `CMD` bound to the container port — verify `docker run` (production env) boots gunicorn and serves a page over the internal port

## 2. Compose and networking

- [x] 2.1 Write `compose.yaml` defining the web service and publish the app port **only to loopback** (`127.0.0.1:<port>:8000`) — verify `docker compose config` is valid and the port is not exposed publicly
- [x] 2.2 Pass all runtime config via environment (`DATABASE_URL`, `SECRET_KEY`, `ALLOWED_HOSTS`, optional `CSRF_TRUSTED_ORIGINS`/email, `MYSQL56_*`) sourced from the host — verify the app boots against an external-`DATABASE_URL` and enforces `ALLOWED_HOSTS`
- [x] 2.3 Confirm the container can reach the external read-only iAccs MySQL source — verify a `import_from_iaccs --dry-run` from the container reaches the source and returns rows (live source gated behind `IACCS_LIVE=1`)

## 3. Host-level edge

- [x] 3.1 Configure the host edge (nginx or Caddy) to terminate TLS on 80/443 and proxy to `127.0.0.1:<port>` with `X-Forwarded-For`/`X-Forwarded-Proto` set — verify `curl` through the edge serves the app over HTTPS with a valid cert and the Host allow-list is honored
- [x] 3.2 Document the edge proxy + TLS + cert-renewal as a committed reference under `deploy/` — verify the doc shows the new internal-port topology replacing the old `deploy/gunicorn.conf.py`/`nginx.conf` guidance

## 4. Disposable-box verification

- [x] 4.1 Prove statelessness: stop/remove the web container and `docker compose up` again — verify all durable data returns from external Postgres and none was lost
- [x] 4.2 Run the project's check/test gate against the built image (`manage.py check` and the test suite) and a deploy smoke test over the edge — verify checks and tests pass in the image and the site serves through the edge

## 5. One-shot demo posture (`--profile demo`)

- [x] 5.1 Add the demo posture as a merge fragment: `compose.demo.yaml` with `postgres` (a `demo-postgres-data` named volume, **no published port**) and `edge` (nginx listening on host port 80 proxying to `web:8000` with `X-Forwarded-For`/`X-Forwarded-Proto` set) plus web environment overrides (demo `DATABASE_URL`/`SECRET_KEY`/`ALLOWED_HOSTS`, `SEED_DEMO_ON_BOOT=1`) — verify `docker compose -f compose.yaml -f compose.demo.yaml config` is valid, the demo stack runs with **zero host env**, and plain `docker compose config` shows only `web`
- [x] 5.2 Wire DB readiness: postgres `healthcheck` + `web depends_on: condition: service_healthy` — verify the web container does not start its entrypoint until the database accepts connections
- [x] 5.3 Write `entrypoint.sh` in the web image: run `migrate` (always) and `collectstatic`, then `seed_demo --seed 42` only when `SEED_DEMO_ON_BOOT=1` — verify against a fresh demo stack that the app comes up **seeded** (10 demo accounts, demo users) after `docker compose --profile demo up -d`, and that setting the flag against a database with organic rows refuses loudly

## 6. Fresh-clone reproducibility and documentation

- [x] 6.1 Remove the `**/migrations/*.py` gitignore rule and commit the existing migrations — verify `git ls-files` covers every migration module and a fresh `git clone` + `migrate` builds the full schema (including the `source` provenance migration)
- [x] 6.2 Run the project's check/test gate against the built image for both postures (`manage.py check` and the test suite in the image; demo posture additionally serves a page through `edge`) — verify checks and tests pass in the image and the site serves through the edge in both postures
- [x] 6.3 Document both topologies under `deploy/` (production: web-only compose + external Database_URL + host edge; demo: `--profile demo` + in-stack postgres/edge + boot seeding) and add the `SEED_DEMO_ON_BOOT` guardrail to `.env.example` (never set in production) — verify the docs show both postures and the env example carries the warning

## Workflow follow-up

- Archive the change after the project's review requirements are satisfied.
- Verify the archived result.