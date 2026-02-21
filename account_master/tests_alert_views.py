from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from account_master.models import Alert, Borrower, LoanAccount
from datetime import date, timedelta
from decimal import Decimal

User = get_user_model()


class AlertListViewTests(TestCase):
    """Test cases for alert list view."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", email="testuser@example.com", password="testpassword"
        )

        # Create test borrower
        self.borrower = Borrower.objects.create(
            borrower_id="B001",
            full_name="John Doe",
            borrower_type="PERSON",
            primary_address="123 Main St",
        )

        # Create test loan account
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

        # Create test alerts
        self.alert1 = Alert.objects.create(
            alert_type=Alert.AlertType.CRITICAL,
            title="Critical Alert",
            message="This is critical",
            entity_type=Alert.EntityType.ACCOUNT,
            entity_id=self.loan_account.loan_id,
            severity=Alert.Severity.HIGH,
            status=Alert.Status.NEW,
            assigned_to=self.user,
            created_by=self.user,
        )

        self.alert2 = Alert.objects.create(
            alert_type=Alert.AlertType.WARNING,
            title="Warning Alert",
            message="This is a warning",
            entity_type=Alert.EntityType.ACCOUNT,
            entity_id=self.loan_account.loan_id,
            severity=Alert.Severity.MEDIUM,
            status=Alert.Status.ACKNOWLEDGED,
            assigned_to=self.user,
            created_by=self.user,
        )

    def test_alert_list_page_loads(self):
        """Test that the alert list page loads successfully."""
        # Login user
        self.client.login(email="testuser@example.com", password="testpassword")

        # Get alert list page
        response = self.client.get(reverse("alert_list"))

        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Alerts Management")
        self.assertContains(response, "Critical Alert")
        self.assertContains(response, "Warning Alert")

    def test_alert_list_filtering(self):
        """Test that alert filtering works."""
        # Login user
        self.client.login(email="testuser@example.com", password="testpassword")

        # Filter by critical alerts only
        response = self.client.get(reverse("alert_list") + "?alert_type=CRITICAL")

        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Critical Alert")
        self.assertNotContains(response, "Warning Alert")

    def test_alert_list_unauthenticated(self):
        """Test that unauthenticated users are redirected to login."""
        # Get alert list page without login
        response = self.client.get(reverse("alert_list"))

        # Should be redirected to login
        self.assertEqual(response.status_code, 302)
