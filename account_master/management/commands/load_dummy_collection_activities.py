from django.core.management.base import BaseCommand
from account_master.models import LoanAccount, CollectionActivityLog
from datetime import date, timedelta
import random

class Command(BaseCommand):
    help = 'Loads dummy collection activity data for existing accounts.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Loading dummy collection activity data...'))
        accounts = LoanAccount.objects.all()

        if not accounts.exists():
            self.stdout.write(self.style.ERROR('No accounts found to create collection activities for.'))
            return

        for account in accounts:
            # Clear existing collection activities for this account to avoid duplicates on re-run
            CollectionActivityLog.objects.filter(account=account).delete()

            # Create 5-15 dummy collection activities for each account
            num_activities = random.randint(5, 15)
            base_date = date.today() - timedelta(days=90) # Start activities from 90 days ago

            for i in range(num_activities):
                activity_date = base_date + timedelta(days=random.randint(1, 90))
                activity_type = random.choice([choice[0] for choice in CollectionActivityLog.ACTIVITY_TYPE_CHOICES])
                staff_assigned = random.choice(['Collection Officer 1', 'Collection Officer 2', 'Collection Officer 3'])
                remarks = f'Follow-up activity {i+1} for account {account.loan_id}. Type: {activity_type}.'

                promise_to_pay_amount = None
                promise_to_pay_date = None
                next_action_date = None

                if activity_type == 'Negotiation' and random.random() > 0.5:
                    promise_to_pay_amount = round(random.uniform(1000, 10000), 2)
                    promise_to_pay_date = activity_date + timedelta(days=random.randint(7, 30))

                if random.random() > 0.3: # Most activities should have a next action
                    next_action_date = activity_date + timedelta(days=random.randint(1, 14))

                CollectionActivityLog.objects.create(
                    account=account,
                    activity_date=activity_date,
                    activity_type=activity_type,
                    remarks=remarks,
                    promise_to_pay_amount=promise_to_pay_amount,
                    promise_to_pay_date=promise_to_pay_date,
                    staff_assigned=staff_assigned,
                    next_action_date=next_action_date,
                )
                self.stdout.write(f'  Created collection activity for {account.loan_id} on {activity_date}')

        self.stdout.write(self.style.SUCCESS('Dummy collection activity data loaded successfully!'))
