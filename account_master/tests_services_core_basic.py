from datetime import date
from decimal import Decimal
from django.test import TestCase
from account_master.models import Borrower, LoanAccount, Exposure
from account_master.services import (
    upsert_borrower,
    upsert_loan_account,
    _update_loan_account_status,
)


class CoreServicesBasicTests(TestCase):
    def test_upsert_borrower_create(self):
        defaults = {
            "borrower_type": "PERSON",
            "full_name": "John Doe",
            "primary_address": "123 Main St",
            "mobile": "1234567890",
        }
        borrower, created = upsert_borrower(borrower_id="B001", defaults=defaults)
        self.assertTrue(created)
        self.assertEqual(borrower.borrower_id, "B001")
        self.assertEqual(borrower.full_name, "John Doe")

    def test_upsert_borrower_update(self):
        defaults = {
            "borrower_type": "PERSON",
            "full_name": "John Doe",
            "primary_address": "123 Main St",
            "mobile": "1234567890",
        }
        upsert_borrower(borrower_id="B001", defaults=defaults)

        update_defaults = {
            "borrower_type": "PERSON",
            "full_name": "John Doe Updated",
            "primary_address": "123 Main St",
            "mobile": "1234567890",
        }
        borrower, created = upsert_borrower(
            borrower_id="B001", defaults=update_defaults
        )
        self.assertFalse(created)
        self.assertEqual(borrower.full_name, "John Doe Updated")

    def test_upsert_loan_account_create(self):
        borrower, _ = upsert_borrower(
            borrower_id="B001",
            defaults={
                "full_name": "John Doe",
                "primary_address": "123 Main St",
                "mobile": "1234567890",
            },
        )
        defaults = {
            "borrower": borrower,
            "booking_date": date(2023, 1, 1),
            "maturity_date": date(2024, 1, 1),
            "original_principal": Decimal("10000.00"),
            "interest_rate": Decimal("5.00"),
            "loan_type": "Personal",
            "account_officer_id": "AO01",
            "status": "PERFORMING",
            "loan_security": "UNSECURED",
        }
        loan, created = upsert_loan_account(loan_id="L001", defaults=defaults)
        self.assertTrue(created)
        self.assertEqual(loan.loan_id, "L001")
        self.assertEqual(loan.original_principal, Decimal("10000.00"))

    def test_upsert_loan_account_update(self):
        borrower, _ = upsert_borrower(
            borrower_id="B001",
            defaults={
                "full_name": "John Doe",
                "primary_address": "123 Main St",
                "mobile": "1234567890",
            },
        )
        defaults = {
            "borrower": borrower,
            "booking_date": date(2023, 1, 1),
            "maturity_date": date(2024, 1, 1),
            "original_principal": Decimal("10000.00"),
            "interest_rate": Decimal("5.00"),
            "loan_type": "Personal",
            "account_officer_id": "AO01",
            "status": "PERFORMING",
            "loan_security": "UNSECURED",
        }
        upsert_loan_account(loan_id="L001", defaults=defaults)

        update_defaults = defaults.copy()
        update_defaults["original_principal"] = Decimal("15000.00")

        loan, created = upsert_loan_account(loan_id="L001", defaults=update_defaults)
        self.assertFalse(created)
        self.assertEqual(loan.original_principal, Decimal("15000.00"))

    def test_update_loan_account_status_transitions(self):
        borrower, _ = upsert_borrower(
            borrower_id="B001",
            defaults={
                "full_name": "John Doe",
                "primary_address": "123 Main St",
                "mobile": "1234567890",
            },
        )
        loan, _ = upsert_loan_account(
            loan_id="L001",
            defaults={
                "borrower": borrower,
                "booking_date": date(2023, 1, 1),
                "maturity_date": date(2024, 1, 1),
                "original_principal": Decimal("10000.00"),
                "interest_rate": Decimal("5.00"),
                "loan_type": "Personal",
                "account_officer_id": "AO01",
                "status": "PERFORMING",
            },
        )

        # Test PERFORMING
        _update_loan_account_status(loan, "C")
        loan.refresh_from_db()
        self.assertEqual(loan.status, "PERFORMING")

        # Test PAST_DUE
        _update_loan_account_status(loan, "SM")
        loan.refresh_from_db()
        self.assertEqual(loan.status, "PAST_DUE")

        # Test NPL
        for classification in ["SS", "D", "L"]:
            _update_loan_account_status(loan, classification)
            loan.refresh_from_db()
            self.assertEqual(loan.status, "NPL")

        # Test WRITEOFF and CLOSED based on exposure
        Exposure.objects.create(
            account=loan,
            as_of_date=date(2023, 2, 1),
            principal_outstanding=Decimal("1.00"),
            accrued_interest=Decimal("0.00"),
            accrued_penalty=Decimal("0.00"),
        )
        _update_loan_account_status(loan, "L")
        loan.refresh_from_db()
        self.assertEqual(loan.status, "WRITEOFF")

        Exposure.objects.create(
            account=loan,
            as_of_date=date(2023, 3, 1),
            principal_outstanding=Decimal("0.00"),
            accrued_interest=Decimal("0.00"),
            accrued_penalty=Decimal("0.00"),
        )
        _update_loan_account_status(loan, "C")
        loan.refresh_from_db()
        self.assertEqual(loan.status, "CLOSED")
