from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from account_master.models import Borrower, LoanAccount

User = get_user_model()


class BorrowerViewsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", password="password123"
        )

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
            booking_date="2023-01-01",
            maturity_date="2024-01-01",
            original_principal=10000.00,
            interest_rate=5.00,
            loan_type="Personal",
            loan_security="UNSECURED",
            status="PERFORMING",
        )

    def test_borrower_list_auth_required(self):
        response = self.client.get(reverse("borrower_list"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/accounts/login/"))

    def test_borrower_list_authenticated(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("borrower_list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "account_master/borrower_list.html")
        self.assertIn("table", response.context)
        self.assertIn("filter", response.context)
        self.assertIn("breadcrumbs", response.context)

    def test_borrower_detail_auth_required(self):
        response = self.client.get(
            reverse("borrower_detail", args=[self.borrower.borrower_id])
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/accounts/login/"))

    def test_borrower_detail_authenticated(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("borrower_detail", args=[self.borrower.borrower_id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "account_master/borrower_detail.html")
        self.assertEqual(response.context["borrower"], self.borrower)
        self.assertIn("table", response.context)
        self.assertEqual(response.context["entity_type"], "borrower")

    def test_create_borrower_auth_required(self):
        response = self.client.get(reverse("create_borrower"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/accounts/login/"))

    def test_create_borrower_get(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("create_borrower"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "account_master/create_borrower.html")
        self.assertIn("form", response.context)

    def test_create_borrower_post(self):
        self.client.force_login(self.user)
        data = {
            "borrower_id": "B002",
            "borrower_type": "CORP",
            "full_name": "Acme Corp",
            "primary_address": "456 Business Rd",
            "mobile": "0987654321",
        }
        response = self.client.post(reverse("create_borrower"), data)
        self.assertRedirects(response, reverse("borrower_list"))
        self.assertTrue(Borrower.objects.filter(borrower_id="B002").exists())

    def test_update_borrower_auth_required(self):
        response = self.client.get(
            reverse("update_borrower", args=[self.borrower.borrower_id])
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/accounts/login/"))

    def test_update_borrower_get(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("update_borrower", args=[self.borrower.borrower_id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "account_master/update_borrower.html")
        self.assertIn("form", response.context)

    def test_update_borrower_post(self):
        self.client.force_login(self.user)
        data = {
            "borrower_id": self.borrower.borrower_id,
            "borrower_type": "PERSON",
            "full_name": "John Doe Updated",
            "primary_address": "123 Main St",
            "mobile": "1234567890",
        }
        response = self.client.post(
            reverse("update_borrower", args=[self.borrower.borrower_id]), data
        )
        self.assertRedirects(
            response, reverse("borrower_detail", args=[self.borrower.borrower_id])
        )
        self.borrower.refresh_from_db()
        self.assertEqual(self.borrower.full_name, "John Doe Updated")

    def test_update_borrower_updates_group(self):
        self.client.force_login(self.user)
        self.borrower.borrower_group = "Initial Group"
        self.borrower.save(update_fields=["borrower_group"])
        data = {
            "borrower_id": self.borrower.borrower_id,
            "borrower_type": "PERSON",
            "full_name": "John Doe Updated",
            "primary_address": "123 Main St",
            "mobile": "1234567890",
            "borrower_group": "Updated Group",
        }
        response = self.client.post(
            reverse("update_borrower", args=[self.borrower.borrower_id]), data
        )
        self.assertRedirects(
            response, reverse("borrower_detail", args=[self.borrower.borrower_id])
        )
        self.borrower.refresh_from_db()
        self.assertEqual(self.borrower.borrower_group, "Updated Group")
