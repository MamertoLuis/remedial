"""Tests for the iAccs single-hop importer (change import-from-iaccs).

Pure unit tests use a fake source connection injected by patching the
loader's ``query`` function; only the Django database is real. Live-source
verification lives in ``tests_iaccs_live.py`` and requires ``IACCS_LIVE=1``.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from account_master.models import Borrower, ECLProvisionHistory, Exposure, LoanAccount
from account_master.services.iaccs import mapper
from account_master.services.iaccs.loader import import_loans, sync_from_iaccs

CUTOFF = date(2025, 6, 30)


def _master(branch=1, slt=8, ref=1428, client=1289, **overrides):
    row = {
        "loan_br": branch,
        "loan_slt": slt,
        "loan_ref": ref,
        "client_id": client,
        "client_name": "SAMPLE BORROWER",
        "product": "Individual Loan",
        "loan_status": 11,
        "status_desc": "Current",
        "restructured": 0,
        "approval_date": date(2024, 1, 10),
        "release_date": date(2024, 1, 15),
        "maturity_date": date(2026, 1, 15),
        "principal_approved": Decimal("10000.00"),
        "interest_rate": Decimal("12.00"),
        "allowance": None,
    }
    row.update(overrides)
    return row


def _agg(branch=1, slt=8, ref=1428, client=1289, outstanding=3500, advanced=5000):
    return {
        "loan_br": branch,
        "loan_slt": slt,
        "loan_ref": ref,
        "client_id": client,
        "total_advanced": Decimal(str(advanced)),
        "outstanding": Decimal(str(outstanding)),
        "principal_collected": Decimal(str(advanced - outstanding)),
        "interest_collected": Decimal("300.00"),
        "penalty_collected": Decimal("0.00"),
    }


def _schedule_rows(cutoff_year=2025, **key):
    """Three monthly installments of principal 1000 + interest 100 each."""
    rows = []
    for i, month in enumerate((1, 2, 3)):
        rows.append(
            {
                "BR_CODE": key.get("branch", 1),
                "SLT_CODE": key.get("slt", 8),
                "REF_NO": key.get("ref", 1428),
                "CLIENTID": key.get("client", 1289),
                "DUEDATE": date(cutoff_year, month, 28),
                "PRINDUE": Decimal("1000.00"),
                "INTDUE": Decimal("100.00"),
            }
        )
    return rows


class FakeConn:
    """Placeholder connection; never reached while ``query`` is patched."""

    def close(self):
        pass

    host = "fake"
    port = 0


def patch_queries(
    masters=None,
    aggregates=None,
    schedules=None,
    branches=None,
):
    """Patch the loader's DB access with canned source rows."""

    def fake_query(conn, sql, params):
        branch = (params or {}).get("branch")
        if "FROM loan l" in sql:
            return [
                m for m in (masters or [])
                if branch is None or m.get("loan_br") == branch
            ]
        if "FROM sldtl d" in sql:
            return [
                a for a in (aggregates or [])
                if branch is None or a.get("loan_br") == branch
            ]
        if "FROM amortsched" in sql:
            rows = []
            base = dict(params)
            for key, items in (schedules or {}).items():
                if branch is not None and key and key[0] != branch:
                    continue
                for item in items:
                    row = {
                        "BR_CODE": key[0] if key else base.get("branch", 1),
                        "SLT_CODE": key[1] if key else 8,
                        "REF_NO": key[2] if key else 1428,
                        "CLIENTID": key[3] if key else 1289,
                    }
                    row.update(item)
                    rows.append(row)
            return rows
        if "SELECT DISTINCT LoanBR_CODE" in sql:
            return [{"branch": b} for b in (branches or [1])]
        return []

    return patch("account_master.services.iaccs.loader.query", side_effect=fake_query)


