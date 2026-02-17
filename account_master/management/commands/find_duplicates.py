from django.core.management.base import BaseCommand
from django.db.models import Count
from account_master.models import Exposure, DelinquencyStatus

class Command(BaseCommand):
    help = 'Finds duplicate Exposure and DelinquencyStatus records based on account and as_of_date.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('--- Finding duplicate Exposure records ---'))
        duplicate_exposures = Exposure.objects.values("account_id", "as_of_date").annotate(c=Count("exposure_id")).filter(c__gt=1)[:20]

        if duplicate_exposures:
            self.stdout.write(self.style.WARNING('Found duplicate Exposure records:'))
            for item in duplicate_exposures:
                self.stdout.write(
                    f"  Account ID: {item['account_id']}, Date: {item['as_of_date']}, Count: {item['c']}"
                )
        else:
            self.stdout.write(self.style.SUCCESS('No duplicate Exposure records found.'))

        self.stdout.write(self.style.SUCCESS('\n--- Finding duplicate DelinquencyStatus records ---'))
        duplicate_delinquency = DelinquencyStatus.objects.values("account_id", "as_of_date").annotate(c=Count("delinquency_id")).filter(c__gt=1)[:20]

        if duplicate_delinquency:
            self.stdout.write(self.style.WARNING('Found duplicate DelinquencyStatus records:'))
            for item in duplicate_delinquency:
                self.stdout.write(
                    f"  Account ID: {item['account_id']}, Date: {item['as_of_date']}, Count: {item['c']}"
                )
        else:
            self.stdout.write(self.style.SUCCESS('No duplicate DelinquencyStatus records found.'))
