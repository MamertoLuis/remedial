# uv run python manage.py import_borrowers /mnt/c/Users/mamer/OneDrive/Desktop/borrowers.csv
# uv run python manage.py import_accounts /mnt/c/Users/mamer/OneDrive/Desktop/accounts.csv
# uv run python manage.py import_exposures --cutoff 2026-03-14 /mnt/c/Users/mamer/OneDrive/Desktop/exposures.csv
# Note: CSV imports follow the csv-import contract. No status, classification,
# aging_bucket, npl_flag, npl_date, or days_past_due columns are accepted
# (those are derived); dates are ISO YYYY-MM-DD; exposure imports compute
# days past due from the iAccs schedule and need the MYSQL56_* environment.
#
# For a fake-only demo host, seed the database instead:
#   uv run python manage.py seed_demo --seed 42
# Real imports (import_from_iaccs, CSV imports) must never run on a demo host.