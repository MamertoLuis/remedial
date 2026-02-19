import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from account_master.models import Borrower
from account_master.services import upsert_loan_account


class Command(BaseCommand):
    help = "Imports loan account data from a CSV file."

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_file", type=str, help="The path to the CSV file to import."
        )

    def handle(self, *args, **options):
        csv_file_path = options["csv_file"]
        self.stdout.write(
            self.style.SUCCESS(
                f"Attempting to import loan account data from {csv_file_path}..."
            )
        )

        try:
            with open(csv_file_path, "r", encoding="utf-8") as file:
                reader = csv.DictReader(file)
                if not reader.fieldnames:
                    raise CommandError("CSV file is empty or has no headers.")

                required_headers = [
                    "loan_id",
                    "borrower_id",
                    "booking_date",
                    "maturity_date",
                    "original_principal",
                    "interest_rate",
                    "loan_type",
                    "account_officer_id",
                    "status",
                ]

                if not all(header in reader.fieldnames for header in required_headers):
                    missing_headers = [
                        h for h in required_headers if h not in reader.fieldnames
                    ]
                    raise CommandError(
                        f"Missing required CSV headers: {', '.join(missing_headers)}. "
                        f"Required: {', '.join(required_headers)}. Found: {', '.join(reader.fieldnames)}"
                    )

                imported_count = 0
                updated_count = 0
                errors = []

                for row_num, row in enumerate(reader, 1):
                    try:
                        with transaction.atomic():
                            loan_id = row["loan_id"]
                            borrower_id = row["borrower_id"]

                            try:
                                borrower = Borrower.objects.get(borrower_id=borrower_id)
                            except Borrower.DoesNotExist:
                                raise ValueError(
                                    f"Borrower with borrower_id '{borrower_id}' does not exist."
                                )

                            booking_date = datetime.strptime(
                                row["booking_date"], "%Y-%m-%d"
                            ).date()
                            maturity_date = datetime.strptime(
                                row["maturity_date"], "%Y-%m-%d"
                            ).date()
                            original_principal = Decimal(row["original_principal"])
                            interest_rate = Decimal(row["interest_rate"])

_, created = upsert_loan_account(
                                loan_id=loan_id,
                                defaults={
                                    'borrower': borrower,
                                    'booking_date': booking_date,
                                    'maturity_date': maturity_date,
                                    'original_principal': original_principal,
                                    'interest_rate': interest_rate,
                                    'loan_type': row['loan_type'],
                                    'account_officer_id': row['account_officer_id'],
                                    'status': row.get('status', 'PERFORMING'),
                                }
                            )

                            if created:
                                imported_count += 1
                            else:
                                updated_count += 1

                    except (ValueError, InvalidOperation) as e:
                        errors.append(f"Row {row_num}: Data conversion error - {e}")
                    except KeyError as e:
                        errors.append(
                            f"Row {row_num}: Missing data for expected field - {e}"
                        )
                    except Exception as e:
                        errors.append(
                            f"Row {row_num}: An unexpected error occurred - {e}"
                        )

                if errors:
                    for error in errors:
                        self.stderr.write(self.style.ERROR(error))
                    raise CommandError(
                        f"Finished with {len(errors)} errors. See above for details."
                    )
                else:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Successfully imported {imported_count} new loan accounts and updated {updated_count} existing accounts."
                        )
                    )

        except FileNotFoundError:
            raise CommandError(f'File "{csv_file_path}" not found.')
        except Exception as e:
            raise CommandError(f"An error occurred during file processing: {e}")
