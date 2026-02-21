from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from account_master.models import LoanAccount
from account_master.services import update_ecl_provision_for_account


class Command(BaseCommand):
    help = "Update ECL provisions for loan accounts based on their delinquency status."

    def add_arguments(self, parser):
        parser.add_argument(
            "--loan-id",
            type=str,
            help="Specific loan ID to update (if not provided, updates all loans).",
        )
        parser.add_argument(
            "--as-of-date",
            type=str,
            help="Specific date to update (YYYY-MM-DD format, if not provided updates all dates).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be updated without actually updating.",
        )

    def handle(self, *args, **options):
        loan_id = options.get("loan_id")
        as_of_date_str = options.get("as_of_date")
        dry_run = options["dry_run"]

        self.stdout.write(self.style.SUCCESS("Starting ECL provision update..."))

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE: No data will actually be updated.")
            )

        try:
            # Parse date if provided
            as_of_date = None
            if as_of_date_str:
                from datetime import datetime

                as_of_date = datetime.strptime(as_of_date_str, "%Y-%m-%d").date()

            # Get accounts to process
            if loan_id:
                try:
                    accounts = [LoanAccount.objects.get(loan_id=loan_id)]
                except LoanAccount.DoesNotExist:
                    raise CommandError(f"Loan account with ID '{loan_id}' not found.")
            else:
                accounts = LoanAccount.objects.all()

            total_accounts = accounts.count()
            processed_count = 0
            error_count = 0

            self.stdout.write(f"Found {total_accounts} loan accounts to process.")

            for account in accounts:
                try:
                    if dry_run:
                        self.stdout.write(
                            f"Would update ECL provisions for loan: {account.loan_id}"
                        )
                        processed_count += 1
                    else:
                        update_ecl_provision_for_account(account, as_of_date)
                        processed_count += 1
                        self.stdout.write(
                            f"Updated ECL provisions for loan: {account.loan_id}"
                        )

                except Exception as e:
                    error_count += 1
                    self.stderr.write(
                        self.style.ERROR(
                            f"Error updating ECL provisions for loan {account.loan_id}: {e}"
                        )
                    )

            if dry_run:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"DRY RUN COMPLETE: Would process {processed_count} loan accounts."
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"ECL provision update completed: {processed_count} accounts processed, {error_count} errors."
                    )
                )

        except Exception as e:
            raise CommandError(f"Error during ECL provision update: {e}")
