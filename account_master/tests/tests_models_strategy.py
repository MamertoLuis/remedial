from django.test import TestCase
from django.utils import timezone
from django.db.utils import IntegrityError
import datetime
from decimal import Decimal

from account_master.models import (
    Borrower,
    LoanAccount,
    RemedialStrategy,
    CollectionActivityLog,
    StrategyAction,
    StrategyActionCatalogEntry,
    Alert,
    AlertLog,
)
from compromise_agreement.models import CompromiseAgreement


class RemedialStrategyModelTest(TestCase):
    def setUp(self):
        self.borrower = Borrower.objects.create(
            borrower_id="B001",
            full_name="John Doe",
            primary_address="123 Main St",
            mobile="1234567890",
        )
        self.account = LoanAccount.objects.create(
            loan_id="L001",
            borrower=self.borrower,
            booking_date=datetime.date(2023, 1, 1),
            maturity_date=datetime.date(2024, 1, 1),
            original_principal=Decimal("10000.00"),
            interest_rate=Decimal("5.00"),
            loan_type="Personal",
            status="PAST_DUE",
        )

    def test_remedial_strategy_str(self):
        strategy = RemedialStrategy.objects.create(
            account=self.account,
            strategy_type="Intensive Collection",
            strategy_start_date=datetime.date(2023, 6, 1),
            strategy_status=RemedialStrategy.StrategyStatus.ACTIVE,
        )
        self.assertEqual(str(strategy), "Intensive Collection for L001")

    def test_save_deactivates_other_active_strategies(self):
        strategy1 = RemedialStrategy.objects.create(
            account=self.account,
            strategy_type="Intensive Collection",
            strategy_start_date=datetime.date(2023, 6, 1),
            strategy_status=RemedialStrategy.StrategyStatus.ACTIVE,
        )

        # Create a new active strategy
        strategy2 = RemedialStrategy.objects.create(
            account=self.account,
            strategy_type="Restructuring",
            strategy_start_date=datetime.date(2023, 7, 1),
            strategy_status=RemedialStrategy.StrategyStatus.ACTIVE,
        )

        # Refresh strategy1 from db
        strategy1.refresh_from_db()

        # strategy1 should be cancelled
        self.assertEqual(
            strategy1.strategy_status, RemedialStrategy.StrategyStatus.CANCELLED
        )
        self.assertEqual(
            strategy2.strategy_status, RemedialStrategy.StrategyStatus.ACTIVE
        )

    def test_save_supersedes_compromise_agreements(self):
        strategy1 = RemedialStrategy.objects.create(
            account=self.account,
            strategy_type="Intensive Collection",
            strategy_start_date=datetime.date(2023, 6, 1),
            strategy_status=RemedialStrategy.StrategyStatus.ACTIVE,
        )

        # Create an active compromise agreement
        agreement = CompromiseAgreement.objects.create(
            strategy=strategy1,
            account=self.account,
            original_total_exposure=Decimal("10000.00"),
            approved_compromise_amount=Decimal("9000.00"),
            approval_level="MANAGER",
            approval_date=datetime.date(2023, 6, 15),
            status="ACTIVE",
        )

        # Create a new active strategy
        strategy2 = RemedialStrategy.objects.create(
            account=self.account,
            strategy_type="Restructuring",
            strategy_start_date=datetime.date(2023, 7, 1),
            strategy_status=RemedialStrategy.StrategyStatus.ACTIVE,
        )

        # Refresh agreement from db
        agreement.refresh_from_db()

        # agreement should be superseded
        self.assertEqual(agreement.status, "SUPERSEDED")

    def test_save_does_not_supersede_own_compromise_agreement(self):
        """An ACTIVE strategy must not supersede its own compromise agreement."""
        strategy = RemedialStrategy.objects.create(
            account=self.account,
            strategy_type="Intensive Collection",
            strategy_start_date=datetime.date(2023, 6, 1),
            strategy_status=RemedialStrategy.StrategyStatus.ACTIVE,
        )
        agreement = CompromiseAgreement.objects.create(
            strategy=strategy,
            account=self.account,
            original_total_exposure=Decimal("10000.00"),
            approved_compromise_amount=Decimal("9000.00"),
            approval_level="MANAGER",
            approval_date=datetime.date(2023, 6, 15),
            status="ACTIVE",
        )
        # Re-saving the same ACTIVE strategy must leave its own agreement alone.
        strategy.save()
        agreement.refresh_from_db()
        self.assertEqual(agreement.status, "ACTIVE")

    def test_save_noop_without_active_compromise_agreement(self):
        """Saving an ACTIVE strategy with no active agreement changes nothing."""
        RemedialStrategy.objects.create(
            account=self.account,
            strategy_type="Restructuring",
            strategy_start_date=datetime.date(2023, 7, 1),
            strategy_status=RemedialStrategy.StrategyStatus.ACTIVE,
        )
        self.assertEqual(CompromiseAgreement.objects.count(), 0)

    def test_unique_active_strategy_per_account_constraint(self):
        # The save method automatically cancels other active strategies,
        # so we can't easily trigger the constraint by just calling create().
        # We need to use bulk_create or update to bypass the save method.
        strategy1 = RemedialStrategy.objects.create(
            account=self.account,
            strategy_type="Intensive Collection",
            strategy_start_date=datetime.date(2023, 6, 1),
            strategy_status=RemedialStrategy.StrategyStatus.ACTIVE,
        )

        strategy2 = RemedialStrategy.objects.create(
            account=self.account,
            strategy_type="Intensive Collection",
            strategy_start_date=datetime.date(2023, 7, 1),
            strategy_status=RemedialStrategy.StrategyStatus.CANCELLED,
        )

        # Attempt to update strategy2 to ACTIVE, which should violate the constraint
        with self.assertRaises(IntegrityError):
            RemedialStrategy.objects.filter(pk=strategy2.pk).update(
                strategy_status=RemedialStrategy.StrategyStatus.ACTIVE
            )


