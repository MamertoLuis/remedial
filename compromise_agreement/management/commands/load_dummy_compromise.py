from django.core.management.base import BaseCommand
from account_master.models import LoanAccount, Borrower, RemedialStrategy
from compromise_agreement.models import CompromiseAgreement, CompromiseInstallment
from django.contrib.auth import get_user_model
from datetime import date, timedelta
import random
from decimal import Decimal

User = get_user_model()

class Command(BaseCommand):
    help = 'Loads dummy compromise agreement data for existing accounts.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Loading dummy compromise agreement data...'))

        accounts = LoanAccount.objects.all()
        if not accounts.exists():
            self.stdout.write(self.style.ERROR('No accounts found. Please load dummy loan accounts first.'))
            return

        # Get or create a dummy user for created_by/updated_by fields
        user, created = User.objects.get_or_create(username='dummy_user', defaults={'email': 'dummy@example.com'})
        if created:
            user.set_password('dummy_password')
            user.save()
            self.stdout.write(f'Created dummy user: {user.username}')

        # Clear existing compromise agreements to avoid duplicates on re-run
        CompromiseAgreement.objects.all().delete()
        CompromiseInstallment.objects.all().delete()

        for account in accounts:
            if random.random() < 0.7:  # 70% chance to create a compromise agreement for an account
                # Ensure only one active 'Compromise' RemedialStrategy exists for this account
                # Set existing active 'Compromise' strategies to CANCELLED before creating a new one
                RemedialStrategy.objects.filter(
                    account=account,
                    strategy_type='Compromise',
                    strategy_status=RemedialStrategy.StrategyStatus.ACTIVE
                ).update(strategy_status=RemedialStrategy.StrategyStatus.CANCELLED)

                # Get or create a RemedialStrategy for the current account
                # This ensures a strategy exists before creating a CompromiseAgreement
                remedial_strategy, strategy_created = RemedialStrategy.objects.get_or_create(
                    account=account,
                    strategy_type='Compromise', # Use a fixed strategy type for dummy data
                    defaults={
                        'strategy_start_date': date.today(),
                        'strategy_status': RemedialStrategy.StrategyStatus.ACTIVE,
                        'created_by': user,
                        'updated_by': user,
                    }
                )
                if strategy_created:
                    self.stdout.write(f'  Created RemedialStrategy for {account.loan_id}: {remedial_strategy.strategy_type}')

                original_exposure = Decimal(random.uniform(100000.00, 1000000.00))
                approved_amount = original_exposure * Decimal(random.uniform(0.5, 0.9))
                
                approval_level = random.choice([
                    CompromiseAgreement.ApprovalLevel.AO,
                    CompromiseAgreement.ApprovalLevel.MANAGER,
                    CompromiseAgreement.ApprovalLevel.BOARD
                ])
                approval_date = date.today() - timedelta(days=random.randint(30, 365))
                installment_flag = random.choice([True, False])
                
                num_installments = None
                payment_frequency = None
                first_payment_date = None

                if installment_flag:
                    num_installments = random.randint(3, 12)
                    payment_frequency = random.choice([
                        CompromiseAgreement.PaymentFrequency.MONTHLY
                    ])
                    first_payment_date = approval_date + timedelta(days=30) # First payment 30 days after approval
                status = random.choice([
                    CompromiseAgreement.CompromiseStatus.ACTIVE,
                    CompromiseAgreement.CompromiseStatus.COMPLETED,
                    CompromiseAgreement.CompromiseStatus.RESCINDED
                ])

                agreement = CompromiseAgreement.objects.create(
                    strategy=remedial_strategy,
                    account=account,
                    original_total_exposure=round(original_exposure, 2),
                    approved_compromise_amount=round(approved_amount, 2),
                    approval_level=approval_level,
                    approval_date=approval_date,
                    installment_flag=installment_flag,
                    rescission_clause_flag=True,
                    status=status,
                    number_of_installments=num_installments,
                    payment_frequency=payment_frequency,
                    first_payment_date=first_payment_date,
                    created_by=user,
                    updated_by=user,
                )
                self.stdout.write(f'  Created compromise agreement for {account.loan_id} (ID: {agreement.compromise_id})')

                if installment_flag:
                    num_installments = random.randint(3, 12)
                    remaining_amount = agreement.approved_compromise_amount
                    for i in range(1, num_installments + 1):
                        due_date = agreement.approval_date + timedelta(days=i * 30)
                        if i == num_installments:
                            amount_due = remaining_amount
                        else:
                            amount_due = Decimal(str(random.uniform(float(remaining_amount / (num_installments - i + 1)) * 0.8, float(remaining_amount / (num_installments - i + 1)) * 1.2)))
                            amount_due = round(min(amount_due, remaining_amount), 2)
                        
                        remaining_amount -= amount_due

                        # Simulate some paid installments
                        if random.random() < 0.7 and status != CompromiseAgreement.CompromiseStatus.RESCINDED: # 70% chance of being paid if not rescinded
                            payment_date = due_date - timedelta(days=random.randint(0, 5))
                            amount_paid = amount_due
                            installment_status = CompromiseInstallment.InstallmentStatus.PAID
                        else:
                            payment_date = None
                            amount_paid = Decimal('0.00')
                            installment_status = CompromiseInstallment.InstallmentStatus.UNPAID

                        CompromiseInstallment.objects.create(
                            compromise_agreement=agreement,
                            installment_number=i,
                            due_date=due_date,
                            amount_due=amount_due,
                            amount_paid=amount_paid,
                            payment_date=payment_date,
                            status=installment_status,
                        )
                        self.stdout.write(f'    Created installment {i} for agreement {agreement.compromise_id}')

        self.stdout.write(self.style.SUCCESS('Dummy compromise agreement data loaded successfully!'))
