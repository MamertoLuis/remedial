import csv
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from account_master.services import upsert_borrower


class Command(BaseCommand):
    help = "Imports borrower data from a CSV file with enhanced duplicate prevention."

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_file", type=str, help="The path to the CSV file to import."
        )
        parser.add_argument(
            "--skip-existing",
            action="store_true",
            help="Skip updating existing borrowers (only create new ones).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be imported without actually importing.",
        )

    def _clean_value(self, value, field_name, required=True):
        """
        Clean and validate a field value.
        """
        if value is None:
            if required:
                raise ValueError(f"{field_name} cannot be empty")
            return ""

        value_str = str(value).strip()
        if required and not value_str:
            raise ValueError(f"{field_name} cannot be empty")

        return value_str

    def _normalize_borrower_type(self, borrower_type):
        """
        Normalize borrower type to match database choices.
        """
        if not borrower_type:
            return "PERSON"

        borrower_type = borrower_type.strip().upper()

        # Map common variations to standard values
        type_mapping = {
            "PERSON": "PERSON",
            "INDIVIDUAL": "PERSON",
            "P": "PERSON",
            "CORP": "CORP",
            "CORPORATION": "CORP",
            "C": "CORP",
            "COMPANY": "CORP",
            "COOP": "COOP",
            "COOPERATIVE": "COOP",
            "CO-OP": "COOP",
        }

        return type_mapping.get(borrower_type, "PERSON")

    def handle(self, *args, **options):
        csv_file_path = options["csv_file"]
        skip_existing = options["skip_existing"]
        dry_run = options["dry_run"]

        self.stdout.write(
            self.style.SUCCESS(
                f"Attempting to import borrower data from {csv_file_path}..."
            )
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE: No data will actually be imported.")
            )

        if skip_existing:
            self.stdout.write(
                self.style.WARNING(
                    "SKIP EXISTING MODE: Only new borrowers will be created."
                )
            )

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
                    "borrower_id",
                    "full_name",
                ]

                optional_headers = [
                    "borrower_type",
                    "primary_address",
                    "mobile",
                    "borrower_group",
                ]

                if not all(header in reader.fieldnames for header in required_headers):
                    missing_headers = [
                        h for h in required_headers if h not in reader.fieldnames
                    ]
                    raise CommandError(
                        f"Missing required CSV headers: {', '.join(missing_headers)}. "
                        f"Required: {', '.join(required_headers)}. Found: {', '.join(reader.fieldnames)}"
                    )

                # Check for optional headers
                missing_optional = [
                    h for h in optional_headers if h not in reader.fieldnames
                ]
                if missing_optional:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Optional headers missing: {', '.join(missing_optional)}. "
                            f"Will use default values for these fields."
                        )
                    )

                imported_count = 0
                updated_count = 0
                skipped_count = 0
                errors = []

                # Track processed borrower_ids to detect duplicates within the CSV
                processed_borrower_ids = set()

                for row_num, row in enumerate(reader, 1):
                    try:
                        with transaction.atomic():
                            # Clean and validate required fields
                            borrower_id = self._clean_value(
                                row["borrower_id"], "borrower_id"
                            )
                            full_name = self._clean_value(row["full_name"], "full_name")

                            # Check for duplicates within this CSV file
                            if borrower_id in processed_borrower_ids:
                                errors.append(
                                    f"Row {row_num}: Duplicate borrower_id '{borrower_id}' found within this CSV file. "
                                    f"Each borrower_id should appear only once."
                                )
                                continue

                            processed_borrower_ids.add(borrower_id)

                            # Clean and normalize other fields
                            borrower_type = self._normalize_borrower_type(
                                row.get("borrower_type", "")
                            )
                            primary_address = self._clean_value(
                                row.get("primary_address", ""),
                                "primary_address",
                                required=False,
                            )
                            mobile = self._clean_value(
                                row.get("mobile", ""), "mobile", required=False
                            )
                            borrower_group = self._clean_value(
                                row.get("borrower_group", ""),
                                "borrower_group",
                                required=False,
                            )

                            if dry_run:
                                self.stdout.write(
                                    f"Row {row_num}: Would process borrower_id '{borrower_id}', name '{full_name}'"
                                )
                                # Check if borrower exists without actually creating/updating
                                from account_master.models import Borrower

                                existing = Borrower.objects.filter(
                                    borrower_id=borrower_id
                                ).exists()
                                if existing:
                                    if not skip_existing:
                                        self.stdout.write(
                                            f"  -> Would UPDATE existing borrower"
                                        )
                                    else:
                                        self.stdout.write(
                                            f"  -> Would SKIP existing borrower"
                                        )
                                else:
                                    self.stdout.write(f"  -> Would CREATE new borrower")
                                continue

                            if skip_existing:
                                # Check if borrower exists first
                                from account_master.models import Borrower

                                if Borrower.objects.filter(
                                    borrower_id=borrower_id
                                ).exists():
                                    skipped_count += 1
                                    self.stdout.write(
                                        f"Row {row_num}: Skipped existing borrower '{borrower_id}'"
                                    )
                                    continue

                            _, created = upsert_borrower(
                                borrower_id=borrower_id,
                                defaults={
                                    "borrower_type": borrower_type,
                                    "full_name": full_name,
                                    "primary_address": primary_address,
                                    "mobile": mobile,
                                    "borrower_group": borrower_group or None,
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
                    if dry_run:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"DRY RUN COMPLETE: Would import {imported_count} new borrowers "
                                f"and update {updated_count} existing borrowers."
                            )
                        )
                    else:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"Successfully imported {imported_count} new borrowers, "
                                f"updated {updated_count} existing borrowers, "
                                f"and skipped {skipped_count} existing borrowers."
                            )
                        )

        except FileNotFoundError:
            raise CommandError(f'File "{csv_file_path}" not found.')
        except Exception as e:
            raise CommandError(f"An error occurred during file processing: {e}")
