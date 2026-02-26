import datetime
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model

from account_master.models import (
    Borrower,
    LoanAccount,
    CollectionActivityLog,
    RemedialStrategy,
    DelinquencyStatus,
    Exposure,
)
from compromise_agreement.models import CompromiseAgreement
from account_master.services.activity_service import ActivityService

User = get_user_model()


class ActivityServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpassword"
        )

        self.borrower = Borrower.objects.create(
            borrower_id="B001",
            borrower_type="PERSON",
            full_name="John Doe",
            created_by=self.user,
        )

        self.now = timezone.now()

        self.loan_account = LoanAccount.objects.create(
            loan_id="L001",
            borrower=self.borrower,
            status="PAST_DUE",
            booking_date=self.now.date(),
            maturity_date=self.now.date() + datetime.timedelta(days=365),
            original_principal=100000.00,
            interest_rate=5.0,
            loan_type="Personal",
            created_by=self.user,
        )

        # Create Collection Activity
        self.collection_activity = CollectionActivityLog.objects.create(
            account=self.loan_account,
            activity_type="Call",
            activity_date=self.now.date(),
            remarks="Called borrower",
            created_by=self.user,
        )

        # Create Remedial Strategy
        self.remedial_strategy = RemedialStrategy.objects.create(
            account=self.loan_account,
            strategy_type="Restructuring",
            strategy_status="ACTIVE",
            strategy_start_date=self.now.date(),
            created_by=self.user,
        )

        # Create Compromise Agreement
        self.compromise_agreement = CompromiseAgreement.objects.create(
            account=self.loan_account,
            strategy=self.remedial_strategy,
            compromise_id=1,
            original_total_exposure=100000.00,
            approved_compromise_amount=95000.00,
            status="ACTIVE",
            approval_date=self.now.date(),
            created_by=self.user,
        )

        # Create Delinquency Status (Significant)
        self.delinquency_status = DelinquencyStatus.objects.create(
            account=self.loan_account,
            as_of_date=self.now.date(),
            classification="DOUBTFUL",
            days_past_due=120,
            npl_flag=True,
            created_by=self.user,
        )

        # Create Exposure (Significant)
        self.exposure = Exposure.objects.create(
            account=self.loan_account,
            as_of_date=self.now.date(),
            principal_outstanding=1500000.00,
            accrued_interest=100000.00,
            accrued_penalty=50000.00,
            created_by=self.user,
        )

    def test_get_recent_activities_all(self):
        activities = ActivityService.get_recent_activities(limit=10)
        self.assertEqual(len(activities), 5)

        types = [a["type"] for a in activities]
        self.assertIn("collection", types)
        self.assertIn("compromise", types)
        self.assertIn("strategy", types)
        self.assertIn("delinquency", types)
        self.assertIn("exposure", types)

    def test_get_recent_activities_filtered(self):
        activities = ActivityService.get_recent_activities(
            limit=10, activity_types=["collection", "strategy"]
        )
        self.assertEqual(len(activities), 2)

        types = [a["type"] for a in activities]
        self.assertIn("collection", types)
        self.assertIn("strategy", types)
        self.assertNotIn("compromise", types)

    def test_get_recent_activities_date_range(self):
        start_date = self.now - datetime.timedelta(days=1)
        end_date = self.now + datetime.timedelta(days=1)

        activities = ActivityService.get_recent_activities(
            limit=10, date_range=(start_date, end_date)
        )
        self.assertEqual(len(activities), 5)

        # Test out of range
        past_start = self.now - datetime.timedelta(days=10)
        past_end = self.now - datetime.timedelta(days=5)
        activities_past = ActivityService.get_recent_activities(
            limit=10, date_range=(past_start, past_end)
        )
        self.assertEqual(len(activities_past), 0)

    def test_get_activity_summary(self):
        summary = ActivityService.get_activity_summary(days=7)
        self.assertEqual(summary["collection"], 1)
        self.assertEqual(summary["compromise"], 1)
        self.assertEqual(summary["strategy"], 1)
        self.assertEqual(summary["delinquency"], 1)
        self.assertEqual(summary["exposure"], 1)

    def test_get_activities_by_user(self):
        activities = ActivityService.get_activities_by_user(self.user, limit=10)
        self.assertEqual(len(activities), 5)
        for activity in activities:
            self.assertEqual(activity["created_by"], self.user)

    def test_get_activities_by_user_unauthenticated(self):
        from django.contrib.auth.models import AnonymousUser

        activities = ActivityService.get_activities_by_user(AnonymousUser(), limit=10)
        self.assertEqual(len(activities), 0)

    def test_delinquency_insignificant_not_included(self):
        # Create insignificant delinquency
        DelinquencyStatus.objects.create(
            account=self.loan_account,
            as_of_date=self.now.date() - datetime.timedelta(days=1),
            classification="SUBSTANDARD",
            days_past_due=30,
            npl_flag=False,
            created_by=self.user,
        )

        activities = ActivityService.get_recent_activities(
            limit=10, activity_types=["delinquency"]
        )
        # Only the significant one created in setUp should be returned
        self.assertEqual(len(activities), 1)
        self.assertEqual(activities[0]["description"], "DOUBTFUL (120 DPD)")

    def test_exposure_insignificant_not_included(self):
        # Create insignificant exposure
        Exposure.objects.create(
            account=self.loan_account,
            as_of_date=self.now.date() - datetime.timedelta(days=1),
            principal_outstanding=100000.00,
            accrued_interest=10000.00,
            accrued_penalty=5000.00,
            created_by=self.user,
        )

        activities = ActivityService.get_recent_activities(
            limit=10, activity_types=["exposure"]
        )
        # Only the significant one created in setUp should be returned
        self.assertEqual(len(activities), 1)
        self.assertEqual(activities[0]["description"], "Total: 1,650,000.00")
