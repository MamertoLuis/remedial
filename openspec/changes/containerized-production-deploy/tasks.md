# Tasks

## 1. Web image

- [ ] 1.1 Write `Dockerfile` on a Python 3.12 base that installs/reconciles the pinned `3.12.12` and runs `uv sync --frozen` against `uv.lock` — verify the image reports Python `3.12.12` and passes `uv run python manage.py check`
- [ ] 1.2 Add `.dockerignore` excluding `.git`, `.venv`, `db.sqlite3`, local env files, and build caches — verify a `docker build --no-cache` context excludes secrets and stays small
- [ ] 1.3 Make the image serve the app: production settings, `collectstatic`, and a gunicorn `CMD` bound to the container port — verify `docker run` (production env) boots gunicorn and serves a page over the internal port

## 2. Compose and networking

- [ ] 2.1 Write `compose.yaml` defining the web service and publish the app port **only to loopback** (`127.0.0.1:<port>:8000`) — verify `docker compose config` is valid and the port is not exposed publicly
- [ ] 2.2 Pass all runtime config via environment (`DATABASE_URL`, `SECRET_KEY`, `ALLOWED_HOSTS`, optional `CSRF_TRUSTED_ORIGINS`/email, `MYSQL56_*`) sourced from the host — verify the app boots against an external-`DATABASE_URL` and enforces `ALLOWED_HOSTS`
- [ ] 2.3 Confirm the container can reach the external read-only iAccs MySQL source — verify a `import_from_iaccs --dry-run` from the container reaches the source and returns rows (live source gated behind `IACCS_LIVE=1`)

## 3. Host-level edge

- [ ] 3.1 Configure the host edge (nginx or Caddy) to terminate TLS on 80/443 and proxy to `127.0.0.1:<port>` with `X-Forwarded-For`/`X-Forwarded-Proto` set — verify `curl` through the edge serves the app over HTTPS with a valid cert and the Host allow-list is honored
- [ ] 3.2 Document the edge proxy + TLS + cert-renewal as a committed reference under `deploy/` — verify the doc shows the new internal-port topology replacing the old `deploy/gunicorn.conf.py`/`nginx.conf` guidance

## 4. Disposable-box verification

- [ ] 4.1 Prove statelessness: stop/remove the web container and `docker compose up` again — verify all durable data returns from external Postgres and none was lost
- [ ] 4.2 Run the project's check/test gate against the built image (`manage.py check` and the test suite) and a deploy smoke test over the edge — verify checks and tests pass in the image and the site serves through the edge

## Workflow follow-up

- Archive the change after the project's review requirements are satisfied.
- Verify the archived result.