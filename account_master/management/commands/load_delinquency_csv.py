import csv
import re
from datetime import date, datetime

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from account_master.models import LoanAccount
from account_master.services import upsert_delinquency_status


class Command(BaseCommand):
    help = "Import delinquency status rows from a CSV file."

    FIELD_ALIASES = {
        "loanid": "loan_id",
        "loan_id": "loan_id",
        "asofdate": "as_of_date",
        "as_of_date": "as_of_date",
        "dayspastdue": "days_past_due",
        "days_past_due": "days_past_due",
        "nplflag": "npl_flag",
        "npl_flag": "npl_flag",
        "npl_date": "npl_date",
        "snapshot": "snapshot_type",
        "snapshottype": "snapshot_type",
        "snapshot_type": "snapshot_type",
        "agingbucket": "aging_bucket",
        "classification": "classification",
    }

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_path", help="Path to the CSV file containing delinquency snapshots."
        )
        parser.add_argument(
            "--delimiter",
            default=",",
            help="Delimiter used in the CSV (default is comma).",
        )
        parser.add_argument(
            "--encoding",
            default="utf-8",
            help="File encoding (default utf-8).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Parse and validate the CSV without writing to the database.",
        )

    def handle(self, *args, **options):
        path = options["csv_path"]
        delimiter = options["delimiter"]
        encoding = options["encoding"]
        dry_run = options["dry_run"]

        try:
            csv_file = open(path, encoding=encoding, newline="")
        except FileNotFoundError as exc:
            raise CommandError(f"File not found: {path}") from exc

        with csv_file:
            reader = csv.DictReader(csv_file, delimiter=delimiter)
            if not reader.fieldnames:
                raise CommandError("CSV file must include headers.")

            stats = {
                "rows": 0,
                "upserts": 0,
                "created": 0,
                "updated": 0,
                "skipped": 0,
                "errors": 0,
            }

            for row_number, raw_row in enumerate(reader, start=2):
                stats["rows"] += 1
                normalized = {}
                for key, value in raw_row.items():
                    canonical = self._normalize_header(key)
                    if not canonical:
                        continue
                    normalized[canonical] = (value or "").strip()

                loan_id = normalized.get("loan_id")
                as_of_date_raw = normalized.get("as_of_date")

                if not loan_id or not as_of_date_raw:
                    self.stderr.write(
                        f"Row {row_number}: missing required loan_id or as_of_date—skipping."
                    )
                    stats["skipped"] += 1
                    continue

                as_of_date = self._parse_date(as_of_date_raw)
                if not as_of_date:
                    self.stderr.write(
                        f"Row {row_number}: invalid as_of_date '{as_of_date_raw}'—skipping."
                    )
                    stats["errors"] += 1
                    continue

                try:
                    account = LoanAccount.objects.get(loan_id=loan_id)
                except LoanAccount.DoesNotExist:
                    self.stderr.write(
                        f"Row {row_number}: loan_id '{loan_id}' not found—skipping."
                    )
                    stats["skipped"] += 1
                    continue

                days_past_due_raw = normalized.get("days_past_due")
                if days_past_due_raw == "":
                    days_past_due = 0
                else:
                    try:
                        days_past_due = int(days_past_due_raw)
                    except ValueError:
                        self.stderr.write(
                            f"Row {row_number}: invalid days_past_due '{days_past_due_raw}'—skipping."
                        )
                        stats["errors"] += 1
                        continue

                npl_flag = self._parse_bool(normalized.get("npl_flag", ""))
                npl_date = self._parse_date(normalized.get("npl_date", ""))
                snapshot_type = normalized.get("snapshot_type") or "EVENT"

                defaults = {
                    "days_past_due": days_past_due,
                    "aging_bucket": normalized.get("aging_bucket") or "",
                    "classification": normalized.get("classification") or "",
                    "npl_flag": npl_flag,
                    "npl_date": npl_date,
                    "snapshot_type": snapshot_type,
                }

                if dry_run:
                    stats["upserts"] += 1
                    continue

                with transaction.atomic():
                    _, created = upsert_delinquency_status(
                        account=account,
                        as_of_date=as_of_date,
                        defaults=defaults,
                    )
                stats["upserts"] += 1
                if created:
                    stats["created"] += 1
                else:
                    stats["updated"] += 1

        summary = (
            f"Processed {stats['rows']} rows, "
            f"applied {stats['upserts']} upserts ({stats['created']} created/{stats['updated']} updated), "
            f"skipped {stats['skipped']}, errors {stats['errors']}"
        )
        if dry_run:
            summary += ", dry-run mode (no DB changes)"

        self.stdout.write(self.style.SUCCESS(summary))

    def _parse_date(self, value: str | None) -> date | None:
        if not value:
            return None
        for parser in (date.fromisoformat, self._parse_legacy):
            try:
                return parser(value)
            except ValueError:
                continue
        return None

    def _parse_legacy(self, value: str) -> date:
        return datetime.strptime(value, "%Y-%m-%d").date()

    def _parse_bool(self, value: str | None) -> bool:
        if not value:
            return False
        return value.strip().lower() in {"1", "true", "yes", "y"}

    def _normalize_header(self, header: str | None) -> str:
        if not header:
            return ""
        normalized = re.sub(r"[^a-z0-9]", "", header.lower())
        return self.FIELD_ALIASES.get(normalized, normalized)
