from django.test import TestCase
from django.utils import timezone
import datetime
from decimal import Decimal
from account_master.models import Borrower, LoanAccount, CollectionActivityLog


class BorrowerModelTest(TestCase):
    def setUp(self):
        self.borrower = Borrower.objects.create(
            borrower_id="B001",
            borrower_type="PERSON",
            full_name="John Doe",
            primary_address="123 Main St",
            mobile="1234567890",
        )

    def test_borrower_creation(self):
        self.assertEqual(Borrower.objects.count(), 1)
        self.assertEqual(self.borrower.borrower_id, "B001")
        self.assertEqual(self.borrower.full_name, "John Doe")

    def test_borrower_str(self):
        self.assertEqual(str(self.borrower), "John Doe")

    def test_borrower_update(self):
        self.borrower.full_name = "Jane Doe"
        self.borrower.save()
        self.assertEqual(Borrower.objects.get(borrower_id="B001").full_name, "Jane Doe")

    def test_borrower_delete(self):
        self.borrower.delete()
        self.assertEqual(Borrower.objects.count(), 0)

    def test_borrower_choices(self):
        self.borrower.borrower_type = "CORP"
        self.borrower.save()
        self.assertEqual(self.borrower.borrower_type, "CORP")


class LoanAccountModelTest(TestCase):
    def setUp(self):
        self.borrower = Borrower.objects.create(
            borrower_id="B002",
            borrower_type="PERSON",
            full_name="Alice Smith",
            primary_address="456 Elm St",
        )
        self.loan = LoanAccount.objects.create(
            loan_id="L001",
            borrower=self.borrower,
            booking_date=datetime.date(2023, 1, 1),
            maturity_date=datetime.date(2024, 1, 1),
            original_principal=Decimal("10000.00"),
            interest_rate=Decimal("5.00"),
            loan_type="Personal",
            loan_security="UNSECURED",
            status="PERFORMING",
        )

    def test_loan_creation(self):
        self.assertEqual(LoanAccount.objects.count(), 1)
        self.assertEqual(self.loan.loan_id, "L001")
        self.assertEqual(self.loan.original_principal, Decimal("10000.00"))

    def test_loan_str(self):
        self.assertEqual(str(self.loan), "L001")

    def test_loan_update(self):
        self.loan.status = "PAST_DUE"
        self.loan.save()
        self.assertEqual(LoanAccount.objects.get(loan_id="L001").status, "PAST_DUE")

    def test_loan_delete(self):
        self.loan.delete()
        self.assertEqual(LoanAccount.objects.count(), 0)

    def test_loan_choices(self):
        self.loan.loan_security = "SECURED"
        self.loan.save()
        self.assertEqual(self.loan.loan_security, "SECURED")


class CollectionActivityLogModelTest(TestCase):
    def setUp(self):
        self.borrower = Borrower.objects.create(
            borrower_id="B003",
            borrower_type="PERSON",
            full_name="Bob Jones",
            primary_address="789 Oak St",
        )
        self.loan = LoanAccount.objects.create(
            loan_id="L002",
            borrower=self.borrower,
            booking_date=datetime.date(2023, 2, 1),
            maturity_date=datetime.date(2024, 2, 1),
            original_principal=Decimal("5000.00"),
            interest_rate=Decimal("10.00"),
            loan_type="Auto",
            loan_security="SECURED",
            status="PERFORMING",
        )
        self.activity = CollectionActivityLog.objects.create(
            account=self.loan,
            activity_date=datetime.date(2023, 3, 1),
            activity_type="Call",
            remarks="Called borrower",
            promise_to_pay_amount=Decimal("500.00"),
            promise_to_pay_date=datetime.date(2023, 3, 15),
            staff_assigned="Staff A",
        )

    def test_activity_creation(self):
        self.assertEqual(CollectionActivityLog.objects.count(), 1)
        self.assertEqual(self.activity.activity_type, "Call")
        self.assertEqual(self.activity.promise_to_pay_amount, Decimal("500.00"))

    def test_activity_str(self):
        expected_str = f"Call on 2023-03-01 for L002"
        self.assertEqual(str(self.activity), expected_str)

    def test_activity_update(self):
        self.activity.remarks = "Called borrower again"
        self.activity.save()
        self.assertEqual(
            CollectionActivityLog.objects.get(
                activity_id=self.activity.activity_id
            ).remarks,
            "Called borrower again",
        )

    def test_activity_delete(self):
        self.activity.delete()
        self.assertEqual(CollectionActivityLog.objects.count(), 0)

    def test_activity_choices(self):
        self.activity.activity_type = "Visit"
        self.activity.save()
        self.assertEqual(self.activity.activity_type, "Visit")