class AlertLogModelTest(TestCase):
    def setUp(self):
        self.alert = Alert.objects.create(
            alert_type=Alert.AlertType.INFO,
            title="Test Alert",
            message="This is a test alert.",
            entity_type=Alert.EntityType.SYSTEM,
            severity=Alert.Severity.LOW,
            status=Alert.Status.NEW,
        )

    def test_alert_log_str(self):
        log = AlertLog.objects.create(
            alert=self.alert,
            action_taken="Alert acknowledged",
            previous_status=Alert.Status.NEW,
            new_status=Alert.Status.ACKNOWLEDGED,
        )
        self.assertEqual(str(log), "Test Alert - Alert acknowledged")

    def test_alert_log_relationship(self):
        log = AlertLog.objects.create(
            alert=self.alert,
            action_taken="Alert resolved",
            previous_status=Alert.Status.NEW,
            new_status=Alert.Status.RESOLVED,
        )
        self.assertEqual(log.alert, self.alert)
        self.assertIn(log, self.alert.logs.all())


class CollectionActivityEvidenceModelTest(TestCase):
    """The evidence link between a collection activity and a strategy action."""

    def setUp(self):
        self.borrower = Borrower.objects.create(
            borrower_id="B-EV",
            full_name="John Doe",
            primary_address="123 Main St",
            mobile="1234567890",
        )
        self.account = LoanAccount.objects.create(
            loan_id="L-EV",
            borrower=self.borrower,
            booking_date=datetime.date(2023, 1, 1),
            maturity_date=datetime.date(2024, 1, 1),
            original_principal=Decimal("10000.00"),
            interest_rate=Decimal("5.00"),
            loan_type="Personal",
            status="NPL",
        )
        self.strategy = RemedialStrategy.objects.create(
            account=self.account,
            strategy_type="Intensive Collection",
            strategy_start_date=datetime.date(2023, 6, 1),
            strategy_status=RemedialStrategy.StrategyStatus.ACTIVE,
        )
        self.entry = StrategyActionCatalogEntry.objects.create(
            strategy_type="Intensive Collection",
            code="IC-EVIDENCE",
            name="Call",
            ordering=10,
            requires_approval=False,
        )
        self.action = StrategyAction.objects.create(
            catalog_entry=self.entry,
            strategy=self.strategy,
            status=StrategyAction.ActionStatus.SELECTED,
        )

    def test_activity_can_carry_an_action_link(self):
        activity = CollectionActivityLog.objects.create(
            account=self.account,
            activity_date=datetime.date(2023, 6, 5),
            activity_type="Call",
            remarks="Called borrower",
            action=self.action,
        )
        self.assertEqual(activity.action, self.action)
        self.assertIn(activity, self.action.evidence_activities.all())

    def test_deleting_the_action_nulls_the_link_and_keeps_the_diary_row(self):
        activity = CollectionActivityLog.objects.create(
            account=self.account,
            activity_date=datetime.date(2023, 6, 5),
            activity_type="Call",
            remarks="Called borrower",
            action=self.action,
        )
        self.action.delete()
        activity.refresh_from_db()
        self.assertIsNone(activity.action)
        self.assertEqual(activity.remarks, "Called borrower")
