import csv
from datetime import datetime, date
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
        parser.add_argument(
            "--snapshot-type",
            type=str,
            choices=["EVENT", "MONTH_END"],
            default="EVENT",
            help="Type of snapshot being imported (EVENT or MONTH_END). Default: EVENT",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be imported without actually importing.",
        )

    def _parse_date(self, date_str):
        """
        Parse date from various possible formats including Excel serial dates.
        """
        if not date_str or date_str.strip() == "":
            raise ValueError("Date cannot be empty")

        date_str = date_str.strip()

        # Try YYYY-MM-DD format first
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            pass

        # Try Excel serial date (numbers like 45874)
        try:
            if date_str.isdigit():
                excel_date = int(date_str)
                # Excel dates start from 1900-01-01, but Excel incorrectly treats 1900 as leap year
                # So we subtract 2 days to get the correct date
                base_date = date(1899, 12, 30)
                parsed_date = base_date.fromordinal(
                    base_date.toordinal() + excel_date - 1
                )
                return parsed_date
        except (ValueError, OverflowError):
            pass

        # Try other common date formats
        formats_to_try = [
            "%m/%d/%Y",
            "%d/%m/%Y",
            "%Y/%m/%d",
            "%m-%d-%Y",
            "%d-%m-%Y",
            "%m/%d/%y",
            "%d/%m/%y",
            "%y/%m/%d",
        ]

        for fmt in formats_to_try:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue

        raise ValueError(f"Date '{date_str}' does not match any expected format")

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

    def handle(self, *args, **options):
        csv_file_path = options["csv_file"]
        snapshot_type = options["snapshot_type"]
        dry_run = options["dry_run"]

        self.stdout.write(
            self.style.SUCCESS(
                f"Attempting to import exposure data from {csv_file_path}..."
            )
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE: No data will actually be imported.")
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
                    "loan_id",
                    "as_of_date",
                    "principal_outstanding",
                    "accrued_interest",
                    "accrued_penalty",
                ]

                optional_headers = [
                    "days_past_due",
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
                errors = []

                for row_num, row in enumerate(reader, 1):
                    try:
                        with transaction.atomic():
                            # Clean and validate required fields
                            loan_id = self._clean_value(row["loan_id"], "loan_id")
                            as_of_date_str = self._clean_value(
                                row["as_of_date"], "as_of_date"
                            )

                            # Get the loan account
                            loan_account = LoanAccount.objects.get(loan_id=loan_id)

                            # Parse the date
                            as_of_date = self._parse_date(as_of_date_str)

                            # Parse decimal fields
                            principal_outstanding = Decimal(
                                self._clean_value(
                                    row.get("principal_outstanding", "0.00"),
                                    "principal_outstanding",
                                )
                            )
                            accrued_interest = Decimal(
                                self._clean_value(
                                    row.get("accrued_interest", "0.00"),
                                    "accrued_interest",
                                )
                            )
                            accrued_penalty = Decimal(
                                self._clean_value(
                                    row.get("accrued_penalty", "0.00"),
                                    "accrued_penalty",
                                )
                            )

                            # Parse optional days_past_due
                            days_past_due_str = row.get("days_past_due", "0")
                            try:
                                days_past_due = int(
                                    self._clean_value(
                                        days_past_due_str,
                                        "days_past_due",
                                        required=False,
                                    )
                                )
                            except ValueError:
                                days_past_due = 0

                            if dry_run:
                                self.stdout.write(
                                    f"Row {row_num}: Would process exposure for loan '{loan_id}' as of {as_of_date}"
                                )
                                # Check if exposure exists without actually creating/updating
                                from account_master.models import Exposure

                                existing = Exposure.objects.filter(
                                    account=loan_account, as_of_date=as_of_date
                                ).exists()
                                if existing:
                                    self.stdout.write(
                                        f"  -> Would UPDATE existing exposure"
                                    )
                                else:
                                    self.stdout.write(f"  -> Would CREATE new exposure")
                                continue

                            _, created = upsert_exposure(
                                account=loan_account,
                                as_of_date=as_of_date,
                                defaults={
                                    "principal_outstanding": principal_outstanding,
                                    "accrued_interest": accrued_interest,
                                    "accrued_penalty": accrued_penalty,
                                    "days_past_due": days_past_due,
                                    "snapshot_type": snapshot_type,
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
                    if dry_run:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"DRY RUN COMPLETE: Would import {imported_count} new exposure records "
                                f"and update {updated_count} existing records."
                            )
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
