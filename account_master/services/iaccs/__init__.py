"""Single-hop loader from the iAccs core-banking MySQL database.

This package implements the ``import_from_iaccs`` data path:

* ``connection.py`` -- read-only ``pymysql`` connection resolved from the
  ``MYSQL56_*`` environment convention.
* ``mapper.py``     -- canonical identity mapping and field derivation
  (five-part loan key, aggregate-shortfall DPD). Conventions mirror
  ``URBD_Financial_Analytics/references/loan-source-to-target-mapping.md``.
* ``loader.py``     -- source queries and orchestration that upserts
  ``Borrower`` / ``LoanAccount`` / ``Exposure`` through the existing service
  layer so the derivation cascade (delinquency -> account status -> ECL)
  runs unchanged.

The pipeline writes only to the Django database; every query against the
iAccs MySQL source is a read.
"""