class MapperUnitTests(TestCase):
    """Spec: canonical identity + schedule-based DPD (pure logic)."""

    def test_render_loan_id_uses_five_part_key(self):
        self.assertEqual(mapper.render_loan_id(1, 8, 1428, 1289), "01-12-08-1428-1289")

    def test_render_loan_id_fits_max_length(self):
        # Worst realistic widths from live schema: BR 2dp, SLT 2dp, ref/client 4dp.
        loan_id = mapper.render_loan_id(1, 21, 9999, 9999)
        self.assertEqual(len(loan_id), 18)
        self.assertLessEqual(len(loan_id), 20)

    def test_render_borrower_id(self):
        self.assertEqual(mapper.render_borrower_id(1, 1289), "1289")

    def test_dpd_zero_when_fully_current(self):
        schedule = [(date(2025, 1, 28), Decimal("1000.00"), Decimal("100.00"))]
        allocated = [s[:2] for s in schedule]
        self.assertEqual(mapper.compute_schedule_dpd(allocated, Decimal("1000.00"), CUTOFF), 0)

    def test_dpd_zero_when_ahead(self):
        schedule = [(date(2025, 1, 28), Decimal("1000.00"), Decimal("100.00"))]
        allocated = [s[:2] for s in schedule]
        self.assertEqual(mapper.compute_schedule_dpd(allocated, Decimal("1500.00"), CUTOFF), 0)

    def test_dpd_95_days_for_uncovered_installment(self):
        # Oldest uncovered installment fell due 95 days before the cutoff.
        schedule = [(date(2025, 3, 27), Decimal("1000.00"), Decimal("100.00"))]
        allocated = [s[:2] for s in schedule]
        self.assertEqual(mapper.compute_schedule_dpd(allocated, Decimal("0.00"), CUTOFF), 95)

    def test_dpd_counts_only_installments_due_at_cutoff(self):
        # An installment due after the cutoff is not the anchor.
        schedule = [
            (date(2025, 6, 1), Decimal("1000.00"), Decimal("100.00")),
            (date(2025, 7, 1), Decimal("1000.00"), Decimal("100.00")),
        ]
        allocated = [s[:2] for s in schedule]
        self.assertEqual(mapper.compute_schedule_dpd(allocated, Decimal("0.00"), CUTOFF), 29)


class BorrowerAndAccountTests(TestCase):
    """Spec: borrower + canonical loan identity."""

    def test_borrower_created_and_reused_across_loans(self):
        masters = [
            _master(ref=1001, client=1289),
            _master(ref=1002, client=1289),
        ]
        with patch_queries(masters=masters, aggregates=[], schedules={}):
            summary = sync_from_iaccs(FakeConn(), None, CUTOFF)

        self.assertEqual(Borrower.objects.count(), 1)
        self.assertEqual(
            LoanAccount.objects.filter(borrower__borrower_id="1289").count(), 2
        )
        self.assertEqual(summary["borrowers_created"], 1)
        self.assertEqual(summary["loans"], 2)

    def test_canonical_loan_id_created_and_updated_in_place(self):
        master = _master()
        with patch_queries(masters=[master], aggregates=[_agg()], schedules={}):
            first = sync_from_iaccs(FakeConn(), None, CUTOFF)
            second = sync_from_iaccs(FakeConn(), None, CUTOFF)

        self.assertEqual(LoanAccount.objects.count(), 1)
        account = LoanAccount.objects.get(loan_id="01-12-08-1428-1289")
        self.assertEqual(account.borrower_id, "1289")
        self.assertEqual(account.original_principal, Decimal("10000.00"))
        self.assertEqual(account.interest_rate, Decimal("12.00"))
        self.assertEqual(account.maturity_date, date(2026, 1, 15))
        self.assertEqual(first["accounts_created"], 1)
        self.assertEqual(second["accounts_updated"], 1)

    def test_loan_key_includes_slt_and_client(self):
        # REF alone is not unique: same REF, different SLT and client.
        masters = [
            _master(slt=1, ref=1, client=2777),
            _master(slt=10, ref=1, client=4389),
        ]
        with patch_queries(masters=masters, aggregates=[], schedules={}):
            sync_from_iaccs(FakeConn(), None, CUTOFF)
        self.assertEqual(LoanAccount.objects.count(), 2)
        self.assertTrue(LoanAccount.objects.filter(loan_id="01-12-01-1-2777").exists())
        self.assertTrue(LoanAccount.objects.filter(loan_id="01-12-10-1-4389").exists())


