"""Contract tests for the two-phase CSV import service (specs/csv-import).

These exercise ``account_master.services.csv_import`` directly; the
command-level wiring is covered by ``tests_commands_import.py``.
"""

import os
import tempfile
import csv
from datetime import date
from decimal import Decimal
from unittest import mock

from django.core.management.base import CommandError
from django.test import TestCase

from account_master.models import Borrower, DelinquencyStatus, Exposure, LoanAccount
from account_master.services import csv_import
from account_master.services.iaccs import dpd as iaccs_dpd
from account_master.services.iaccs import mapper


def _write_csv(path, headers, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(headers)
        writer.writerows(rows)
    return path


def _fake_query(conn, sql, params=None):
    if "FROM amortsched" in sql:
        return [
            {"DUEDATE": date(2023, 2, 15), "PRINDUE": Decimal("5000.00"), "INTDUE": Decimal("0.00")},
            {"DUEDATE": date(2023, 4, 15), "PRINDUE": Decimal("5000.00"), "INTDUE": Decimal("0.00")},
        ]
    if "FROM sldtl" in sql:
        return [{"total_advanced": Decimal("10000.00"), "outstanding": Decimal("8000.00")}]
    return []


class CsvContractTestCase(TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def path(self, name):
        return os.path.join(self.tmp.name, name)

    def create(self, name, headers, rows):
        return _write_csv(self.path(name), headers, rows)


class BorrowerContractTests(CsvContractTestCase):
    HEADERS = ["borrower_id", "full_name", "borrower_type", "primary_address", "mobile"]

    def test_clean_file_imports_all_rows(self):
        f = self.create("b.csv", self.HEADERS, [["B001", "Ada", "PERSON", "", "555-1"]])
        summary = csv_import.import_borrowers_file(f)
        self.assertEqual(summary.created, 1)
        self.assertEqual(Borrower.objects.count(), 1)

    def test_unrecognized_borrower_type_rejected_and_nothing_written(self):
        f = self.create("b.csv", self.HEADERS, [["B001", "Ada", "ALIEN", "", ""]])
        with self.assertRaises(CommandError):
            csv_import.import_borrowers_file(f)
        self.assertEqual(Borrower.objects.count(), 0)

    def test_duplicate_borrower_id_rejects_file(self):
        f = self.create(
            "b.csv", self.HEADERS, [["B001", "Ada", "PERSON", "", ""], ["B001", "Bob", "PERSON", "", ""]]
        )
        with self.assertRaises(CommandError):
            csv_import.import_borrowers_file(f)
        self.assertEqual(Borrower.objects.count(), 0)

    def test_slash_date_column_rejected_as_unknown(self):
        f = self.create("b.csv", ["borrower_id", "full_name", "as_of_date"], [["B001", "Ada", "2023/06/01"]])
        with self.assertRaises(CommandError) as cm:
            csv_import.import_borrowers_file(f)
        self.assertIn("unknown columns", str(cm.exception))

    def test_classification_column_rejected(self):
        f = self.create("b.csv", ["borrower_id", "full_name", "classification"], [["B001", "Ada", "SS"]])
        with self.assertRaises(CommandError) as cm:
            csv_import.import_borrowers_file(f)
        self.assertIn("classification", str(cm.exception))

    def test_dry_run_writes_nothing(self):
        f = self.create("b.csv", self.HEADERS, [["B001", "Ada", "PERSON", "", ""]])
        summary = csv_import.import_borrowers_file(f, dry_run=True)
        self.assertEqual(summary.created, 1)
        self.assertEqual(Borrower.objects.count(), 0)

    def test_rerun_is_idempotent(self):
        f = self.create("b.csv", self.HEADERS, [["B001", "Ada", "PERSON", "", ""]])
        first = csv_import.import_borrowers_file(f)
        self.assertEqual(first.created, 1)
        second = csv_import.import_borrowers_file(f)
        self.assertEqual(second.created, 0)
        self.assertEqual(second.updated, 1)
        self.assertEqual(Borrower.objects.count(), 1)


class AccountContractTests(CsvContractTestCase):
    HEADERS = [
        "loan_id", "borrower_id", "booking_date", "maturity_date", "original_principal",
        "interest_rate", "loan_type", "account_officer_id", "loan_security",
    ]

    def setUp(self):
        super().setUp()
        self.borrower = Borrower.objects.create(
            borrower_id="B001", full_name="Ada", borrower_type="PERSON", primary_address=""
        )

    def test_status_column_rejected_and_nothing_written(self):
        f = self.create(
            "a.csv",
            self.HEADERS + ["status"],
            [["L001", "B001", "2023-01-01", "2024-01-01", "10000.00", "0.05", "TERM", "AO1", "SECURED", "PERFORMING"]],
        )
        with self.assertRaises(CommandError) as cm:
            csv_import.import_accounts_file(f)
        self.assertIn("status", str(cm.exception))
        self.assertEqual(LoanAccount.objects.count(), 0)

    def test_missing_loan_security_rejected(self):
        headers = self.HEADERS[:-1]  # drop loan_security
        f = self.create("a.csv", headers, [["L001", "B001", "2023-01-01", "2024-01-01", "10000.00", "0.05", "TERM", "AO1"]])
        with self.assertRaises(CommandError) as cm:
            csv_import.import_accounts_file(f)
        self.assertIn("loan_security", str(cm.exception))

    def test_unrecognized_loan_security_rejected(self):
        f = self.create("a.csv", self.HEADERS, [["L001", "B001", "2023-01-01", "2024-01-01", "10000.00", "0.05", "TERM", "AO1", "GOLD"]])
        with self.assertRaises(CommandError) as cm:
            csv_import.import_accounts_file(f)
        self.assertIn("loan_security", str(cm.exception))
        self.assertEqual(LoanAccount.objects.count(), 0)

    def test_missing_borrower_rejects_file(self):
        f = self.create("a.csv", self.HEADERS, [["L001", "B999", "2023-01-01", "2024-01-01", "10000.00", "0.05", "TERM", "AO1", "SECURED"]])
        with self.assertRaises(CommandError) as cm:
            csv_import.import_accounts_file(f)
        self.assertIn("does not exist", str(cm.exception))
        self.assertEqual(LoanAccount.objects.count(), 0)

    def test_one_bad_row_writes_nothing(self):
        f = self.create(
            "a.csv",
            self.HEADERS,
            [
                ["L001", "B001", "2023-01-01", "2024-01-01", "10000.00", "0.05", "TERM", "AO1", "SECURED"],
                ["L002", "B001", "2023-01-01", "not-a-date", "10000.00", "0.05", "TERM", "AO1", "SECURED"],
            ],
        )
        with self.assertRaises(CommandError):
            csv_import.import_accounts_file(f)
        self.assertEqual(LoanAccount.objects.count(), 0)

    def test_clean_file_imports(self):
        f = self.create("a.csv", self.HEADERS, [["L001", "B001", "2023-01-01", "2024-01-01", "10000.00", "0.05", "TERM", "AO1", "SECURED"]])
        summary = csv_import.import_accounts_file(f)
        self.assertEqual(summary.created, 1)
        loan = LoanAccount.objects.get(loan_id="L001")
        self.assertEqual(loan.loan_security, "SECURED")

    def test_dry_run_writes_nothing(self):
        f = self.create("a.csv", self.HEADERS, [["L001", "B001", "2023-01-01", "2024-01-01", "10000.00", "0.05", "TERM", "AO1", "SECURED"]])
        summary = csv_import.import_accounts_file(f, dry_run=True)
        self.assertEqual(summary.created, 1)
        self.assertEqual(LoanAccount.objects.count(), 0)


class ExposureContractTests(CsvContractTestCase):
    HEADERS = ["loan_id", "as_of_date", "principal_outstanding", "accrued_interest", "accrued_penalty"]

    def setUp(self):
        super().setUp()
        self.borrower = Borrower.objects.create(
            borrower_id="B001", full_name="Ada", borrower_type="PERSON", primary_address=""
        )
        self.account = LoanAccount.objects.create(
            loan_id="01-12-08-1428-1289",
            borrower=self.borrower,
            booking_date=date(2023, 1, 1),
            maturity_date=date(2024, 1, 1),
            original_principal=Decimal("10000.00"),
            interest_rate=Decimal("0.05"),
            loan_type="TERM",
            account_officer_id="AO1",
            status="PERFORMING",
        )
        self.fake_conn = mock.Mock()
        self.query_patcher = mock.patch("account_master.services.iaccs.loader.query", _fake_query)
        self.query_patcher.start()
        self.addCleanup(self.query_patcher.stop)

    def test_days_past_due_column_rejected(self):
        f = self.create("e.csv", self.HEADERS + ["days_past_due"], [["01-12-08-1428-1289", "2023-06-01", "8000", "100", "0", "30"]])
        with self.assertRaises(CommandError) as cm:
            csv_import.import_exposures_file(f, conn=self.fake_conn, cutoff=date(2023, 6, 1))
        self.assertIn("days_past_due", str(cm.exception))
        self.assertEqual(Exposure.objects.count(), 0)

    def test_missing_connection_rejected(self):
        f = self.create("e.csv", self.HEADERS, [["01-12-08-1428-1289", "2023-06-01", "8000", "100", "0"]])
        with self.assertRaises(CommandError) as cm:
            csv_import.import_exposures_file(f, conn=None, cutoff=date(2023, 6, 1))
        self.assertIn("iAccs connection", str(cm.exception))

    def test_clean_file_computes_dpd_and_tags_csv(self):
        f = self.create("e.csv", self.HEADERS, [["01-12-08-1428-1289", "2023-06-01", "8000.00", "100.00", "0.00"]])
        summary = csv_import.import_exposures_file(f, conn=self.fake_conn, cutoff=date(2023, 6, 1))
        self.assertEqual(summary.created, 1)
        exposure = Exposure.objects.get(account=self.account, as_of_date=date(2023, 6, 1))
        self.assertEqual(exposure.source, "CSV")
        expected = mapper.compute_schedule_dpd(
            [
                (date(2023, 2, 15), Decimal("5000.00"), Decimal("0.00")),
                (date(2023, 4, 15), Decimal("5000.00"), Decimal("0.00")),
            ],
            Decimal("2000.00"),
            date(2023, 6, 1),
        )
        self.assertEqual(exposure.days_past_due, expected)

    def test_iaccs_snapshot_conflict_rejects_file(self):
        Exposure.objects.create(
            account=self.account,
            as_of_date=date(2023, 6, 1),
            principal_outstanding=Decimal("8000"),
            accrued_interest=Decimal("0"),
            accrued_penalty=Decimal("0"),
            days_past_due=20,
            source="IACCS",
        )
        f = self.create("e.csv", self.HEADERS, [["01-12-08-1428-1289", "2023-06-01", "7000.00", "100.00", "0.00"]])
        with self.assertRaises(CommandError) as cm:
            csv_import.import_exposures_file(f, conn=self.fake_conn, cutoff=date(2023, 6, 1))
        self.assertIn("iAccs-tagged", str(cm.exception))
        self.assertEqual(
            Exposure.objects.get(account=self.account, as_of_date=date(2023, 6, 1)).principal_outstanding,
            Decimal("8000"),
        )

    def test_csv_tagged_correction_allowed(self):
        Exposure.objects.create(
            account=self.account,
            as_of_date=date(2023, 6, 1),
            principal_outstanding=Decimal("9000"),
            accrued_interest=Decimal("0"),
            accrued_penalty=Decimal("0"),
            days_past_due=5,
            source="CSV",
        )
        f = self.create("e.csv", self.HEADERS, [["01-12-08-1428-1289", "2023-06-01", "7000.00", "100.00", "0.00"]])
        summary = csv_import.import_exposures_file(f, conn=self.fake_conn, cutoff=date(2023, 6, 1))
        self.assertEqual(summary.updated, 1)
        self.assertEqual(
            Exposure.objects.get(account=self.account, as_of_date=date(2023, 6, 1)).principal_outstanding,
            Decimal("7000.00"),
        )

    def test_dry_run_writes_nothing(self):
        f = self.create("e.csv", self.HEADERS, [["01-12-08-1428-1289", "2023-06-01", "8000.00", "100.00", "0.00"]])
        summary = csv_import.import_exposures_file(f, conn=self.fake_conn, cutoff=date(2023, 6, 1), dry_run=True)
        self.assertEqual(summary.created, 1)
        self.assertEqual(Exposure.objects.count(), 0)


class DpdHelperTests(CsvContractTestCase):
    def test_compute_dpd_for_loan_uses_shared_rule(self):
        fake_conn = mock.Mock()
        with mock.patch("account_master.services.iaccs.loader.query", _fake_query):
            dpd = iaccs_dpd.compute_dpd_for_loan(fake_conn, "01-12-08-1428-1289", date(2023, 6, 1))
        expected = mapper.compute_schedule_dpd(
            [
                (date(2023, 2, 15), Decimal("5000.00"), Decimal("0.00")),
                (date(2023, 4, 15), Decimal("5000.00"), Decimal("0.00")),
            ],
            Decimal("2000.00"),
            date(2023, 6, 1),
        )
        self.assertEqual(dpd, expected)

    def test_parse_rejects_foreign_loan_id_shape(self):
        from account_master.services.iaccs.mapper import parse_loan_id

        with self.assertRaises(ValueError):
            parse_loan_id("0000002301-0002605-3")
        self.assertEqual(parse_loan_id("01-12-08-1428-1289"), (1, 8, 1428, 1289))