# Remedial development workflow.
#
# The `audit` target is the delivery gate required by the project's SDD exit
# gate: it runs the framework system checks and the full test suite and fails
# (non-zero) if any check or test fails. Intentional skips -- e.g. the live
# iAccs DB tests that skip unless IACCS_LIVE=1 is set -- are allowed.

.PHONY: check test audit

check:
	uv run python manage.py check

test:
	uv run python manage.py test

audit: check test
	@echo "AUDIT PASSED: all system checks and tests succeeded."