class ExposureAndDpdTests(TestCase):
    """Spec: point-in-time exposure with schedule-based DPD."""

    def test_exposure_upserted_per_account_and_asof(self):
        master = _master()
        with patch_queries(
            masters=[master],
            aggregates=[_agg(outstanding=3500, advanced=5000)],
            schedules={},
        ):
            first = sync_from_iaccs(FakeConn(), None, CUTOFF)
            second = sync_from_iaccs(FakeConn(), None, CUTOFF)

        self.assertEqual(Exposure.objects.count(), 1)
        exposure = Exposure.objects.get(account_id="01-12-08-1428-1289")
        self.assertEqual(exposure.principal_outstanding, Decimal("3500.00"))
        self.assertEqual(first["exposures_created"], 1)
        self.assertEqual(second["exposures_updated"], 1)

    def test_outstanding_is_sum_of_principal_postings(self):
        master = _master()
        # disbursement +5000, repayment -1500 -> outstanding 3500.
        with patch_queries(
            masters=[master],
            aggregates=[_agg(outstanding=3500, advanced=5000)],
            schedules={},
        ):
            sync_from_iaccs(FakeConn(), None, CUTOFF)
        exposure = Exposure.objects.get(account_id="01-12-08-1428-1289")
        self.assertEqual(exposure.principal_outstanding, Decimal("3500.00"))
        # repaid = advanced - outstanding = 1500, covering the first installment.
        self.assertEqual(exposure.days_past_due, 0)

    def test_dpd_propagates_into_exposure(self):
        master = _master()
        # No repayment at all -> oldest installment uncovered.
        schedule = {
            (1, 8, 1428, 1289): [
                {"DUEDATE": date(2025, 1, 28), "PRINDUE": Decimal("1000.00"), "INTDUE": Decimal("100.00")},
                {"DUEDATE": date(2025, 2, 28), "PRINDUE": Decimal("1000.00"), "INTDUE": Decimal("100.00")},
                {"DUEDATE": date(2025, 3, 28), "PRINDUE": Decimal("1000.00"), "INTDUE": Decimal("100.00")},
            ]
        }
        with patch_queries(
            masters=[master],
            aggregates=[_agg(outstanding=5000, advanced=5000)],
            schedules=schedule,
        ):
            sync_from_iaccs(FakeConn(), None, CUTOFF)
        exposure = Exposure.objects.get(account_id="01-12-08-1428-1289")
        self.assertEqual(exposure.days_past_due, 153)  # 2025-01-28 -> 2025-06-30

    def test_report_variable_length_dpd(self):
        master = _master()
        schedule = {
            (1, 8, 1428, 1289): [
                {"DUEDATE": date(2025, 3, 27), "PRINDUE": Decimal("1000.00"), "INTDUE": Decimal("100.00")},
            ]
        }
        with patch_queries(
            masters=[master],
            aggregates=[_agg(outstanding=5000, advanced=5000)],
            schedules=schedule,
        ):
            sync_from_iaccs(FakeConn(), None, CUTOFF)
        exposure = Exposure.objects.get(account_id="01-12-08-1428-1289")
        self.assertEqual(exposure.days_past_due, 95)


class CascadeIntegrationTests(TestCase):
    """Spec: existing derivation cascade runs unchanged."""

    def test_imported_delinquency_moves_account_to_npl_and_provisions(self):
        master = _master(loan_status=11)  # source says Current; ignored
        schedule = {
            (1, 8, 1428, 1289): [
                {"DUEDATE": date(2025, 3, 27), "PRINDUE": Decimal("1000.00"), "INTDUE": Decimal("100.00")},
            ]
        }
        with patch_queries(
            masters=[master],
            aggregates=[_agg(outstanding=5000, advanced=5000)],
            schedules=schedule,
        ):
            sync_from_iaccs(FakeConn(), None, CUTOFF)

        account = LoanAccount.objects.get(loan_id="01-12-08-1428-1289")
        self.assertEqual(account.status, "NPL")
        exposure = Exposure.objects.get(account=account)
        provision = ECLProvisionHistory.objects.filter(exposure=exposure).first()
        self.assertIsNotNone(provision)
        self.assertEqual(provision.as_of_date, CUTOFF)
        self.assertGreater(provision.provision_amount, 0)
        self.assertEqual(provision.method, "RULE_BASED")

    def test_source_classification_never_overrides_derivation(self):
        # Source status 11 = Current; 95-DPD loan must still derive NPL.
        master = _master(loan_status=11, status_desc="Current")
        schedule = {
            (1, 8, 1428, 1289): [
                {"DUEDATE": date(2025, 3, 27), "PRINDUE": Decimal("1000.00"), "INTDUE": Decimal("100.00")},
            ]
        }
        with patch_queries(
            masters=[master],
            aggregates=[_agg(outstanding=5000, advanced=5000)],
            schedules=schedule,
        ):
            sync_from_iaccs(FakeConn(), None, CUTOFF)
        account = LoanAccount.objects.get(loan_id="01-12-08-1428-1289")
        self.assertEqual(account.status, "NPL")


