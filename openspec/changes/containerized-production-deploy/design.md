# Design

## Context

The web app today runs hand-configured on a single server: a host nginx terminates TLS and reverse-proxies to gunicorn on `127.0.0.1:8000`, managed via systemd. Dependencies are fully pinned by `uv` (`uv.lock`), Python is pinned to exactly `3.12.12`, `app.css` (Tailwind output) is committed, static is served by Whitenoise, there are no `MEDIA`/file uploads, and Celery/Redis are in dependencies but not wired up. Production settings (`remedial.settings.production`) are entirely env-driven: `DATABASE_URL`, `SECRET_KEY`, `ALLOWED_HOSTS`, plus optional `CSRF_TRUSTED_ORIGINS`/email vars. The app reads an external read-only iAccs MySQL source (`MYSQL56_*`) for sync.

The goal is a **disposable** production box: rebuild from git + compose, with all durable data surviving box loss. See `proposal.md` for the why; the `application-deployment` spec pins the runtime contract.

## Goals / Non-Goals

**Goals:**
- Reproduce the whole web app from the repo via a single `docker compose up` on a fresh box.
- Keep the web process stateless: no durable data on its filesystem (no media, no worker state).
- Preserve the no-state-on-the-box invariant by keeping Postgres external/managed, reached via `DATABASE_URL`.
- Keep TLS/ceritificates on a host-level edge (unchanged operational home for certs).
- Honor the pinned `Python 3.12.12` and the uv-managed dependency set in the image build.

**Non-Goals:**
- Not adding background workers/brokers (Celery/Redis remain unwired).
- Not containerizing the iAccs source MySQL.
- Not introducing a container-local cert-management loop (certs stay on the host edge).
- Not changing end-user behavior or the external database schema.

## Decisions

- **D1 — Dockerize the web app only.** A single image runs gunicorn + Whitenoise via `remedial.wsgi` using production settings. Rationale: the app is stateless (Whitenoise static, no media, no workers), so the image is one `CMD` with no auxiliary containers. Alternative (in-stack edge) rejected: it moves cert management into the stack, adding moving parts for no benefit here.
- **D2 — Base image and dependency install.** Use a `python:3.12` base and honor the exact pin by installing Python `3.12.12` in the image (or pinning to a matching `3.12.12` base/patched image), then `uv sync --frozen` against `uv.lock`. Static assets are already committed; `make css` runs in the repo, so there is no Node/static build stage in the image.
- **D3 — Expose only an internal app port.** The web container listens (e.g. `8000`) but `compose.yaml` publishes it only to `127.0.0.1` (or to the edge's network), never to the public interface. The host edge (nginx or Caddy) owns 80/443, terminates TLS, and proxies to that internal port.
- **D4 — Postgres external/managed.** `DATABASE_URL` points at off-box Postgres. A disposable box holds no durable DB state; wiping the box never risks production data. Alternative (named volume inside the box) rejected because a disk-local volume dies with a lost box.
- **D5 — Configuration purely via environment.** Settings already read everything from `DATABASE_URL`/`SECRET_KEY`/`ALLOWED_HOSTS`, so compose/edge passes env vars only; no context/config files baked into the image.
- **D6 — External iAccs MySQL reachability.** The sync process needs host/network access to the source DB. The web container connects via the `MYSQL56_*` env settings; compose maps the source host reachable (host gateway or explicit network), and live sync tests stay gated behind `IACCS_LIVE=1`.

## Risks / Trade-offs

- **Python 3.12.12 exact pin:** a floating `python:3.12` image may drift to a different patch. Mitigation: install/match `3.12.12` explicitly during the image build and re-run `uv sync --frozen` to keep the lock authoritative.
- **External Postgres is now a dependency you operate:** network/credentials become a deploy concern. Trade-off accepted because it is the only way to survive a disposable box without a manual backup ritual.
- **TLS still lives on the host edge:** certs/proxy remain a host concern (unchanged from today). This is intentional — it keeps the flaky, cert-sensitive piece in the environment people already know.
- **Whitenoise static vs. edge caching:** serving static via the app is fine at this scale; if traffic grows, the host edge can add a static cache or offload `/static/` without changing the app contract.