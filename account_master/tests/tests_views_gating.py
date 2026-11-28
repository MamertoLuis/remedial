import csv
import os
import tempfile
from datetime import date, timedelta

from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from account_master.decorators import system_admin_required
from account_master.models import Borrower, LoanAccount, Exposure
from account_master.services import upsert_borrower, upsert_loan_account, upsert_exposure

User = get_user_model()


def _make_user(username="officer", role=None, **kwargs):
    user = User.objects.create_user(username=username, password="password123")
    if role is not None:
        user.role = role
        user.save()
    return user


class SystemAdminRequiredDecoratorTests(TestCase):
    """Task 2.1: the shared ``system_admin_required`` decorator."""

    def test_decorator_redirects_anonymous_user_to_login(self):
        # The decorator composes @login_required; anonymous users are
        # redirected to the login page rather than seeing a 403.
        response = self.client.get(reverse("create_borrower"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/accounts/login/"))

    def test_non_admin_role_receives_403(self):
        user = _make_user(role=User.Role.MANAGER)
        self.client.force_login(user)
        response = self.client.get(reverse("create_borrower"))
        self.assertEqual(response.status_code, 403)
        self.assertTemplateUsed(response, "account_master/403.html")

    def test_system_administrator_is_allowed(self):
        user = _make_user(role=User.Role.SYSTEM_ADMINISTRATOR)
        self.client.force_login(user)
        response = self.client.get(reverse("create_borrower"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "account_master/create_borrower.html")


class CoreDataEditAllowedContextTests(TestCase):
    """Task 2.2: the ``core_data_edit_allowed`` template context flag."""

    def setUp(self):
        self.borrower = Borrower.objects.create(
            borrower_id="B001",
            full_name="John Doe",
            borrower_type="PERSON",
            primary_address="123 Main St",
        )

    def test_flag_true_for_system_administrator(self):
        user = _make_user(role=User.Role.SYSTEM_ADMINISTRATOR)
        self.client.force_login(user)
        response = self.client.get(
            reverse("borrower_detail", args=[self.borrower.borrower_id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["core_data_edit_allowed"])

    def test_flag_false_for_other_roles(self):
        for role in (User.Role.ACCOUNT_OFFICER, User.Role.MANAGER, User.Role.BOARD_MEMBER):
            user = _make_user(username=f"user_{role}", role=role)
            self.client.force_login(user)
            response = self.client.get(
                reverse("borrower_detail", args=[self.borrower.borrower_id])
            )
            self.assertEqual(response.status_code, 200)
            self.assertFalse(response.context["core_data_edit_allowed"])


class BorrowerGatingViewTests(TestCase):
    """Task 3.1: Borrower fact-plane views are admin-gated."""

    def setUp(self):
        self.borrower = Borrower.objects.create(
            borrower_id="B001",
            full_name="John Doe",
            borrower_type="PERSON",
            primary_address="123 Main St",
        )
        self.officer = _make_user(role=User.Role.ACCOUNT_OFFICER)
        self.admin = _make_user(username="admin", role=User.Role.SYSTEM_ADMINISTRATOR)

    def _borrower_payload(self, **overrides):
        data = {
            "borrower_id": "B002",
            "borrower_type": "CORP",
            "full_name": "Acme Corp",
            "primary_address": "456 Business Rd",
            "mobile": "0987654321",
        }
        data.update(overrides)
        return data

    def test_non_admin_create_borrower_forbidden_and_no_write(self):
        self.client.force_login(self.officer)
        response = self.client.post(reverse("create_borrower"), self._borrower_payload())
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Borrower.objects.filter(borrower_id="B002").exists())

    def test_non_admin_update_borrower_forbidden_and_no_write(self):
        self.client.force_login(self.officer)
        response = self.client.post(
            reverse("update_borrower", args=[self.borrower.borrower_id]),
            self._borrower_payload(borrower_id="B001", full_name="Hijacked"),
        )
        self.assertEqual(response.status_code, 403)
        self.borrower.refresh_from_db()
        self.assertEqual(self.borrower.full_name, "John Doe")

    def test_non_admin_delete_borrower_forbidden(self):
        self.client.force_login(self.officer)
        response = self.client.post(
            reverse("delete_borrower", args=[self.borrower.borrower_id])
        )
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Borrower.objects.filter(borrower_id="B001").exists())

    def test_admin_create_borrower_succeeds(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("create_borrower"), self._borrower_payload())
        self.assertRedirects(response, reverse("borrower_list"))
        self.assertTrue(Borrower.objects.filter(borrower_id="B002").exists())

    def test_admin_update_borrower_succeeds(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("update_borrower", args=[self.borrower.borrower_id]),
            self._borrower_payload(borrower_id="B001", full_name="Updated Name"),
        )
        self.assertRedirects(
            response, reverse("borrower_detail", args=[self.borrower.borrower_id])
        )
        self.borrower.refresh_from_db()
        self.assertEqual(self.borrower.full_name, "Updated Name")

    def test_admin_delete_borrower_succeeds(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("delete_borrower", args=[self.borrower.borrower_id])
        )
        self.assertRedirects(response, reverse("borrower_list"))
        self.assertFalse(Borrower.objects.filter(borrower_id="B001").exists())

    def test_read_views_still_available_to_non_admin(self):
        self.client.force_login(self.officer)
        response = self.client.get(reverse("borrower_list"))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(
            reverse("borrower_detail", args=[self.borrower.borrower_id])
        )
        self.assertEqual(response.status_code, 200)


class AccountGatingViewTests(TestCase):
    """Task 3.2: LoanAccount fact-plane views are admin-gated."""

    def setUp(self):
        self.borrower = Borrower.objects.create(
            borrower_id="B001",
            full_name="John Doe",
            borrower_type="PERSON",
            primary_address="123 Main St",
        )
        self.account = LoanAccount.objects.create(
            loan_id="L001",
            borrower=self.borrower,
            booking_date=date.today(),
            maturity_date=date.today(),
            original_principal=100000.00,
            interest_rate=5.00,
            loan_type="TERM_LOAN",
            status="PERFORMING",
        )
        self.officer = _make_user(role=User.Role.ACCOUNT_OFFICER)
        self.admin = _make_user(username="admin", role=User.Role.SYSTEM_ADMINISTRATOR)

    def _account_payload(self, **overrides):
        data = {
            "loan_id": "L002",
            "borrower": self.borrower.pk,
            "booking_date": date.today().isoformat(),
            "maturity_date": date.today().isoformat(),
            "original_principal": 50000.00,
            "interest_rate": 6.00,
            "loan_type": "TERM_LOAN",
            "loan_security": "UNSECURED",
            "status": "PERFORMING",
        }
        data.update(overrides)
        return data

    def test_non_admin_create_account_forbidden_and_no_write(self):
        self.client.force_login(self.officer)
        response = self.client.post(reverse("create_account"), self._account_payload())
        self.assertEqual(response.status_code, 403)
        self.assertFalse(LoanAccount.objects.filter(loan_id="L002").exists())

    def test_non_admin_create_account_for_borrower_forbidden(self):
        self.client.force_login(self.officer)
        response = self.client.post(
            reverse("create_account_for_borrower", args=[self.borrower.borrower_id]),
            self._account_payload(),
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(LoanAccount.objects.filter(loan_id="L002").exists())

    def test_non_admin_update_account_forbidden_and_no_write(self):
        self.client.force_login(self.officer)
        response = self.client.post(
            reverse("update_account", args=[self.account.loan_id]),
            self._account_payload(loan_id="L001", original_principal=999999.00),
        )
        self.assertEqual(response.status_code, 403)
        self.account.refresh_from_db()
        self.assertEqual(self.account.original_principal, 100000.00)

    def test_non_admin_update_account_status_forbidden_and_unchanged(self):
        self.client.force_login(self.officer)
        response = self.client.post(
            reverse("update_account_status", args=[self.account.loan_id])
        )
        self.assertEqual(response.status_code, 403)
        self.account.refresh_from_db()
        self.assertEqual(self.account.status, "PERFORMING")

    def test_admin_create_account_succeeds(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("create_account"), self._account_payload())
        self.assertRedirects(response, reverse("account_list"))
        self.assertTrue(LoanAccount.objects.filter(loan_id="L002").exists())

    def test_admin_update_account_status_succeeds(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("update_account_status", args=[self.account.loan_id])
        )
        self.assertEqual(response.status_code, 200)
        self.account.refresh_from_db()
        self.assertEqual(self.account.status, "PAST_DUE")


class ExposureGatingViewTests(TestCase):
    """Task 3.3: Exposure fact-plane views are admin-gated."""

    def setUp(self):
        self.borrower = Borrower.objects.create(
            borrower_id="B001",
            full_name="John Doe",
            borrower_type="PERSON",
            primary_address="123 Main St",
        )
        self.account = LoanAccount.objects.create(
            loan_id="L001",
            borrower=self.borrower,
            booking_date=date.today(),
            maturity_date=date.today(),
            original_principal=100000.00,
            interest_rate=5.00,
            loan_type="TERM_LOAN",
            status="PERFORMING",
        )
        self.exposure = Exposure.objects.create(
            account=self.account,
            as_of_date=date.today(),
            principal_outstanding=50000.00,
            accrued_interest=1000.00,
            accrued_penalty=0.00,
            days_past_due=0,
            snapshot_type="EVENT",
        )
        self.officer = _make_user(role=User.Role.ACCOUNT_OFFICER)
        self.admin = _make_user(username="admin", role=User.Role.SYSTEM_ADMINISTRATOR)

    def _exposure_payload(self, **overrides):
        data = {
            "account": self.account.pk,
            "as_of_date": date.today().isoformat(),
            "snapshot_type": "EVENT",
            "principal_outstanding": 60000.00,
            "accrued_interest": 1200.00,
            "accrued_penalty": 0.00,
            "days_past_due": 0,
        }
        data.update(overrides)
        return data

    def test_non_admin_create_exposure_forbidden_and_no_write(self):
        self.client.force_login(self.officer)
        count_before = Exposure.objects.filter(account=self.account).count()
        response = self.client.post(
            reverse("create_exposure", args=[self.account.loan_id]),
            self._exposure_payload(),
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            Exposure.objects.filter(account=self.account).count(), count_before
        )

    def test_non_admin_update_exposure_forbidden_and_no_write(self):
        self.client.force_login(self.officer)
        response = self.client.post(
            reverse(
                "update_exposure",
                args=[self.account.loan_id, self.exposure.exposure_id],
            ),
            self._exposure_payload(principal_outstanding=999999.00),
        )
        self.assertEqual(response.status_code, 403)
        self.exposure.refresh_from_db()
        self.assertEqual(self.exposure.principal_outstanding, 50000.00)

    def test_admin_create_exposure_succeeds(self):
        self.client.force_login(self.admin)
        # Use a different as_of_date to avoid the (account, as_of_date) unique
        # constraint already occupied by the setup exposure.
        response = self.client.post(
            reverse("create_exposure", args=[self.account.loan_id]),
            self._exposure_payload(as_of_date=(date.today() - timedelta(days=1)).isoformat()),
        )
        self.assertRedirects(response, reverse("account_detail", args=[self.account.loan_id]))
        self.assertTrue(
            Exposure.objects.filter(
                account=self.account, principal_outstanding=60000.00
            ).exists()
        )

    def test_admin_update_exposure_succeeds(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse(
                "update_exposure",
                args=[self.account.loan_id, self.exposure.exposure_id],
            ),
            self._exposure_payload(principal_outstanding=70000.00),
        )
        self.assertRedirects(response, reverse("account_detail", args=[self.account.loan_id]))
        self.exposure.refresh_from_db()
        self.assertEqual(self.exposure.principal_outstanding, 70000.00)


class ReadOnlyTemplateTests(TestCase):
    """Task 4.1: non-admins see read-only pages without fact-plane controls."""

    def setUp(self):
        self.borrower = Borrower.objects.create(
            borrower_id="B001",
            full_name="John Doe",
            borrower_type="PERSON",
            primary_address="123 Main St",
        )
        self.account = LoanAccount.objects.create(
            loan_id="L001",
            borrower=self.borrower,
            booking_date=date.today(),
            maturity_date=date.today(),
            original_principal=100000.00,
            interest_rate=5.00,
            loan_type="TERM_LOAN",
            status="PERFORMING",
        )
        self.exposure = Exposure.objects.create(
            account=self.account,
            as_of_date=date.today(),
            principal_outstanding=50000.00,
            accrued_interest=1000.00,
            accrued_penalty=0.00,
            days_past_due=0,
            snapshot_type="EVENT",
        )
        self.officer = _make_user(role=User.Role.ACCOUNT_OFFICER)
        self.admin = _make_user(username="admin", role=User.Role.SYSTEM_ADMINISTRATOR)

    def test_non_admin_pages_have_no_fact_plane_edit_urls(self):
        self.client.force_login(self.officer)
        pages = [
            reverse("borrower_list"),
            reverse("borrower_detail", args=[self.borrower.borrower_id]),
            reverse("account_list"),
            reverse("account_detail", args=[self.account.loan_id]),
        ]
        for page in pages:
            response = self.client.get(page)
            self.assertEqual(response.status_code, 200)
            self.assertNotContains(response, "create_borrower", html=False)
            self.assertNotContains(response, "create_account", html=False)
            self.assertNotContains(response, "update_account", html=False)
            self.assertNotContains(response, "update_borrower", html=False)
            self.assertNotContains(response, "delete_borrower", html=False)
            self.assertNotContains(response, "create_exposure", html=False)
            self.assertNotContains(response, "update_exposure", html=False)
            self.assertNotContains(response, "update_account_status", html=False)

    def test_admin_pages_render_fact_plane_controls(self):
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse("borrower_detail", args=[self.borrower.borrower_id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("update_borrower", args=["B001"]))
        self.assertContains(response, reverse("create_account_for_borrower", args=["B001"]))

        response = self.client.get(
            reverse("account_detail", args=[self.account.loan_id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("update_account", args=["L001"]))
        self.assertContains(response, reverse("create_exposure", args=["L001"]))

        response = self.client.get(reverse("borrower_list"))
        self.assertContains(response, reverse("create_borrower"))

        response = self.client.get(reverse("account_list"))
        self.assertContains(response, reverse("create_account"))


class ForbiddenPageMessageTests(TestCase):
    """Task 4.2: parameterized 403 page messaging."""

    def setUp(self):
        self.borrower = Borrower.objects.create(
            borrower_id="B001",
            full_name="John Doe",
            borrower_type="PERSON",
            primary_address="123 Main St",
        )
        self.account = LoanAccount.objects.create(
            loan_id="L001",
            borrower=self.borrower,
            booking_date=date.today(),
            maturity_date=date.today(),
            original_principal=100000.00,
            interest_rate=5.00,
            loan_type="TERM_LOAN",
            status="PERFORMING",
        )

    def test_fact_plane_gate_mentions_system_administrator(self):
        officer = _make_user(role=User.Role.ACCOUNT_OFFICER)
        self.client.force_login(officer)
        response = self.client.get(reverse("create_borrower"))
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "SYSTEM_ADMINISTRATOR", status_code=403)

    def test_delinquency_gate_mentions_manager_or_board_member(self):
        officer = _make_user(role=User.Role.ACCOUNT_OFFICER)
        self.client.force_login(officer)
        response = self.client.get(
            reverse("create_delinquency_status", args=[self.account.loan_id])
        )
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "MANAGER or BOARD_MEMBER", status_code=403)
        self.assertNotContains(response, "SYSTEM_ADMINISTRATOR", status_code=403)


class RefreshPipelineRegressionTests(TestCase):
    """Task 5.1: refresh pipeline (service upserts + import command) is ungated."""

    def test_service_upserts_write_without_a_user(self):
        """Upserts run with no authenticated user in the request context."""
        client = Client()  # anonymous context
        self.assertFalse(client.session.get("_auth_user_id"))
        del client  # the service layer must not depend on request context

        created_borrower, _ = upsert_borrower(
            borrower_id="B001",
            defaults={
                "borrower_type": "PERSON",
                "full_name": "John Doe",
                "primary_address": "123 Main St",
                "mobile": "555-1234",
            },
        )
        self.assertTrue(created_borrower.pk)

        created_account, _ = upsert_loan_account(
            loan_id="L001",
            defaults={
                "borrower": created_borrower,
                "booking_date": date.today(),
                "maturity_date": date.today(),
                "original_principal": 100000.00,
                "interest_rate": 5.00,
                "loan_type": "TERM_LOAN",
                "account_officer_id": "OFF001",
                "status": "PERFORMING",
            },
        )
        self.assertTrue(created_account.pk)

        created_exposure, _ = upsert_exposure(
            account=created_account,
            as_of_date=date.today(),
            defaults={
                "principal_outstanding": 50000.00,
                "accrued_interest": 1000.00,
                "accrued_penalty": 0.00,
                "days_past_due": 0,
                "snapshot_type": "EVENT",
            },
        )
        self.assertTrue(created_exposure.pk)

    def test_import_command_writes_without_a_user(self):
        """The CSV import command path writes facts with no role required."""
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = os.path.join(tmp, "borrowers.csv")
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(
                    ["borrower_id", "full_name", "borrower_type", "primary_address", "mobile"]
                )
                writer.writerow(
                    ["B100", "Imported Corp", "CORP", "789 Import Rd", "555-0000"]
                )
            call_command("import_borrowers", csv_path)

        self.assertTrue(Borrower.objects.filter(borrower_id="B100").exists())
