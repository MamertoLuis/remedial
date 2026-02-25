import csv
from datetime import datetime, date
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from account_master.models import Borrower
from account_master.services import upsert_loan_account


class Command(BaseCommand):
    help = "Enhanced import of loan account data with detailed debugging and error reporting."

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_file", type=str, help="The path to the CSV file to import."
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be imported without actually importing.",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Show detailed processing information for each row.",
        )
        parser.add_argument(
            "--skip-errors",
            action="store_true",
            help="Continue processing even if some rows have errors.",
        )

    def _find_similar_borrower_ids(self, borrower_id, max_suggestions=5):
        """
        Find borrower_ids that are similar to the given one (helpful for debugging).
        """
        # Look for borrower_ids that contain the search string
        similar = Borrower.objects.filter(
            borrower_id__icontains=borrower_id
        ).values_list("borrower_id", flat=True)[:max_suggestions]

        return list(similar)

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
        dry_run = options["dry_run"]
        verbose = options["verbose"]
        skip_errors = options["skip_errors"]

        self.stdout.write(
            self.style.SUCCESS(
                f"Enhanced import of loan account data from {csv_file_path}..."
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

                # Print CSV info
                total_rows = sum(1 for row in reader)
                file.seek(0)
                reader = csv.DictReader(file, dialect=dialect)

                self.stdout.write(f"CSV Info:")
                self.stdout.write(f"  Headers: {reader.fieldnames}")
                self.stdout.write(f"  Total rows: {total_rows}")

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

                # Analyze borrower_ids in CSV vs database
                csv_borrower_ids = set()
                for row in reader:
                    borrower_id = row.get("borrower_id", "").strip()
                    if borrower_id:
                        csv_borrower_ids.add(borrower_id)
                file.seek(0)
                reader = csv.DictReader(file, dialect=dialect)

                db_borrower_ids = set(
                    Borrower.objects.values_list("borrower_id", flat=True)
                )

                self.stdout.write(f"\nBorrower Analysis:")
                self.stdout.write(
                    f"  Unique borrower_ids in CSV: {len(csv_borrower_ids)}"
                )
                self.stdout.write(
                    f"  Unique borrower_ids in database: {len(db_borrower_ids)}"
                )

                missing_borrowers = csv_borrower_ids - db_borrower_ids
                if missing_borrowers:
                    self.stdout.write(
                        self.style.ERROR(
                            f"  Missing borrowers in database: {len(missing_borrowers)}"
                        )
                    )
                    if len(missing_borrowers) <= 10:
                        self.stdout.write(
                            f"    Missing: {', '.join(sorted(missing_borrowers))}"
                        )
                    else:
                        self.stdout.write(
                            f"    First 10 missing: {', '.join(sorted(list(missing_borrowers)[:10]))}..."
                        )
                else:
                    self.stdout.write(
                        self.style.SUCCESS(f"  All borrower_ids found in database!")
                    )

                # Check for duplicate loan_ids
                csv_loan_ids = []
                for row in reader:
                    loan_id = row.get("loan_id", "").strip()
                    if loan_id:
                        csv_loan_ids.append(loan_id)
                file.seek(0)
                reader = csv.DictReader(file, dialect=dialect)

                from collections import Counter

                loan_id_counter = Counter(csv_loan_ids)
                duplicate_loan_ids = [
                    loan_id for loan_id, count in loan_id_counter.items() if count > 1
                ]

                if duplicate_loan_ids:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  Duplicate loan_ids found: {len(duplicate_loan_ids)}"
                        )
                    )
                    if len(duplicate_loan_ids) <= 10:
                        self.stdout.write(
                            f"    Duplicates: {', '.join(duplicate_loan_ids)}"
                        )
                    else:
                        self.stdout.write(
                            f"    First 10 duplicates: {', '.join(duplicate_loan_ids[:10])}..."
                        )

                imported_count = 0
                updated_count = 0
                skipped_count = 0
                errors = []

                self.stdout.write(f"\nProcessing {total_rows} rows...")
                for row_num, row in enumerate(reader, 1):
                    try:
                        with transaction.atomic():
                            # Clean and validate required fields
                            loan_id = self._clean_value(row["loan_id"], "loan_id")
                            borrower_id = self._clean_value(
                                row["borrower_id"], "borrower_id"
                            )

                            # Check if borrower exists
                            try:
                                borrower = Borrower.objects.get(borrower_id=borrower_id)
                            except Borrower.DoesNotExist:
                                if verbose:
                                    similar_ids = self._find_similar_borrower_ids(
                                        borrower_id
                                    )
                                    similar_msg = ""
                                    if similar_ids:
                                        similar_msg = (
                                            f" Similar: {', '.join(similar_ids)}"
                                        )
                                    self.stdout.write(
                                        f"Row {row_num}: Borrower '{borrower_id}' not found{similar_msg}"
                                    )
                                raise ValueError(
                                    f"Borrower with borrower_id '{borrower_id}' does not exist."
                                    f" Please import the borrower first."
                                )

                            booking_date = self._parse_date(row["booking_date"])
                            maturity_date = self._parse_date(row["maturity_date"])
                            original_principal = Decimal(
                                str(
                                    self._clean_value(
                                        row["original_principal"], "original_principal"
                                    )
                                )
                            )
                            interest_rate = Decimal(
                                str(
                                    self._clean_value(
                                        row["interest_rate"], "interest_rate"
                                    )
                                )
                            )

                            # Clean optional fields
                            loan_type = self._clean_value(row["loan_type"], "loan_type")
                            account_officer_id = self._clean_value(
                                row["account_officer_id"], "account_officer_id"
                            )
                            status = self._clean_value(
                                row.get("status", ""), "status", required=False
                            )
                            loan_security = self._clean_value(
                                row.get("loan_security", ""),
                                "loan_security",
                                required=False,
                            )

                            if dry_run:
                                if verbose:
                                    self.stdout.write(
                                        f"Row {row_num}: Processing loan '{loan_id}' for borrower '{borrower.full_name}'"
                                    )

                                # Check if loan account exists without actually creating/updating
                                from account_master.models import LoanAccount

                                existing = LoanAccount.objects.filter(
                                    loan_id=loan_id
                                ).exists()
                                if existing:
                                    if verbose:
                                        self.stdout.write(
                                            f"  -> Would UPDATE existing loan account"
                                        )
                                    updated_count += 1
                                else:
                                    if verbose:
                                        self.stdout.write(
                                            f"  -> Would CREATE new loan account"
                                        )
                                    imported_count += 1
                            else:
                                _, created = upsert_loan_account(
                                    loan_id=loan_id,
                                    defaults={
                                        "borrower": borrower,
                                        "booking_date": booking_date,
                                        "maturity_date": maturity_date,
                                        "original_principal": original_principal,
                                        "interest_rate": interest_rate,
                                        "loan_type": loan_type,
                                        "loan_security": loan_security or "UNSECURED",
                                        "account_officer_id": account_officer_id,
                                        "status": status or "PERFORMING",
                                    },
                                )

                                if created:
                                    imported_count += 1
                                    if verbose:
                                        self.stdout.write(
                                            f"Row {row_num}: CREATED loan account '{loan_id}'"
                                        )
                                else:
                                    updated_count += 1
                                    if verbose:
                                        self.stdout.write(
                                            f"Row {row_num}: UPDATED loan account '{loan_id}'"
                                        )

                    except (ValueError, InvalidOperation) as e:
                        error_msg = f"Row {row_num}: Data conversion error - {e}"
                        errors.append(error_msg)
                        if skip_errors:
                            self.stderr.write(self.style.ERROR(error_msg))
                            skipped_count += 1
                            continue
                        else:
                            raise
                    except KeyError as e:
                        error_msg = (
                            f"Row {row_num}: Missing data for expected field - {e}"
                        )
                        errors.append(error_msg)
                        if skip_errors:
                            self.stderr.write(self.style.ERROR(error_msg))
                            skipped_count += 1
                            continue
                        else:
                            raise
                    except Exception as e:
                        error_msg = f"Row {row_num}: An unexpected error occurred - {e}"
                        errors.append(error_msg)
                        if skip_errors:
                            self.stderr.write(self.style.ERROR(error_msg))
                            skipped_count += 1
                            continue
                        else:
                            raise

                # Summary report
                self.stdout.write("\n" + "=" * 50)
                self.stdout.write("IMPORT SUMMARY")
                self.stdout.write("=" * 50)
                self.stdout.write(f"Total rows in CSV: {total_rows}")
                self.stdout.write(f"Rows processed: {imported_count + updated_count}")
                self.stdout.write(f"Rows with errors: {len(errors)}")
                if skip_errors:
                    self.stdout.write(f"Rows skipped: {skipped_count}")
                self.stdout.write(f"  - New accounts imported: {imported_count}")
                self.stdout.write(f"  - Existing accounts updated: {updated_count}")

                if errors:
                    self.stdout.write(
                        self.style.ERROR(f"\nFound {len(errors)} errors:")
                    )
                    for error in errors[:10]:  # Show first 10 errors
                        self.stderr.write(self.style.ERROR(f"  {error}"))
                    if len(errors) > 10:
                        self.stderr.write(
                            self.style.ERROR(
                                f"  ... and {len(errors) - 10} more errors"
                            )
                        )
                    if not skip_errors:
                        raise CommandError(
                            f"Import failed with {len(errors)} errors. Use --skip-errors to continue processing."
                        )
                else:
                    if dry_run:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"\nDRY RUN COMPLETE: Would import {imported_count} new loan accounts and update {updated_count} existing accounts."
                            )
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
