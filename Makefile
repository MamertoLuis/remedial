# Remedial development workflow.
#
# The `audit` target is the delivery gate required by the project's SDD exit
# gate: it runs the framework system checks and the full test suite and fails
# (non-zero) if any check or test fails. Intentional skips -- e.g. the live
# iAccs DB tests that skip unless IACCS_LIVE=1 is set -- are allowed.

# --- Tailwind CSS -----------------------------------------------------------
# Tailwind v4 standalone CLI (single binary, no Node). The pinned binary is
# downloaded on first `make css` into tools/ (gitignored). The compiled
# app.css is COMMITTED, so deployments/containers do not need a build step to
# serve styles; when building the Docker image, run `make css` first (or add a
# `RUN make css` step in the image that has network access).
TAILWIND_VERSION := v4.3.5
TAILWIND_BIN := tools/tailwindcss
TAILWIND_URL := https://github.com/tailwindlabs/tailwindcss/releases/download/$(TAILWIND_VERSION)/tailwindcss-linux-x64
CSS_IN ?= account_master/static/css/input.css
CSS_OUT ?= account_master/static/css/app.css

css:
	@mkdir -p tools
	@test -x $(TAILWIND_BIN) || (curl -sL -o $(TAILWIND_BIN) $(TAILWIND_URL) && chmod +x $(TAILWIND_BIN))
	$(TAILWIND_BIN) -i $(CSS_IN) -o $(CSS_OUT) --minify
	@echo "CSS compiled to $(CSS_OUT)"

.PHONY: check test audit css

check:
	uv run python manage.py check

test:
	uv run python manage.py test

audit: check test
	@echo "AUDIT PASSED: all system checks and tests succeeded."
