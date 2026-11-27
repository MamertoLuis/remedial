# Proposal

## Why

Production deployment currently depends on hand-configured nginx and systemd units on a single server, which is error-prone and impossible to reproduce on a replacement box. Containerizing the web app makes the server disposable: any fresh box rebuilds from the repo with a single `docker compose up`, while an external Postgres keeps production data safe from box loss.

## What Changes

- Add a `Dockerfile` (Python 3.12.12, uv-managed install) and `compose.yaml` packaging the web app (gunicorn + Whitenoise). Static assets are already committed, so no build stage is needed in the image.
- Publish only an internal app port; TLS termination and certificates remain on a **host-level edge** (host nginx or Caddy) outside the container stack.
- Configure the app entirely through the environment (`DATABASE_URL`, `SECRET_KEY`, `ALLOWED_HOSTS`); the web container persists **no state** on its filesystem.
- Keep **Postgres external/managed**, reached solely via `DATABASE_URL`, so survives a disposable box.
- Keep the external read-only **iAccs MySQL** source unchanged, reachable from the container network.
- Add no background workers (Celery/Redis stay unwired in dependencies).
- Document the topology and the no-state-on-the-box invariant.

## Capabilities

### New Capabilities

- `application-deployment`: durable runtime contract of the deployed application — a stateless web service that serves its own static assets over HTTP and persists durable state only through the configured database.

### Modified Capabilities

- (none — end-user behavior is unchanged; this change is deployment topology plus its runtime contract.)

## Impact

- **Code**: new build/deploy artifacts (`Dockerfile`, `compose.yaml`, `.dockerignore`, production `.env` example) and updates to `deploy/` reference documentation.
- **Dependencies**: base-image/build strategy to honor the pinned `Python 3.12.12`; no new runtime packages.
- **Systems**: replaces hand-wired nginx→gunicorn/systemd app process management; the host-level edge still terminates TLS; external Postgres and iAccs MySQL sources are unaffected.
- **Operations**: the server becomes disposable; durable data lives in externally-hosted Postgres.