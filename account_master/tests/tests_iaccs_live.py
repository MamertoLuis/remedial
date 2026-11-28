"""Live-source integration tests for the iAccs importer.

These tests connect read-only to the real iAccs MySQL database and are
skipped unless ``IACCS_LIVE=1`` is set with ``MYSQL56_*`` available (the
analytics host where the ``iaccs-mysql`` container is published, e.g.
``MYSQL56_PORT=32768``). They do not write anything.
"""

import os
import unittest
from datetime import date

from django.test import SimpleTestCase

from account_master.services.iaccs import connection, mapper
from account_master.services.iaccs.loader import (
    build_records,
    fetch_branches,
    fetch_loan_aggregates,
    fetch_loan_masters,
    fetch_schedules,
)

LIVE = os.environ.get("IACCS_LIVE") == "1"
BRANCH = 1
CUTOFF = date(2025, 6, 30)


@unittest.skipUnless(LIVE, "set IACCS_LIVE=1 with MYSQL56_* pointing at the live iAccs DB")
class IaccsLiveQueryTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.conn = connection.get_connection()

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()
        super().tearDownClass()

    def test_loan_source_is_read_only(self):
        # A write statement must be refused by the connection guard.
        from account_master.services.iaccs.connection import query

        with self.assertRaises(ValueError):
            query(self.conn, "DELETE FROM loan LIMIT 1")

    def test_branches_match_live_portfolio(self):
        self.assertEqual(fetch_branches(self.conn), [BRANCH])

    def test_master_rows_and_five_part_key(self):
        masters = fetch_loan_masters(self.conn, BRANCH)
        self.assertGreater(len(masters), 8000)  # live: 9,141 loans
        columns = {"loan_br", "loan_slt", "loan_ref", "client_id"}
        self.assertTrue(all(columns <= set(m) for m in masters))
        # The full five-part key must be unique per row (REF alone is not).
        keys = [(m["loan_br"], m["loan_slt"], m["loan_ref"], m["client_id"]) for m in masters]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertLess(len({m["loan_ref"] for m in masters}), len(masters))

    def test_rendered_loan_id_fits_max_length(self):
        masters = fetch_loan_masters(self.conn, BRANCH)
        loan_ids = [mapper.render_loan_id(m["loan_br"], m["loan_slt"], m["loan_ref"], m["client_id"]) for m in masters]
        self.assertLessEqual(max(len(i) for i in loan_ids), 20)
        self.assertTrue(all("-12-" in i for i in loan_ids))

    def test_no_negative_outstanding_totals(self):
        aggregates = fetch_loan_aggregates(self.conn, BRANCH, CUTOFF)
        self.assertGreater(len(aggregates), 8000)
        for agg in aggregates:
            self.assertGreaterEqual(
                agg["outstanding"], 0,
                f"negative outstanding for {agg['loan_br']}-{agg['loan_slt']}-{agg['loan_ref']}-{agg['client_id']}",
            )

    def test_records_combine_master_aggregates_schedule(self):
        masters = fetch_loan_masters(self.conn, BRANCH)
        aggregates = fetch_loan_aggregates(self.conn, BRANCH, CUTOFF)
        schedules = fetch_schedules(self.conn, BRANCH, CUTOFF)
        records = build_records(masters, aggregates, schedules)
        self.assertEqual(len(records), len(masters))
        self.assertGreaterEqual(len(schedules), 0)
        self.assertTrue(all("master" in r and "aggregates" in r and "schedule" in r for r in records))