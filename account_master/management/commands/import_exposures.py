import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from account_master.models import LoanAccount
from account_master.services import upsert_exposure


class Command(BaseCommand):
    help = "Imports exposure data from a CSV file."

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_file", type=str, help="The path to the CSV file to import."
        )

    def handle(self, *args, **options):
        csv_file_path = options["csv_file"]
        self.stdout.write(
            self.style.SUCCESS(
                f"Attempting to import exposure data from {csv_file_path}..."
            )
        )

        try:
            with open(csv_file_path, "r", encoding="utf-8") as file:
                reader = csv.DictReader(file)
                if not reader.fieldnames:
                    raise CommandError("CSV file is empty or has no headers.")

                required_headers = [
                    "loan_id",
                    "as_of_date",
                    "principal_outstanding",
                    "accrued_interest",
                    "accrued_penalty",
                ]

                # Check for all required headers
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
                            as_of_date_str = row["as_of_date"]

                            loan_account = LoanAccount.objects.get(loan_id=loan_id)

                            try:
                                as_of_date = datetime.strptime(
                                    as_of_date_str, "%Y-%m-%d"
                                ).date()
                            except ValueError:
                                raise ValueError(
                                    f"Invalid date format for 'as_of_date': {as_of_date_str}. Expected YYYY-MM-DD."
                                )

                            # Parse decimal fields
                            principal_outstanding = Decimal(
                                row.get("principal_outstanding", "0.00")
                            )
                            accrued_interest = Decimal(
                                row.get("accrued_interest", "0.00")
                            )
                            accrued_penalty = Decimal(
                                row.get("accrued_penalty", "0.00")
                            )

                            _, created = upsert_exposure(
                                account=loan_account,
                                as_of_date=as_of_date,
                                defaults={
                                    "principal_outstanding": principal_outstanding,
                                    "accrued_interest": accrued_interest,
                                    "accrued_penalty": accrued_penalty,
                                },
                            )
                            accrued_interest = Decimal(
                                row.get("accrued_interest", "0.00")
                            )
                            accrued_penalty = Decimal(
                                row.get("accrued_penalty", "0.00")
                            )
                            legal_fees = Decimal(row.get("legal_fees", "0.00"))
                            other_charges = Decimal(row.get("other_charges", "0.00"))
                            provision_level = Decimal(
                                row.get("provision_level", "0.00")
                            )

                            _, created = upsert_exposure(
                                account=loan_account,
                                as_of_date=as_of_date,
                                defaults={
                                    "principal_outstanding": principal_outstanding,
                                    "accrued_interest": accrued_interest,
                                    "accrued_penalty": accrued_penalty,
                                    "legal_fees": legal_fees,
                                    "other_charges": other_charges,
                                    "provision_level": provision_level,
                                },
                            )

                            if created:
                                imported_count += 1
                            else:
                                updated_count += 1

                    except LoanAccount.DoesNotExist:
                        errors.append(
                            f'Row {row_num}: LoanAccount with loan_id "{loan_id}" does not exist.'
                        )
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
                            f"Successfully imported {imported_count} new exposure records and updated {updated_count} existing records."
                        )
                    )

        except FileNotFoundError:
            raise CommandError(f'File "{csv_file_path}" not found.')
        except Exception as e:
            raise CommandError(f"An error occurred during file processing: {e}")
