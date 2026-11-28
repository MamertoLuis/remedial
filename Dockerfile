# Remedial web image.
#
# Builds the stateless web process: pinned Python 3.12.12, uv-managed
# dependencies from uv.lock, gunicorn + Whitenoise. No durable state lives in
# this image; all runtime configuration comes from the environment and all
# durable state goes to the configured database.
#
# The PDF stack (xhtml2pdf -> svglib -> rlpycairo -> pycairo) builds from
# source on Linux and needs the Cairo headers before `uv sync`.
FROM python:3.12.12

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_LINK_MODE=copy \
    DJANGO_SETTINGS_MODULE=remedial.settings.production

# Cairo headers (PDF stack build prerequisite; see README "Requirements").
RUN apt-get update && apt-get install -y --no-install-recommends \
        pkg-config libcairo2-dev libcairo2 \
    && rm -rf /var/lib/apt/lists/*

# uv-managed environment.
RUN pip install --no-cache-dir uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY . .

# Install the pinned dependency set (package = false -> deps only into .venv).
RUN uv sync --frozen

COPY deploy/entrypoint.sh /app/deploy/entrypoint.sh
RUN chmod +x /app/deploy/entrypoint.sh

EXPOSE 8000

CMD ["/app/deploy/entrypoint.sh"]