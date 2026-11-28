from datetime import date
from decimal import Decimal
from django.test import TestCase

from account_master.models import (
    Borrower,
    LoanAccount,
    CollectionActivityLog,
    RemedialStrategy,
)
from account_master.services import (
    create_collection_activity,
    create_remedial_strategy,
)


class CoreActivityServicesTests(TestCase):
    def setUp(self):
        self.borrower = Borrower.objects.create(
            borrower_id="B001",
            borrower_type="PERSON",
            full_name="John Doe",
            primary_address="123 Main St",
            mobile="1234567890",
        )
        self.loan_account = LoanAccount.objects.create(
            loan_id="L001",
            borrower=self.borrower,
            booking_date=date(2023, 1, 1),
            maturity_date=date(2024, 1, 1),
            original_principal=Decimal("10000.00"),
            interest_rate=Decimal("5.00"),
            loan_type="Personal",
            loan_security="UNSECURED",
            account_officer_id="AO01",
            status="PERFORMING",
        )

    def test_create_collection_activity(self):
        activity_date = date(2023, 6, 1)
        activity_type = "Call"
        remarks = "Called borrower, promised to pay next week."

        activity = create_collection_activity(
            account=self.loan_account,
            activity_date=activity_date,
            activity_type=activity_type,
            remarks=remarks,
            promise_to_pay_amount=Decimal("500.00"),
            promise_to_pay_date=date(2023, 6, 8),
            staff_assigned="Staff A",
        )

        self.assertIsInstance(activity, CollectionActivityLog)
        self.assertEqual(activity.account, self.loan_account)
        self.assertEqual(activity.activity_date, activity_date)
        self.assertEqual(activity.activity_type, activity_type)
        self.assertEqual(activity.remarks, remarks)
        self.assertEqual(activity.promise_to_pay_amount, Decimal("500.00"))
        self.assertEqual(activity.promise_to_pay_date, date(2023, 6, 8))
        self.assertEqual(activity.staff_assigned, "Staff A")

        # Verify it was saved to the database
        self.assertTrue(
            CollectionActivityLog.objects.filter(
                activity_id=activity.activity_id
            ).exists()
        )

    def test_create_remedial_strategy(self):
        strategy_type = "Restructuring"
        strategy_start_date = date(2023, 7, 1)

        strategy = create_remedial_strategy(
            account=self.loan_account,
            strategy_type=strategy_type,
            strategy_start_date=strategy_start_date,
            strategy_outcome="Pending",
        )

        self.assertIsInstance(strategy, RemedialStrategy)
        self.assertEqual(strategy.account, self.loan_account)
        self.assertEqual(strategy.strategy_type, strategy_type)
        self.assertEqual(strategy.strategy_start_date, strategy_start_date)
        self.assertEqual(strategy.strategy_outcome, "Pending")

        # Verify it was saved to the database
        self.assertTrue(
            RemedialStrategy.objects.filter(strategy_id=strategy.strategy_id).exists()
        )
