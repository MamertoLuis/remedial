import datetime
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from account_master.models import (
    LoanAccount,
    Borrower,
    RemedialStrategy,
    CollectionActivityLog,
)

User = get_user_model()


class StrategyAndCollectionViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="password")

        self.borrower = Borrower.objects.create(
            borrower_id="B001",
            borrower_type="PERSON",
            full_name="John Doe",
            primary_address="123 Main St",
        )

        self.account = LoanAccount.objects.create(
            loan_id="L001",
            borrower=self.borrower,
            booking_date=datetime.date(2023, 1, 1),
            maturity_date=datetime.date(2024, 1, 1),
            original_principal=10000.00,
            interest_rate=5.00,
            loan_type="Personal",
            loan_security="UNSECURED",
            status="PERFORMING",
        )

        self.strategy = RemedialStrategy.objects.create(
            account=self.account,
            strategy_type="Restructuring",
            strategy_start_date=datetime.date(2023, 6, 1),
            strategy_status="ACTIVE",
        )

        self.activity = CollectionActivityLog.objects.create(
            account=self.account,
            activity_date=datetime.date(2023, 6, 15),
            activity_type="Call",
            remarks="Called borrower",
            staff_assigned="Agent Smith",
        )

    def test_remedial_strategy_list_auth_required(self):
        # The prompt asks for remedial_strategy_list, but the view is remedial_strategy_detail
        url = reverse(
            "remedial_strategy_detail",
            args=[self.account.loan_id, self.strategy.strategy_id],
        )
        response = self.client.get(url)
        self.assertNotEqual(response.status_code, 200)
        self.assertTrue(response.url.startswith("/accounts/login/"))

    def test_remedial_strategy_list(self):
        self.client.force_login(self.user)
        url = reverse(
            "remedial_strategy_detail",
            args=[self.account.loan_id, self.strategy.strategy_id],
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "account_master/remedial_strategy_detail.html"
        )
        self.assertEqual(response.context["account"], self.account)
        self.assertEqual(response.context["strategy"], self.strategy)
        self.assertIn("compromise_agreements_table", response.context)

    def test_create_remedial_strategy_auth_required(self):
        url = reverse("create_remedial_strategy", args=[self.account.loan_id])
        response = self.client.get(url)
        self.assertNotEqual(response.status_code, 200)

    def test_create_remedial_strategy_get(self):
        self.client.force_login(self.user)
        url = reverse("create_remedial_strategy", args=[self.account.loan_id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "account_master/create_remedial_strategy.html"
        )
        self.assertIn("form", response.context)

    def test_create_remedial_strategy_post(self):
        self.client.force_login(self.user)
        url = reverse("create_remedial_strategy", args=[self.account.loan_id])
        data = {
            "account": self.account.loan_id,
            "strategy_type": "Compromise",
            "strategy_start_date": "2023-07-01",
            "strategy_status": "ACTIVE",
            "strategy_outcome": "Pending",
        }
        response = self.client.post(url, data)
        self.assertRedirects(
            response, reverse("account_detail", args=[self.account.loan_id])
        )
        self.assertTrue(
            RemedialStrategy.objects.filter(strategy_type="Compromise").exists()
        )

    def test_update_remedial_strategy_auth_required(self):
        url = reverse(
            "update_remedial_strategy",
            args=[self.account.loan_id, self.strategy.strategy_id],
        )
        response = self.client.get(url)
        self.assertNotEqual(response.status_code, 200)

    def test_update_remedial_strategy_get(self):
        self.client.force_login(self.user)
        url = reverse(
            "update_remedial_strategy",
            args=[self.account.loan_id, self.strategy.strategy_id],
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "account_master/update_remedial_strategy.html"
        )
        self.assertEqual(response.context["remedial_strategy"], self.strategy)

    def test_update_remedial_strategy_post(self):
        self.client.force_login(self.user)
        url = reverse(
            "update_remedial_strategy",
            args=[self.account.loan_id, self.strategy.strategy_id],
        )
        data = {
            "account": self.account.loan_id,
            "strategy_type": "Restructuring",
            "strategy_start_date": "2023-06-01",
            "strategy_status": "COMPLETED",
            "strategy_outcome": "Success",
        }
        response = self.client.post(url, data)
        self.assertRedirects(
            response, reverse("account_detail", args=[self.account.loan_id])
        )
        self.strategy.refresh_from_db()
        self.assertEqual(self.strategy.strategy_status, "COMPLETED")

    def test_collection_activity_list(self):
        # Note: collection_activity_list does not have @login_required in the view
        url = reverse("collection_activity_list", args=[self.account.loan_id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "account_master/collection_activity_list.html"
        )
        self.assertEqual(response.context["account"], self.account)
        self.assertIn("table", response.context)

    def test_create_collection_activity_get(self):
        # Note: create_collection_activity does not have @login_required in the view
        url = reverse("create_collection_activity", args=[self.account.loan_id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "account_master/create_collection_activity.html"
        )
        self.assertIn("form", response.context)

    def test_create_collection_activity_post(self):
        self.client.force_login(self.user)
        url = reverse("create_collection_activity", args=[self.account.loan_id])
        data = {
            "account": self.account.loan_id,
            "activity_date": "2023-07-01",
            "activity_type": "Visit",
            "remarks": "Visited borrower",
            "staff_assigned": "Agent Jones",
        }
        response = self.client.post(url, data)
        self.assertRedirects(
            response, reverse("collection_activity_list", args=[self.account.loan_id])
        )
        self.assertTrue(
            CollectionActivityLog.objects.filter(activity_type="Visit").exists()
        )

    def test_update_collection_activity_auth_required(self):
        url = reverse(
            "update_collection_activity",
            args=[self.account.loan_id, self.activity.activity_id],
        )
        response = self.client.get(url)
        self.assertNotEqual(response.status_code, 200)

    def test_update_collection_activity_get(self):
        self.client.force_login(self.user)
        url = reverse(
            "update_collection_activity",
            args=[self.account.loan_id, self.activity.activity_id],
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "account_master/update_collection_activity.html"
        )
        self.assertEqual(response.context["activity"], self.activity)

    def test_update_collection_activity_post(self):
        self.client.force_login(self.user)
        url = reverse(
            "update_collection_activity",
            args=[self.account.loan_id, self.activity.activity_id],
        )
        data = {
            "account": self.account.loan_id,
            "activity_date": "2023-06-15",
            "activity_type": "Call",
            "remarks": "Called borrower again",
            "staff_assigned": "Agent Smith",
        }
        response = self.client.post(url, data)
        self.assertRedirects(
            response, reverse("collection_activity_list", args=[self.account.loan_id])
        )
        self.activity.refresh_from_db()
        self.assertEqual(self.activity.remarks, "Called borrower again")
