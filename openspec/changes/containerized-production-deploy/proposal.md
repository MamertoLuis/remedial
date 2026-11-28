# Proposal

## Why

Production deployment currently depends on hand-configured nginx and systemd units on a single server, which is error-prone and impossible to reproduce on a replacement box. Containerizing the web app makes the server disposable: any fresh box rebuilds from the repo with a single `docker compose up`, while an external Postgres keeps production data safe from box loss. A second, one-shot **demo posture** (`--profile demo`) brings up the whole stack — web, in-stack Postgres, and an internal edge proxy — with a seeded fake database, for cloud demos and trials.

## What Changes

- Add a `Dockerfile` (Python 3.12.12, uv-managed install) and `compose.yaml` packaging the web app (gunicorn + Whitenoise). Static assets are already committed, so no build stage is needed in the image.
- **Two compose postures**: base `compose.yaml` (web container only, no runtime defaults — production posture) plus a `compose.demo.yaml` merge fragment that adds `postgres` (named volume, internal-only port) and `edge` (nginx on port 80) and overrides web's environment with demo values for a one-shot demo stack. `docker compose up -d` = production; `docker compose -f compose.yaml -f compose.demo.yaml up -d` = demo. No TLS in the demo stack — certificates stay host-level in both postures.
- Publish only an internal app port; TLS termination and certificates remain on a **host-level edge** (host nginx or Caddy) outside the container stack.
- Configure the app entirely through the environment (`DATABASE_URL`, `SECRET_KEY`, `ALLOWED_HOSTS`); the web container persists **no state** on its filesystem.
- **Postgres**: external/managed for the production posture (the existing invariant — durable data survives box loss); in-stack with a `demo-postgres-data` volume for the demo posture, whose data is disposable by design.
- **First-boot demo seeding**: web `entrypoint` always runs `migrate` (idempotent), then `seed_demo --seed 42` only when `SEED_DEMO_ON_BOOT=1` (demo posture only; never set in production). The `demo-data` organic guard refuses a non-empty database, so the flag cannot seed a real DB.
- **Migrations become tracked**: the `**/migrations/*.py` gitignore rule is removed so a fresh `git clone` carries the schema history (including the `source` provenance migration) and `migrate` can build the database in either posture. **BREAKING** for the previous policy of regenerating migrations per environment.
- Keep the external read-only **iAccs MySQL** source unchanged, reachable from the container network.
- Add no background workers (Celery/Redis stay unwired in dependencies).
- Document both topologies and the no-state-on-the-box invariant.

## Capabilities

### New Capabilities

- `application-deployment`: durable runtime contract of the deployed application — a stateless web service that serves its own static assets over HTTP and persists durable state only through the configured database.

### Modified Capabilities

- (none — end-user behavior is unchanged; this change is deployment topology plus its runtime contract.)

## Impact

- **Code**: new build/deploy artifacts (`Dockerfile`, `compose.yaml` with a `demo` profile, `entrypoint.sh`, `.dockerignore`, production `.env` example) and updates to `deploy/` reference documentation for both postures.
- **Dependencies**: base-image/build strategy to honor the pinned `Python 3.12.12`; no new runtime packages.
- **Systems**: replaces hand-wired nginx→gunicorn/systemd app process management; the host-level edge still terminates TLS; external Postgres and iAccs MySQL sources are unaffected in the production posture.
- **Repo policy**: migrations switch from per-environment regeneration to being versioned in git (gitignore change), so a fresh clone can build the schema.
- **Operations**: the server becomes disposable; durable data lives in externally-hosted Postgres (production) or a disposable named volume (demo).