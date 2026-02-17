from django.core.management.base import BaseCommand
from account_master.models import LoanAccount, RemedialStrategy
from datetime import date, timedelta
import random

class Command(BaseCommand):
    help = 'Loads dummy remedial strategy data for existing accounts.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Loading dummy remedial strategy data...'))
        accounts = LoanAccount.objects.all()

        if not accounts.exists():
            self.stdout.write(self.style.ERROR('No accounts found to create remedial strategies for.'))
            return

        for account in accounts:
            # Clear existing strategies for this account to avoid duplicates on re-run
            RemedialStrategy.objects.filter(account=account).delete()

            # Create 1-3 dummy strategies for each account
            num_strategies = random.randint(1, 3)
            base_date = date.today() - timedelta(days=random.randint(30, 180)) # Strategies started in the past

            for i in range(num_strategies):
                strategy_start_date = base_date + timedelta(days=random.randint(0, 60))
                strategy_type = random.choice([choice[0] for choice in RemedialStrategy.STRATEGY_TYPE_CHOICES])
                
                if i == 0:
                    # The first strategy created for an account is active
                    current_strategy_status = RemedialStrategy.StrategyStatus.ACTIVE
                else:
                    # Subsequent strategies can have varied statuses
                    current_strategy_status = random.choice([
                        RemedialStrategy.StrategyStatus.COMPLETED, 
                        RemedialStrategy.StrategyStatus.CANCELLED
                    ])
                
                strategy_outcome = f'Outcome for {strategy_type} strategy {i+1}.'

                RemedialStrategy.objects.create(
                    account=account,
                    strategy_type=strategy_type,
                    strategy_start_date=strategy_start_date,
                    strategy_status=current_strategy_status,
                    strategy_outcome=strategy_outcome,
                )
                self.stdout.write(f'  Created {strategy_type} strategy for {account.loan_id} starting {strategy_start_date}')

        self.stdout.write(self.style.SUCCESS('Dummy remedial strategy data loaded successfully!'))
