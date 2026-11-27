"""Command-level tests for the csv-import contract imports.

These exercise the management commands over the two-phase contract service
(``account_master.services.csv_import``); service-level contract details are
covered by ``tests_csv_import_contract.py``.
"""

import os
import tempfile
import csv
from datetime import date
from decimal import Decimal
from unittest import mock

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from account_master.models import Borrower, Exposure, LoanAccount


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


class _FakeConn:
    def close(self):
        pass


class ImportCommandsTestCase(TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

    def create_csv(self, filename, headers, rows):
        return _write_csv(
            os.path.join(self.temp_dir.name, filename), headers, rows
        )


class BorrowerCommandTests(ImportCommandsTestCase):
    HEADERS = ["borrower_id", "full_name", "borrower_type", "primary_address", "mobile"]

    def test_import_borrowers_success(self):
        csv_path = self.create_csv(
            "borrowers.csv",
            self.HEADERS,
            [["B001", "John Doe", "PERSON", "123 Main St", "555-1234"]],
        )
        call_command("import_borrowers", csv_path)
        self.assertEqual(Borrower.objects.count(), 1)
        b = Borrower.objects.get(borrower_id="B001")
        self.assertEqual(b.full_name, "John Doe")
        self.assertEqual(b.borrower_type, "PERSON")

    def test_import_borrowers_skip_existing(self):
        csv_path = self.create_csv(
            "borrowers.csv", self.HEADERS, [["B001", "John Doe", "PERSON", "", ""]]
        )
        call_command("import_borrowers", csv_path)
        call_command("import_borrowers", csv_path, "--skip-existing")
        self.assertEqual(Borrower.objects.count(), 1)

    def test_import_borrowers_dry_run_writes_nothing(self):
        csv_path = self.create_csv(
            "borrowers.csv", self.HEADERS, [["B001", "John Doe", "PERSON", "", ""]]
        )
        call_command("import_borrowers", csv_path, "--dry-run")
        self.assertEqual(Borrower.objects.count(), 0)

    def test_import_borrowers_rejects_unrecognized_type(self):
        csv_path = self.create_csv(
            "borrowers.csv", self.HEADERS, [["B001", "John Doe", "ALIEN", "", ""]]
        )
        with self.assertRaises(CommandError) as cm:
            call_command("import_borrowers", csv_path)
        self.assertIn("borrower_type", str(cm.exception))
        self.assertEqual(Borrower.objects.count(), 0)

    def test_import_borrowers_missing_headers(self):
        csv_path = self.create_csv("borrowers_bad.csv", ["borrower_id"], [["B001"]])
        with self.assertRaises(CommandError) as cm:
            call_command("import_borrowers", csv_path)
        self.assertIn("CSV header contract violated", str(cm.exception))


class AccountCommandTests(ImportCommandsTestCase):
    HEADERS = [
        "loan_id", "borrower_id", "booking_date", "maturity_date", "original_principal",
        "interest_rate", "loan_type", "account_officer_id", "loan_security",
    ]
    ROW = ["L001", "B001", "2023-01-01", "2024-01-01", "10000.00", "0.05", "TERM", "AO1", "SECURED"]

    def setUp(self):
        super().setUp()
        self.borrower = Borrower.objects.create(
            borrower_id="B001", full_name="John Doe", borrower_type="PERSON", primary_address=""
        )

    def test_import_accounts_success(self):
        csv_path = self.create_csv("accounts.csv", self.HEADERS, [self.ROW])
        call_command("import_accounts", csv_path)
        loan = LoanAccount.objects.get(loan_id="L001")
        self.assertEqual(loan.borrower.borrower_id, "B001")
        self.assertEqual(loan.original_principal, Decimal("10000.00"))
        self.assertEqual(loan.loan_security, "SECURED")

    def test_import_accounts_rejects_status_column(self):
        csv_path = self.create_csv(
            "accounts.csv", self.HEADERS + ["status"], [self.ROW + ["PERFORMING"]]
        )
        with self.assertRaises(CommandError) as cm:
            call_command("import_accounts", csv_path)
        self.assertIn("status", str(cm.exception))
        self.assertEqual(LoanAccount.objects.count(), 0)

    def test_import_accounts_missing_borrower(self):
        csv_path = self.create_csv(
            "accounts.csv", self.HEADERS, [["L001", "B999", "2023-01-01", "2024-01-01", "10000.00", "0.05", "TERM", "AO1", "SECURED"]]
        )
        with self.assertRaises(CommandError) as cm:
            call_command("import_accounts", csv_path)
        self.assertIn("does not exist", str(cm.exception))
        self.assertEqual(LoanAccount.objects.count(), 0)

    def test_import_accounts_one_bad_row_writes_nothing(self):
        csv_path = self.create_csv(
            "accounts.csv",
            self.HEADERS,
            [self.ROW, ["L002", "B001", "2023-01-01", "bad-date", "10000.00", "0.05", "TERM", "AO1", "SECURED"]],
        )
        with self.assertRaises(CommandError):
            call_command("import_accounts", csv_path)
        self.assertEqual(LoanAccount.objects.count(), 0)


class ExposureCommandTests(ImportCommandsTestCase):
    HEADERS = ["loan_id", "as_of_date", "principal_outstanding", "accrued_interest", "accrued_penalty"]

    def setUp(self):
        super().setUp()
        borrower = Borrower.objects.create(
            borrower_id="B001", full_name="John Doe", borrower_type="PERSON", primary_address=""
        )
        self.account = LoanAccount.objects.create(
            loan_id="01-12-08-1428-1289",
            borrower=borrower,
            booking_date=date(2023, 1, 1),
            maturity_date=date(2024, 1, 1),
            original_principal=Decimal("10000.00"),
            interest_rate=Decimal("0.05"),
            loan_type="TERM",
            account_officer_id="AO1",
            status="PERFORMING",
        )
        self.exposure_row = ["01-12-08-1428-1289", "2023-06-01", "8000.00", "100.00", "0.00"]

    def _run(self, csv_path, **kwargs):
        with mock.patch(
            "account_master.services.iaccs.connection.get_connection",
            return_value=_FakeConn(),
        ), mock.patch("account_master.services.iaccs.loader.query", _fake_query):
            call_command("import_exposures", csv_path, **kwargs)

    def test_import_exposures_success(self):
        csv_path = self.create_csv("exposures.csv", self.HEADERS, [self.exposure_row])
        self._run(csv_path, cutoff="2023-06-01")
        exposure = Exposure.objects.get(account=self.account, as_of_date=date(2023, 6, 1))
        self.assertEqual(exposure.principal_outstanding, Decimal("8000.00"))
        self.assertEqual(exposure.source, "CSV")
        self.assertGreater(exposure.days_past_due, 0)

    def test_import_exposures_rejects_dpd_column(self):
        csv_path = self.create_csv(
            "exposures.csv", self.HEADERS + ["days_past_due"], [self.exposure_row + ["30"]]
        )
        with self.assertRaises(CommandError) as cm:
            self._run(csv_path, cutoff="2023-06-01")
        self.assertIn("days_past_due", str(cm.exception))
        self.assertEqual(Exposure.objects.count(), 0)

    def test_import_exposures_requires_cutoff(self):
        csv_path = self.create_csv("exposures.csv", self.HEADERS, [self.exposure_row])
        with self.assertRaises((CommandError, SystemExit)):
            call_command("import_exposures", csv_path)

    def test_import_exposures_iaccs_conflict_rejected(self):
        Exposure.objects.create(
            account=self.account,
            as_of_date=date(2023, 6, 1),
            principal_outstanding=Decimal("8000"),
            accrued_interest=Decimal("0"),
            accrued_penalty=Decimal("0"),
            days_past_due=20,
            source="IACCS",
        )
        csv_path = self.create_csv("exposures.csv", self.HEADERS, [self.exposure_row])
        with self.assertRaises(CommandError) as cm:
            self._run(csv_path, cutoff="2023-06-01")
        self.assertIn("iAccs-tagged", str(cm.exception))