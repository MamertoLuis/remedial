#!/bin/sh
#
# Web container entrypoint (both compose postures).
#
# Always: collectstatic, migrate (idempotent).
# Demo posture only (SEED_DEMO_ON_BOOT=1): seed_demo --seed 42.
# The demo-data organic guard refuses to seed a database that already holds
# non-demo exposure/delinquency rows, so this flag is self-protecting and
# must never be set against a real database.
#
# Then run gunicorn bound to the container's port (0.0.0.0:8000); the
# loopback publishing and the edge proxy are compose/network concerns.

set -e
cd /app

echo "[entrypoint] collectstatic..."
.venv/bin/python manage.py collectstatic --noinput

echo "[entrypoint] migrate..."
.venv/bin/python manage.py migrate

if [ "$SEED_DEMO_ON_BOOT" = "1" ]; then
    echo "[entrypoint] seeding demo data (SEED_DEMO_ON_BOOT=1)..."
    .venv/bin/python manage.py seed_demo --seed 42
fi

echo "[entrypoint] starting gunicorn on 0.0.0.0:8000..."
exec .venv/bin/gunicorn --bind 0.0.0.0:8000 --config deploy/gunicorn.conf.py