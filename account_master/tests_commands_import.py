import os
import tempfile
import csv
from datetime import date
from decimal import Decimal
from django.test import TestCase
from django.core.management import call_command
from django.core.management.base import CommandError

from account_master.models import Borrower, LoanAccount, Exposure


class ImportCommandsTestCase(TestCase):
    def setUp(self):
        # Create temporary directory for CSV files
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def create_csv(self, filename, headers, rows):
        filepath = os.path.join(self.temp_dir.name, filename)
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(rows)
        return filepath

    def test_import_borrowers_success(self):
        headers = [
            "borrower_id",
            "full_name",
            "borrower_type",
            "primary_address",
            "mobile",
        ]
        rows = [
            ["B001", "John Doe", "PERSON", "123 Main St", "555-1234"],
            ["B002", "Acme Corp", "CORP", "456 Market St", "555-5678"],
        ]
        csv_path = self.create_csv("borrowers.csv", headers, rows)

        call_command("import_borrowers", csv_path)

        self.assertEqual(Borrower.objects.count(), 2)
        b1 = Borrower.objects.get(borrower_id="B001")
        self.assertEqual(b1.full_name, "John Doe")
        self.assertEqual(b1.borrower_type, "PERSON")

        b2 = Borrower.objects.get(borrower_id="B002")
        self.assertEqual(b2.full_name, "Acme Corp")
        self.assertEqual(b2.borrower_type, "CORP")

    def test_import_borrowers_missing_headers(self):
        headers = ["borrower_id"]  # Missing full_name
        rows = [["B001"]]
        csv_path = self.create_csv("borrowers_bad.csv", headers, rows)

        with self.assertRaises(CommandError) as cm:
            call_command("import_borrowers", csv_path)

        self.assertIn("CSV file is empty or has no headers", str(cm.exception))

    def test_import_accounts_success(self):
        # First create a borrower
        Borrower.objects.create(
            borrower_id="B001", full_name="John Doe", borrower_type="PERSON"
        )

        headers = [
            "loan_id",
            "borrower_id",
            "booking_date",
            "maturity_date",
            "original_principal",
            "interest_rate",
            "loan_type",
            "account_officer_id",
            "status",
        ]
        rows = [
            [
                "L001",
                "B001",
                "2023-01-01",
                "2024-01-01",
                "10000.00",
                "0.05",
                "TERM",
                "AO1",
                "PERFORMING",
            ],
        ]
        csv_path = self.create_csv("accounts.csv", headers, rows)

        call_command("import_accounts", csv_path)

        self.assertEqual(LoanAccount.objects.count(), 1)
        loan = LoanAccount.objects.get(loan_id="L001")
        self.assertEqual(loan.borrower.borrower_id, "B001")
        self.assertEqual(loan.original_principal, Decimal("10000.00"))
        self.assertEqual(loan.booking_date, date(2023, 1, 1))

    def test_import_accounts_missing_borrower(self):
        headers = [
            "loan_id",
            "borrower_id",
            "booking_date",
            "maturity_date",
            "original_principal",
            "interest_rate",
            "loan_type",
            "account_officer_id",
            "status",
        ]
        rows = [
            [
                "L001",
                "B999",
                "2023-01-01",
                "2024-01-01",
                "10000.00",
                "0.05",
                "TERM",
                "AO1",
                "PERFORMING",
            ],
        ]
        csv_path = self.create_csv("accounts_bad.csv", headers, rows)

        with self.assertRaises(CommandError) as cm:
            call_command("import_accounts", csv_path)

        self.assertIn(
            "Borrower with borrower_id 'B999' does not exist", str(cm.exception)
        )

    def test_import_exposures_success(self):
        # Create borrower and loan account
        borrower = Borrower.objects.create(
            borrower_id="B001", full_name="John Doe", borrower_type="PERSON"
        )
        LoanAccount.objects.create(
            loan_id="L001",
            borrower=borrower,
            booking_date=date(2023, 1, 1),
            maturity_date=date(2024, 1, 1),
            original_principal=Decimal("10000.00"),
            interest_rate=Decimal("0.05"),
            loan_type="TERM",
            account_officer_id="AO1",
            status="PERFORMING",
        )

        headers = [
            "loan_id",
            "as_of_date",
            "principal_outstanding",
            "accrued_interest",
            "accrued_penalty",
            "days_past_due",
        ]
        rows = [
            ["L001", "2023-06-01", "5000.00", "100.00", "0.00", "0"],
        ]
        csv_path = self.create_csv("exposures.csv", headers, rows)

        call_command("import_exposures", csv_path)

        self.assertEqual(Exposure.objects.count(), 1)
        exposure = Exposure.objects.first()
        self.assertEqual(exposure.account.loan_id, "L001")
        self.assertEqual(exposure.principal_outstanding, Decimal("5000.00"))
        self.assertEqual(exposure.as_of_date, date(2023, 6, 1))

    def test_import_exposures_missing_loan(self):
        headers = [
            "loan_id",
            "as_of_date",
            "principal_outstanding",
            "accrued_interest",
            "accrued_penalty",
            "days_past_due",
        ]
        rows = [
            ["L999", "2023-06-01", "5000.00", "100.00", "0.00", "0"],
        ]
        csv_path = self.create_csv("exposures_bad.csv", headers, rows)

        with self.assertRaises(CommandError) as cm:
            call_command("import_exposures", csv_path)

        self.assertIn("Finished with 1 errors", str(cm.exception))
