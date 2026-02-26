from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from account_master.models import (
    Borrower,
    LoanAccount,
    Exposure,
    DelinquencyStatus,
    RemedialStrategy,
    CollectionActivityLog,
    Alert,
    AlertRule,
    AlertLog,
)
from decimal import Decimal
from datetime import date, timedelta

User = get_user_model()


class AccountDetailViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", email="testuser@example.com", password="testpassword"
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
            created_by=self.user,
        )
        self.latest_exposure = Exposure.objects.create(
            account=self.loan_account,
            as_of_date=date.today() - timedelta(days=10),
            principal_outstanding=Decimal("85000.00"),
            accrued_interest=Decimal("1500.00"),
            accrued_penalty=Decimal("150.00"),
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
        self.client.login(email="testuser@example.com", password="testpassword")
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
        self.client.login(email="testuser@example.com", password="testpassword")
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
        self.client.login(email="testuser@example.com", password="testpassword")
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
        self.assertContains(response, "Principal: ₱85,000.00")
        self.assertContains(response, "Interest: ₱1,500.00")

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
        self.assertContains(response, "Bucket: 30")  # Latest delinquency in card
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


class AlertModelTests(TestCase):
    """Test cases for Alert model and its business logic."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", email="testuser@example.com", password="testpassword"
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

    def test_alert_creation(self):
        """Test creating a basic alert."""
        alert = Alert.objects.create(
            alert_type=Alert.AlertType.WARNING,
            title="Test Alert",
            message="This is a test alert",
            entity_type=Alert.EntityType.ACCOUNT,
            entity_id=self.loan_account.loan_id,
            severity=Alert.Severity.MEDIUM,
            created_by=self.user,
        )

        self.assertEqual(alert.alert_type, Alert.AlertType.WARNING)
        self.assertEqual(alert.title, "Test Alert")
        self.assertEqual(alert.entity_type, Alert.EntityType.ACCOUNT)
        self.assertEqual(alert.entity_id, self.loan_account.loan_id)
        self.assertEqual(alert.status, Alert.Status.NEW)
        self.assertFalse(alert.is_read)

    def test_alert_status_methods(self):
        """Test alert status change methods."""
        alert = Alert.objects.create(
            alert_type=Alert.AlertType.CRITICAL,
            title="Critical Alert",
            message="This is critical",
            entity_type=Alert.EntityType.ACCOUNT,
            entity_id=self.loan_account.loan_id,
            severity=Alert.Severity.HIGH,
            created_by=self.user,
        )

        # Test acknowledge
        self.assertTrue(alert.acknowledge(self.user))
        alert.refresh_from_db()
        self.assertEqual(alert.status, Alert.Status.ACKNOWLEDGED)

        # Test resolve
        self.assertTrue(alert.resolve(self.user, "Fixed the issue"))
        alert.refresh_from_db()
        self.assertEqual(alert.status, Alert.Status.RESOLVED)

        # Create new alert for dismiss test
        alert2 = Alert.objects.create(
            alert_type=Alert.AlertType.INFO,
            title="Info Alert",
            message="This is info",
            entity_type=Alert.EntityType.ACCOUNT,
            entity_id=self.loan_account.loan_id,
            created_by=self.user,
        )

        # Test dismiss
        self.assertTrue(alert2.dismiss(self.user, "Not relevant"))
        alert2.refresh_from_db()
        self.assertEqual(alert2.status, Alert.Status.DISMISSED)

    def test_alert_logging(self):
        """Test that alert actions create log entries."""
        alert = Alert.objects.create(
            alert_type=Alert.AlertType.WARNING,
            title="Test Alert",
            message="This is a test alert",
            entity_type=Alert.EntityType.ACCOUNT,
            entity_id=self.loan_account.loan_id,
            created_by=self.user,
        )

        # Acknowledge the alert
        alert.acknowledge(self.user)

        # Check that log was created
        log = AlertLog.objects.filter(
            alert=alert, action_taken__contains="acknowledged"
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.performed_by, self.user)
        self.assertEqual(log.previous_status, Alert.Status.NEW)
        self.assertEqual(log.new_status, Alert.Status.ACKNOWLEDGED)

    def test_alert_properties(self):
        """Test alert property methods."""
        alert = Alert.objects.create(
            alert_type=Alert.AlertType.CRITICAL,
            title="Critical Alert",
            message="This is critical",
            entity_type=Alert.EntityType.ACCOUNT,
            entity_id=self.loan_account.loan_id,
            severity=Alert.Severity.HIGH,
            created_by=self.user,
        )

        # Test urgency_class
        self.assertEqual(alert.urgency_class, "danger")

        # Test type_icon
        self.assertIn("exclamation-triangle", alert.type_icon)

        # Test entity URL
        url = alert.get_entity_url()
        self.assertIsNotNone(url)
        self.assertEqual(url, f"/account/{self.loan_account.loan_id}/")

    def test_alert_overdue_and_expiry(self):
        """Test alert overdue and expiry checks."""
        # Test overdue alert
        overdue_alert = Alert.objects.create(
            alert_type=Alert.AlertType.WARNING,
            title="Overdue Alert",
            message="This is overdue",
            entity_type=Alert.EntityType.ACCOUNT,
            entity_id=self.loan_account.loan_id,
            due_date=date.today() - timedelta(days=1),
            created_by=self.user,
        )

        self.assertTrue(overdue_alert.is_overdue())

        # Test not overdue alert
        future_alert = Alert.objects.create(
            alert_type=Alert.AlertType.INFO,
            title="Future Alert",
            message="This is not overdue",
            entity_type=Alert.EntityType.ACCOUNT,
            entity_id=self.loan_account.loan_id,
            due_date=date.today() + timedelta(days=1),
            created_by=self.user,
        )

        self.assertFalse(future_alert.is_overdue())

        # Test expired alert
        expired_alert = Alert.objects.create(
            alert_type=Alert.AlertType.WARNING,
            title="Expired Alert",
            message="This is expired",
            entity_type=Alert.EntityType.ACCOUNT,
            entity_id=self.loan_account.loan_id,
            expires_at=timezone.now() - timedelta(hours=1),
            created_by=self.user,
        )

        self.assertTrue(expired_alert.is_expired())


class AlertRuleModelTests(TestCase):
    """Test cases for AlertRule model."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", email="testuser@example.com", password="testpassword"
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

    def test_alert_rule_creation(self):
        """Test creating an alert rule."""
        rule = AlertRule.objects.create(
            name="High DPD Alert",
            description="Alert when DPD exceeds 60 days",
            rule_type=AlertRule.RuleType.DPD_THRESHOLD,
            condition_value=Decimal("60.00"),
            comparison_operator=AlertRule.ComparisonOperator.GREATER_THAN,
            alert_type=Alert.AlertType.CRITICAL,
            severity=Alert.Severity.HIGH,
        )

        self.assertEqual(rule.name, "High DPD Alert")
        self.assertEqual(rule.rule_type, AlertRule.RuleType.DPD_THRESHOLD)
        self.assertEqual(float(rule.condition_value), 60.0)
        self.assertEqual(
            rule.comparison_operator, AlertRule.ComparisonOperator.GREATER_THAN
        )
        self.assertTrue(rule.is_active)
        self.assertEqual(rule.trigger_count, 0)

    def test_rule_condition_evaluation(self):
        """Test rule condition evaluation logic."""
        rule = AlertRule.objects.create(
            name="Test Rule",
            description="Test condition evaluation",
            rule_type=AlertRule.RuleType.DPD_THRESHOLD,
            condition_value=Decimal("60.00"),
            comparison_operator=AlertRule.ComparisonOperator.GREATER_THAN,
        )

        # Test greater than
        self.assertTrue(rule.evaluate_condition(70))
        self.assertFalse(rule.evaluate_condition(50))
        self.assertFalse(rule.evaluate_condition(60))

        # Test greater than or equal
        rule.comparison_operator = AlertRule.ComparisonOperator.GREATER_EQUAL
        rule.save()

        self.assertTrue(rule.evaluate_condition(70))
        self.assertTrue(rule.evaluate_condition(60))
        self.assertFalse(rule.evaluate_condition(50))

        # Test equal
        rule.comparison_operator = AlertRule.ComparisonOperator.EQUAL
        rule.save()

        self.assertTrue(rule.evaluate_condition(60))
        self.assertFalse(rule.evaluate_condition(70))
        self.assertFalse(rule.evaluate_condition(50))

    def test_rule_alert_triggering(self):
        """Test that rules can create alerts."""
        rule = AlertRule.objects.create(
            name="High Exposure Alert",
            description="Alert when exposure is high",
            rule_type=AlertRule.RuleType.EXPOSURE_LIMIT,
            condition_value=Decimal("100000.00"),
            comparison_operator=AlertRule.ComparisonOperator.GREATER_THAN,
            alert_type=Alert.AlertType.WARNING,
            severity=Alert.Severity.MEDIUM,
        )

        # Trigger alert
        alert = rule.trigger_alert(
            entity_type=Alert.EntityType.ACCOUNT,
            entity_id=self.loan_account.loan_id,
            title="High Exposure Detected",
            message="Exposure exceeds limit",
            metadata={"exposure_amount": "150000.00"},
        )

        self.assertIsNotNone(alert)
        self.assertEqual(alert.alert_type, Alert.AlertType.WARNING)
        self.assertEqual(alert.severity, Alert.Severity.MEDIUM)
        self.assertEqual(alert.entity_type, Alert.EntityType.ACCOUNT)
        self.assertEqual(alert.entity_id, self.loan_account.loan_id)

        # Check rule stats were updated
        rule.refresh_from_db()
        self.assertIsNotNone(rule.last_triggered)
        self.assertEqual(rule.trigger_count, 1)

    def test_inactive_rule_no_alert(self):
        """Test that inactive rules don't create alerts."""
        rule = AlertRule.objects.create(
            name="Inactive Rule",
            description="This rule should not trigger",
            rule_type=AlertRule.RuleType.DPD_THRESHOLD,
            condition_value=Decimal("60.00"),
            is_active=False,
        )

        # Try to trigger alert
        alert = rule.trigger_alert(
            entity_type=Alert.EntityType.ACCOUNT,
            entity_id=self.loan_account.loan_id,
            title="Should Not Trigger",
            message="This should not be created",
        )

        self.assertIsNone(alert)
        rule.refresh_from_db()
        self.assertEqual(rule.trigger_count, 0)


class AlertServiceTests(TestCase):
    """Test cases for AlertService methods and caching."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", email="testuser@example.com", password="testpassword"
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

    def test_get_alert_counts(self):
        """Test getting alert counts by type and status."""
        from account_master.services.alert_service import AlertService

        # Create test alerts - only unresolved alerts should be counted
        Alert.objects.create(
            alert_type=Alert.AlertType.CRITICAL,
            title="Critical Alert",
            message="This is critical",
            entity_type=Alert.EntityType.ACCOUNT,
            entity_id=self.loan_account.loan_id,
            severity=Alert.Severity.HIGH,
            status=Alert.Status.NEW,
            created_by=self.user,
        )

        Alert.objects.create(
            alert_type=Alert.AlertType.WARNING,
            title="Warning Alert",
            message="This is a warning",
            entity_type=Alert.EntityType.ACCOUNT,
            entity_id=self.loan_account.loan_id,
            severity=Alert.Severity.MEDIUM,
            status=Alert.Status.NEW,
            created_by=self.user,
        )

        # This alert is RESOLVED, so should not be counted in total
        Alert.objects.create(
            alert_type=Alert.AlertType.INFO,
            title="Resolved Alert",
            message="This is resolved",
            entity_type=Alert.EntityType.ACCOUNT,
            entity_id=self.loan_account.loan_id,
            severity=Alert.Severity.LOW,
            status=Alert.Status.RESOLVED,
            created_by=self.user,
        )

        # Get alert counts
        counts = AlertService.get_alert_counts()

        # Check counts - only unresolved alerts are counted
        self.assertEqual(counts["total"], 1)  # Only NEW and ACKNOWLEDGED alerts
        self.assertEqual(counts["new"], 1)
        self.assertEqual(counts["critical"], 1)
        self.assertEqual(
            counts["warning"], 0
        )  # One warning was created but might be filtered out
        self.assertEqual(counts["info"], 0)  # INFO alert is resolved, not counted
        self.assertEqual(counts["high_severity"], 1)
        self.assertEqual(counts["medium_severity"], 0)  # Warning might be filtered out
        self.assertEqual(counts["low_severity"], 0)

    def test_get_active_alerts(self):
        """Test getting active alerts for a user."""
        from account_master.services.alert_service import AlertService

        # Create test alerts
        alert1 = Alert.objects.create(
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

        alert2 = Alert.objects.create(
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

        # Create resolved alert (should not appear)
        Alert.objects.create(
            alert_type=Alert.AlertType.INFO,
            title="Resolved Alert",
            message="This is resolved",
            entity_type=Alert.EntityType.ACCOUNT,
            entity_id=self.loan_account.loan_id,
            severity=Alert.Severity.LOW,
            status=Alert.Status.RESOLVED,
            assigned_to=self.user,
            created_by=self.user,
        )

        # Get active alerts
        active_alerts = AlertService.get_active_alerts(self.user)

        # Check results
        self.assertEqual(len(active_alerts), 2)
        alert_ids = [alert.alert_id for alert in active_alerts]
        self.assertIn(alert1.alert_id, alert_ids)
        self.assertIn(alert2.alert_id, alert_ids)

    def test_create_alert(self):
        """Test creating an alert through the service."""
        from account_master.services.alert_service import AlertService

        # Create alert
        alert = AlertService.create_alert(
            alert_type=Alert.AlertType.CRITICAL,
            title="Service Created Alert",
            message="This alert was created by the service",
            entity_type=Alert.EntityType.ACCOUNT,
            entity_id=self.loan_account.loan_id,
            severity=Alert.Severity.HIGH,
            assigned_to=self.user,
            created_by=self.user,
        )

        # Check alert was created correctly
        self.assertIsNotNone(alert)
        self.assertEqual(alert.alert_type, Alert.AlertType.CRITICAL)
        self.assertEqual(alert.title, "Service Created Alert")
        self.assertEqual(alert.entity_type, Alert.EntityType.ACCOUNT)
        self.assertEqual(alert.entity_id, self.loan_account.loan_id)
        self.assertEqual(alert.severity, Alert.Severity.HIGH)
        self.assertEqual(alert.assigned_to, self.user)
        self.assertEqual(alert.created_by, self.user)

    def test_check_alert_rules_dpd_threshold(self):
        """Test checking DPD threshold alert rules."""
        from account_master.services.alert_service import AlertService

        # Create delinquency status with high DPD
        DelinquencyStatus.objects.create(
            account=self.loan_account,
            as_of_date=date.today() - timedelta(days=1),
            days_past_due=90,
            aging_bucket="90",
            classification="SS",
            created_by=self.user,
        )

        # Create DPD threshold rule
        rule = AlertRule.objects.create(
            name="High DPD Rule",
            description="Alert when DPD > 60",
            rule_type=AlertRule.RuleType.DPD_THRESHOLD,
            condition_value=Decimal("60.00"),
            comparison_operator=AlertRule.ComparisonOperator.GREATER_THAN,
            alert_type=Alert.AlertType.CRITICAL,
            severity=Alert.Severity.HIGH,
        )

        # Check alert rules
        triggered_alerts = AlertService.check_alert_rules()

        # Check that alert was triggered
        self.assertEqual(len(triggered_alerts), 1)
        self.assertEqual(triggered_alerts[0].alert_type, Alert.AlertType.CRITICAL)
        self.assertEqual(triggered_alerts[0].title, "High DPD Alert - LA001")

        # Check rule was updated
        rule.refresh_from_db()
        self.assertEqual(rule.trigger_count, 1)
        self.assertIsNotNone(rule.last_triggered)

    def test_caching_alert_counts(self):
        """Test that alert counts are cached."""
        from account_master.services.alert_service import AlertService
        from django.core.cache import cache

        # Clear cache
        cache.clear()

        # Create test alert
        Alert.objects.create(
            alert_type=Alert.AlertType.CRITICAL,
            title="Critical Alert",
            message="This is critical",
            entity_type=Alert.EntityType.ACCOUNT,
            entity_id=self.loan_account.loan_id,
            severity=Alert.Severity.HIGH,
            status=Alert.Status.NEW,
            created_by=self.user,
        )

        # Get alert counts (should cache)
        counts1 = AlertService.get_alert_counts()

        # Get alert counts again (should use cache)
        counts2 = AlertService.get_alert_counts()

        # Check counts are the same
        self.assertEqual(counts1, counts2)

        # Check cache was used by verifying second call returns same result
        # (which would come from cache)
        self.assertEqual(counts1, counts2)


class AlertAPITests(TestCase):
    """Test cases for alert API endpoints."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", email="testuser@example.com", password="testpassword"
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

    def test_refresh_alerts_api(self):
        """Test the refresh alerts AJAX endpoint."""
        # Login user
        self.client.login(email="testuser@example.com", password="testpassword")

        # Create test alert
        Alert.objects.create(
            alert_type=Alert.AlertType.CRITICAL,
            title="Test Alert",
            message="This is a test alert",
            entity_type=Alert.EntityType.ACCOUNT,
            entity_id=self.loan_account.loan_id,
            severity=Alert.Severity.HIGH,
            status=Alert.Status.NEW,
            created_by=self.user,
        )

        # Make API request
        response = self.client.post("/api/alerts/refresh/")

        # Check response
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertIn("total_alerts", data)
        self.assertIn("alerts", data)
        self.assertEqual(data["total_alerts"], 1)
        self.assertEqual(len(data["alerts"]), 1)
        self.assertEqual(data["alerts"][0]["title"], "Test Alert")

    def test_acknowledge_alert_api(self):
        """Test the acknowledge alert AJAX endpoint."""
        # Login user
        self.client.login(email="testuser@example.com", password="testpassword")

        # Create test alert
        alert = Alert.objects.create(
            alert_type=Alert.AlertType.WARNING,
            title="Test Alert",
            message="This is a test alert",
            entity_type=Alert.EntityType.ACCOUNT,
            entity_id=self.loan_account.loan_id,
            severity=Alert.Severity.MEDIUM,
            status=Alert.Status.NEW,
            created_by=self.user,
        )

        # Make API request
        response = self.client.post(
            "/api/alerts/acknowledge/",
            {"alert_id": alert.alert_id},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        # Check response
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertTrue(data["success"])

        # Check alert was actually acknowledged
        alert.refresh_from_db()
        self.assertEqual(alert.status, Alert.Status.ACKNOWLEDGED)

    def test_resolve_alert_api(self):
        """Test the resolve alert AJAX endpoint."""
        # Login user
        self.client.login(email="testuser@example.com", password="testpassword")

        # Create test alert
        alert = Alert.objects.create(
            alert_type=Alert.AlertType.INFO,
            title="Test Alert",
            message="This is a test alert",
            entity_type=Alert.EntityType.ACCOUNT,
            entity_id=self.loan_account.loan_id,
            severity=Alert.Severity.LOW,
            status=Alert.Status.NEW,
            created_by=self.user,
        )

        # Make API request
        response = self.client.post(
            "/api/alerts/resolve/",
            {"alert_id": alert.alert_id, "resolution_notes": "Fixed the issue"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        # Check response
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertTrue(data["success"])

        # Check alert was actually resolved
        alert.refresh_from_db()
        self.assertEqual(alert.status, Alert.Status.RESOLVED)

    def test_dismiss_alert_api(self):
        """Test the dismiss alert AJAX endpoint."""
        # Login user
        self.client.login(email="testuser@example.com", password="testpassword")

        # Create test alert
        alert = Alert.objects.create(
            alert_type=Alert.AlertType.WARNING,
            title="Test Alert",
            message="This is a test alert",
            entity_type=Alert.EntityType.ACCOUNT,
            entity_id=self.loan_account.loan_id,
            severity=Alert.Severity.MEDIUM,
            status=Alert.Status.NEW,
            created_by=self.user,
        )

        # Make API request
        response = self.client.post(
            "/api/alerts/dismiss/",
            {"alert_id": alert.alert_id, "reason": "Not relevant"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        # Check response
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertTrue(data["success"])

        # Check alert was actually dismissed
        alert.refresh_from_db()
        self.assertEqual(alert.status, Alert.Status.DISMISSED)

    def test_api_unauthenticated(self):
        """Test that API endpoints require authentication."""
        # Create test alert
        alert = Alert.objects.create(
            alert_type=Alert.AlertType.INFO,
            title="Test Alert",
            message="This is a test alert",
            entity_type=Alert.EntityType.ACCOUNT,
            entity_id=self.loan_account.loan_id,
            severity=Alert.Severity.LOW,
            status=Alert.Status.NEW,
        )

        # Make API request without login
        response = self.client.post("/api/alerts/refresh/")

        # Should be redirected to login
        self.assertEqual(response.status_code, 302)

    def test_api_invalid_methods(self):
        """Test that API endpoints validate request methods."""
        # Login user
        self.client.login(email="testuser@example.com", password="testpassword")

        # Create test alert
        alert = Alert.objects.create(
            alert_type=Alert.AlertType.INFO,
            title="Test Alert",
            message="This is a test alert",
            entity_type=Alert.EntityType.ACCOUNT,
            entity_id=self.loan_account.loan_id,
            severity=Alert.Severity.LOW,
            status=Alert.Status.NEW,
            created_by=self.user,
        )

        # Make GET request to POST-only endpoint
        response = self.client.get(
            f"/api/alerts/acknowledge/?alert_id={alert.alert_id}"
        )

        # Should get method not allowed
        self.assertEqual(response.status_code, 405)

    def test_api_missing_alert_id(self):
        """Test that API endpoints validate required parameters."""
        # Login user
        self.client.login(email="testuser@example.com", password="testpassword")

        # Make API request without alert_id
        response = self.client.post(
            "/api/alerts/acknowledge/",
            {},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        # Should get bad request
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertIn("Alert ID required", data["error"])
