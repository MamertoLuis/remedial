import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from account_master.models import Borrower
from account_master.services import upsert_loan_account


class Command(BaseCommand):
    help = "Debug version: Imports loan account data from a CSV file with borrower_id validation."

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_file", type=str, help="The path to the CSV file to import."
        )

    def handle(self, *args, **options):
        csv_file_path = options["csv_file"]
        self.stdout.write(
            self.style.SUCCESS(
                f"Attempting to import loan account data from {csv_file_path} with debug info..."
            )
        )

        # First, let's show all existing borrower_ids in the database
        self.stdout.write(self.style.WARNING("Existing borrower_ids in database:"))
        existing_borrower_ids = list(
            Borrower.objects.values_list("borrower_id", flat=True)
        )
        for borrower_id in existing_borrower_ids[:10]:  # Show first 10
            self.stdout.write(f"  - '{borrower_id}'")
        if len(existing_borrower_ids) > 10:
            self.stdout.write(f"  ... and {len(existing_borrower_ids) - 10} more")
        self.stdout.write(f"Total existing borrowers: {len(existing_borrower_ids)}")

        try:
            with open(csv_file_path, "r", encoding="utf-8-sig") as file:
                try:
                    dialect = csv.Sniffer().sniff(file.read(1024), delimiters=",;\t")
                    file.seek(0)
                except csv.Error:
                    dialect = "excel"  # Default to comma

                reader = csv.DictReader(file, dialect=dialect)
                if not reader.fieldnames:
                    raise CommandError("CSV file is empty or has no headers.")

                # Clean header names
                reader.fieldnames = [name.strip() for name in reader.fieldnames]

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
                not_found_borrower_ids = []

                for row_num, row in enumerate(reader, 1):
                    try:
                        with transaction.atomic():
                            loan_id = row["loan_id"]
                            borrower_id = row["borrower_id"]

                            # Debug: Show the borrower_id we're looking for
                            self.stdout.write(
                                f"\nRow {row_num}: Looking for borrower_id: '{borrower_id}' (type: {type(borrower_id)})"
                            )

                            try:
                                borrower = Borrower.objects.get(borrower_id=borrower_id)
                                self.stdout.write(
                                    f"  ✓ Found borrower: {borrower.full_name}"
                                )
                            except Borrower.DoesNotExist:
                                self.stdout.write(
                                    f"  ✗ Borrower with borrower_id '{borrower_id}' does not exist."
                                )
                                not_found_borrower_ids.append(borrower_id)
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
                                    "borrower": borrower,
                                    "booking_date": booking_date,
                                    "maturity_date": maturity_date,
                                    "original_principal": original_principal,
                                    "interest_rate": interest_rate,
                                    "loan_type": row["loan_type"],
                                    "account_officer_id": row["account_officer_id"],
                                    "status": row.get("status", "PERFORMING"),
                                },
                            )

                            if created:
                                imported_count += 1
                                self.stdout.write(
                                    f"  ✓ Created new loan account: {loan_id}"
                                )
                            else:
                                updated_count += 1
                                self.stdout.write(
                                    f"  ✓ Updated existing loan account: {loan_id}"
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

                # Show summary of not found borrower_ids
                if not_found_borrower_ids:
                    self.stdout.write(
                        self.style.ERROR("\nSummary of borrower_ids not found:")
                    )
                    unique_not_found = set(not_found_borrower_ids)
                    for borrower_id in sorted(unique_not_found):
                        count = not_found_borrower_ids.count(borrower_id)
                        self.stdout.write(
                            f"  - '{borrower_id}' (appeared {count} times)"
                        )
                    self.stdout.write(
                        f"Total unique borrower_ids not found: {len(unique_not_found)}"
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
                            f"\nSuccessfully imported {imported_count} new loan accounts and updated {updated_count} existing accounts."
                        )
                    )

        except FileNotFoundError:
            raise CommandError(f'File "{csv_file_path}" not found.')
        except Exception as e:
            raise CommandError(f"An error occurred during file processing: {e}")
