import csv
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from account_master.services import upsert_borrower


class Command(BaseCommand):
    help = "Imports borrower data from a CSV file."

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_file", type=str, help="The path to the CSV file to import."
        )

    def handle(self, *args, **options):
        csv_file_path = options["csv_file"]
        self.stdout.write(
            self.style.SUCCESS(
                f"Attempting to import borrower data from {csv_file_path}..."
            )
        )

        try:
            with open(csv_file_path, "r", encoding="utf-8") as file:
                reader = csv.DictReader(file)
                if not reader.fieldnames:
                    raise CommandError("CSV file is empty or has no headers.")

                required_headers = [
                    "borrower_id",
                    "borrower_type",
                    "full_name",
                    "primary_address",
                    "mobile",
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
                            borrower_id = row["borrower_id"]

                            _, created = upsert_borrower(
                                borrower_id=borrower_id,
                                defaults={
                                    "borrower_type": row.get("borrower_type", "PERSON"),
                                    "full_name": row.get("full_name"),
                                    "primary_address": row.get("primary_address"),
                                    "mobile": row.get("mobile"),
                                },
                            )

                            if created:
                                imported_count += 1
                            else:
                                updated_count += 1

                    except ValueError as e:
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
                            f"Successfully imported {imported_count} new borrowers and updated {updated_count} existing borrowers."
                        )
                    )

        except FileNotFoundError:
            raise CommandError(f'File "{csv_file_path}" not found.')
        except Exception as e:
            raise CommandError(f"An error occurred during file processing: {e}")
