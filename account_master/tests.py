from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from account_master.models import (
    Borrower,
    LoanAccount,
    Exposure,
    DelinquencyStatus,
    RemedialStrategy,
    CollectionActivityLog,
)
from decimal import Decimal
from datetime import date, timedelta

User = get_user_model()


class AccountDetailViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", password="testpassword"
        )

        self.borrower = Borrower.objects.create(
            borrower_id="B001",
            full_name="John Doe",
            borrower_type="PERSON",
            primary_address="123 Main St",
        )
        self.loan_account = LoanAccount.objects.create(
            loan_id="LA001",
            borrower=self.borrower,
            booking_date=date.today() - timedelta(days=365),
            maturity_date=date.today() + timedelta(days=300),
            original_principal=Decimal("100000.00"),
            interest_rate=Decimal("0.05"),
            loan_type="Personal",
            status="PERFORMING",
        )

        # Create Exposure data
        self.exposure1 = Exposure.objects.create(
            account=self.loan_account,
            as_of_date=date.today() - timedelta(days=60),
            principal_outstanding=Decimal("90000.00"),
            accrued_interest=Decimal("1000.00"),
            accrued_penalty=Decimal("100.00"),
            total_exposure=Decimal("91100.00"),
            created_by=self.user,
        )
        self.latest_exposure = Exposure.objects.create(
            account=self.loan_account,
            as_of_date=date.today() - timedelta(days=10),
            principal_outstanding=Decimal("85000.00"),
            accrued_interest=Decimal("1500.00"),
            accrued_penalty=Decimal("150.00"),
            total_exposure=Decimal("86650.00"),
            created_by=self.user,
        )

        # Create Delinquency Status data
        self.delinquency1 = DelinquencyStatus.objects.create(
            account=self.loan_account,
            as_of_date=date.today() - timedelta(days=90),
            days_past_due=60,
            aging_bucket="60",
            classification="SM",
            created_by=self.user,
        )
        self.latest_delinquency = DelinquencyStatus.objects.create(
            account=self.loan_account,
            as_of_date=date.today() - timedelta(days=30),
            days_past_due=30,
            aging_bucket="30",
            classification="SM",
            created_by=self.user,
        )

        # Create Remedial Strategy data
        self.historical_strategy = RemedialStrategy.objects.create(
            account=self.loan_account,
            strategy_type="Intensive Collection",
            strategy_start_date=date.today() - timedelta(days=120),
            strategy_status="CANCELLED",
            created_by=self.user,
        )
        self.current_strategy = RemedialStrategy.objects.create(
            account=self.loan_account,
            strategy_type="Restructuring",
            strategy_start_date=date.today() - timedelta(days=50),
            strategy_status="ACTIVE",
            created_by=self.user,
        )

        # Create Collection Activity Log data
        self.activity1 = CollectionActivityLog.objects.create(
            account=self.loan_account,
            activity_date=date.today() - timedelta(days=20),
            activity_type="Call",
            remarks="Called borrower, no answer",
            staff_assigned="Agent X",
            created_by=self.user,
        )
        self.activity2 = CollectionActivityLog.objects.create(
            account=self.loan_account,
            activity_date=date.today() - timedelta(days=5),
            activity_type="Visit",
            remarks="Visited borrower, discussed payment",
            staff_assigned="Agent Y",
            created_by=self.user,
        )

    def test_account_detail_view_authenticated(self):
        self.client.login(username="testuser", password="testpassword")
        response = self.client.get(
            reverse("account_detail", kwargs={"loan_id": self.loan_account.loan_id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "account_master/account_detail.html")

    def test_account_detail_view_unauthenticated(self):
        response = self.client.get(
            reverse("account_detail", kwargs={"loan_id": self.loan_account.loan_id})
        )
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_account_detail_view_context(self):
        self.client.login(username="testuser", password="testpassword")
        response = self.client.get(
            reverse("account_detail", kwargs={"loan_id": self.loan_account.loan_id})
        )

        self.assertTrue("account" in response.context)
        self.assertEqual(response.context["account"], self.loan_account)

        self.assertTrue("latest_exposure" in response.context)
        self.assertEqual(response.context["latest_exposure"], self.latest_exposure)

        self.assertTrue("latest_delinquency" in response.context)
        self.assertEqual(
            response.context["latest_delinquency"], self.latest_delinquency
        )

        self.assertTrue("current_strategy" in response.context)
        self.assertEqual(response.context["current_strategy"], self.current_strategy)

        self.assertTrue("historical_exposure_table" in response.context)
        self.assertTrue("historical_delinquency_table" in response.context)
        self.assertTrue("historical_strategies_table" in response.context)
        self.assertTrue("collection_activities_table" in response.context)

        # Verify table data counts
        self.assertEqual(len(response.context["historical_exposure_table"].data), 2)
        self.assertEqual(len(response.context["historical_delinquency_table"].data), 2)
        self.assertEqual(
            len(response.context["historical_strategies_table"].data), 1
        )  # Only historical, not active
        self.assertEqual(len(response.context["collection_activities_table"].data), 2)

    def test_account_detail_view_content(self):
        self.client.login(username="testuser", password="testpassword")
        response = self.client.get(
            reverse("account_detail", kwargs={"loan_id": self.loan_account.loan_id})
        )

        # Check Borrower Summary Card
        self.assertContains(response, self.borrower.full_name)
        self.assertContains(response, self.borrower.borrower_id)

        # Check Account Detail Card
        self.assertContains(response, self.loan_account.loan_id)
        self.assertContains(response, "₱100,000.00")  # Using intcomma filter
        self.assertContains(
            response, self.loan_account.get_status_display()
        )  # "Performing"

        # Check Latest Exposure Card
        self.assertContains(response, "Latest Exposure")
        self.assertContains(response, "As of:")
        self.assertContains(response, self.latest_exposure.as_of_date.strftime("%b"))
        self.assertContains(response, str(self.latest_exposure.as_of_date.day))
        self.assertContains(response, str(self.latest_exposure.as_of_date.year))
        self.assertContains(response, "Total: ₱86,650.00")
        self.assertContains(response, "Principal: 85,000.00")
        self.assertContains(response, "Interest: 1,500.00")

        # Check Latest Delinquency Card
        self.assertContains(response, "Latest Delinquency")
        self.assertContains(response, "As of:")
        self.assertContains(response, self.latest_delinquency.as_of_date.strftime("%b"))
        self.assertContains(response, str(self.latest_delinquency.as_of_date.day))
        self.assertContains(response, str(self.latest_delinquency.as_of_date.year))
        self.assertContains(
            response, f"{self.latest_delinquency.days_past_due} Days Past Due"
        )
        self.assertContains(
            response, self.latest_delinquency.get_aging_bucket_display()
        )  # "30 days"
        self.assertContains(
            response, self.latest_delinquency.get_classification_display()
        )  # "Especially Mentioned"

        # Check Current Remedial Strategy Card
        self.assertContains(response, "Current Strategy")
        self.assertContains(response, "Start Date:")
        self.assertContains(
            response, self.current_strategy.strategy_start_date.strftime("%b")
        )
        self.assertContains(
            response, str(self.current_strategy.strategy_start_date.day)
        )
        self.assertContains(
            response, str(self.current_strategy.strategy_start_date.year)
        )
        self.assertContains(
            response, self.current_strategy.get_strategy_type_display()
        )  # "Restructuring"
        self.assertContains(
            response, self.current_strategy.get_strategy_status_display()
        )  # "Active"

        # Check presence of historical tables headers
        self.assertContains(response, "Historical Exposures")
        self.assertContains(response, "Historical Delinquency Status")
        self.assertContains(response, "Historical Remedial Strategies")
        self.assertContains(response, "Collection Activities")

        # Check some data in historical tables (using the exact string from the rendered HTML)
        self.assertContains(response, "85,000.00")  # Latest exposure in table
        self.assertContains(response, "90,000.00")  # Historical exposure in table
        self.assertContains(response, "30 days")  # Latest delinquency in table
        self.assertContains(response, "60 days")  # Historical delinquency in table
        self.assertContains(
            response, "Intensive Collection"
        )  # Historical strategy in table
        self.assertContains(
            response, "Cancelled"
        )  # Historical strategy status in table
        self.assertContains(
            response, "Called borrower, no answer"
        )  # From collection activities
        self.assertContains(
            response, "Visited borrower, discussed payment"
        )  # From collection activities