class DryRunAndErrorTests(TestCase):
    """Spec: import command contract + read-only failure semantics."""

    def test_dry_run_writes_nothing(self):
        masters = [_master(), _master(ref=1002, client=1289)]
        with patch_queries(masters=masters, aggregates=[_agg(), _agg(ref=1002)], schedules={}):
            summary = sync_from_iaccs(FakeConn(), None, CUTOFF, dry_run=True)
        self.assertEqual(Borrower.objects.count(), 0)
        self.assertEqual(LoanAccount.objects.count(), 0)
        self.assertEqual(Exposure.objects.count(), 0)
        # per-loan intent: two loans -> two would-create borrowers (same client)
        self.assertEqual(summary["borrowers_created"], 2)
        self.assertEqual(summary["accounts_created"], 2)

    def test_single_row_failure_is_isolated(self):
        good = _master(ref=2001, client=9001)
        bad = _master(ref=2002, client=9002)
        records = [
            {"master": good, "aggregates": {}, "schedule": []},
            {"master": bad, "aggregates": {}, "schedule": []},
        ]

        from account_master.services.iaccs import loader

        original_run_loan = loader._run_loan

        def broken(record, cutoff):
            if record["master"]["loan_ref"] == 2002:
                raise ValueError("boom")
            return original_run_loan(record, cutoff)

        with patch.object(loader, "_run_loan", side_effect=broken):
            summary = import_loans(records, CUTOFF)

        self.assertEqual(len(summary["errors"]), 1)
        self.assertIn("boom", summary["errors"][0])
        self.assertEqual(LoanAccount.objects.count(), 1)

    def test_branch_filter_imports_only_that_branch(self):
        masters_branch1 = [_master(branch=1, ref=11, client=1111)]
        masters_branch2 = [_master(branch=2, ref=22, client=2222)]
        with patch_queries(
            masters=masters_branch1 + masters_branch2,
            aggregates=[],
            schedules={},
            branches=[1, 2],
        ):
            sync_from_iaccs(FakeConn(), 1, CUTOFF)
        self.assertEqual(LoanAccount.objects.count(), 1)
        self.assertTrue(LoanAccount.objects.filter(loan_id="01-12-08-11-1111").exists())

    def test_connection_failure_fails_fast_without_writes(self):
        with patch(
            "account_master.management.commands.import_from_iaccs.connection.get_connection",
            side_effect=Exception("refused"),
        ):
            with self.assertRaises(CommandError) as cm:
                call_command("import_from_iaccs", "--cutoff", "2025-06-30")
        self.assertIn("Could not connect to the iAccs MySQL database", str(cm.exception))
        self.assertEqual(Borrower.objects.count(), 0)

    def test_errors_raise_command_error(self):
        with patch(
            "account_master.management.commands.import_from_iaccs.connection.get_connection",
            return_value=FakeConn(),
        ), patch(
            "account_master.management.commands.import_from_iaccs.sync_from_iaccs",
            return_value={
                "borrowers_created": 0,
                "borrowers_updated": 0,
                "accounts_created": 0,
                "accounts_updated": 0,
                "exposures_created": 0,
                "exposures_updated": 0,
                "loans": 1,
                "errors": ["01-12-08-1-1: boom"],
            },
        ):
            with self.assertRaises(CommandError) as cm:
                call_command("import_from_iaccs", "--cutoff", "2025-06-30", "--dry-run")
        self.assertIn("Finished with 1 errors", str(cm.exception))

    def test_invalid_cutoff_rejected(self):
        with self.assertRaises(CommandError):
            call_command("import_from_iaccs", "--cutoff", "not-a-date", "--dry-run")