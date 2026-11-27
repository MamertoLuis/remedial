"""Two-phase CSV import contract (see specs/csv-import/spec.md).

Every CSV import validates the whole file — exact headers, field types,
referential integrity, within-file uniqueness, and provenance conflicts —
before writing any row, then commits all rows in one transaction. Nothing is
written when any row is invalid, and imports exit non-zero through the
command layer.

Anti-coercion rules:
* Dates are ISO ``YYYY-MM-DD`` only (no slash layouts, no Excel serials).
* Unknown ``borrower_type`` values are rejected, never defaulted to PERSON.
* A ``days_past_due`` column on exposures is rejected; days past due is
  computed from the iAccs repayment schedule (``services/iaccs/dpd.py``).
* ``status`` (accounts) and any classification column are rejected for all
  commands; those values are always derived.
"""

import csv
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional, Sequence, Tuple

from django.core.management.base import CommandError
from django.db import transaction

from ..models import Borrower, DelinquencyStatus, Exposure, LoanAccount
from ..services import upsert_borrower, upsert_exposure, upsert_loan_account

#: Columns no CSV import may carry (spec R5): always derived.
CLASSIFICATION_COLUMNS = ("classification", "aging_bucket", "npl_flag", "npl_date")

BORROWER_REQUIRED = ("borrower_id", "full_name")
BORROWER_OPTIONAL = ("borrower_type", "primary_address", "mobile", "borrower_group")
BORROWER_TYPES = tuple(c[0] for c in Borrower.BORROWER_TYPE_CHOICES)

ACCOUNT_REQUIRED = (
    "loan_id",
    "borrower_id",
    "booking_date",
    "maturity_date",
    "original_principal",
    "interest_rate",
    "loan_type",
    "account_officer_id",
    "loan_security",
)
ACCOUNT_OPTIONAL = ("transaction_type",)
ACCOUNT_FORBIDDEN = ("status",)
LOAN_SECURITY_TYPES = tuple(c[0] for c in LoanAccount.LOAN_SECURITY_CHOICES)
TRANSACTION_TYPES = tuple(c[0] for c in LoanAccount.TRANSACTION_TYPE_CHOICES)

EXPOSURE_REQUIRED = (
    "loan_id",
    "as_of_date",
    "principal_outstanding",
    "accrued_interest",
    "accrued_penalty",
)
EXPOSURE_OPTIONAL = ("shouldbepay", "actualpay")
EXPOSURE_FORBIDDEN = ("days_past_due",)

IACCS = "IACCS"
CSV = "CSV"


class RowError(Exception):
    """A single row failed validation; the whole file is rejected."""

    def __init__(self, row_number: int, message: str):
        self.row_number = row_number
        super().__init__(f"Row {row_number}: {message}")


@dataclass
class ImportSummary:
    created: int = 0
    updated: int = 0
    skipped: int = 0

    @property
    def total(self) -> int:
        return self.created + self.updated + self.skipped


# --------------------------------------------------------------------------- #
# Parsing primitives (no coercion)
# --------------------------------------------------------------------------- #


def parse_iso_date(value: Optional[str], row: int, field: str) -> date:
    """ISO ``YYYY-MM-DD`` only; anything else is rejected."""
    raw = (value or "").strip()
    if not raw:
        raise RowError(row, f"{field} is required")
    try:
        return date.fromisoformat(raw)
    except ValueError:
        raise RowError(row, f"{field} '{raw}' is not ISO YYYY-MM-DD")


def parse_decimal(
    value: Optional[str], row: int, field: str, *, required: bool = True
) -> Decimal:
    raw = (value or "").strip() if value is not None else ""
    if raw == "":
        if required:
            raise RowError(row, f"{field} is required")
        return Decimal("0.00")
    try:
        return Decimal(raw)
    except InvalidOperation:
        raise RowError(row, f"{field} '{raw}' is not a valid number")


def parse_choice(value: Optional[str], row: int, field: str, choices: Sequence[str]) -> str:
    raw = (value or "").strip() if value is not None else ""
    if raw == "":
        raise RowError(row, f"{field} is required")
    if raw not in choices:
        raise RowError(
            row,
            f"{field} '{raw}' is not recognized; expected one of {', '.join(choices)}",
        )
    return raw


def parse_text(
    value: Optional[str], row: int, field: str, *, required: bool = True
) -> str:
    raw = (value or "").strip() if value is not None else ""
    if required and raw == "":
        raise RowError(row, f"{field} is required")
    return raw


# --------------------------------------------------------------------------- #
# Header contract
# --------------------------------------------------------------------------- #


def check_headers(
    fieldnames: Sequence[str],
    required: Sequence[str],
    optional: Sequence[str],
    forbidden: Sequence[str],
) -> Optional[str]:
    """Return a file-level error message when the header contract is violated.

    Exact headers: missing required columns, unknown columns, and forbidden
    (derived/legacy) columns all reject the file before any row is parsed.
    """
    present = [name for name in fieldnames]

    missing = [h for h in required if h not in present]
    unknown = [
        h
        for h in present
        if h not in required and h not in optional and h not in forbidden
    ]
    legacy = [h for h in forbidden if h in present]

    messages = []
    if missing:
        messages.append(
            f"missing required columns: {', '.join(missing)}"
        )
    if unknown:
        messages.append(
            f"unknown columns not part of the import contract: {', '.join(unknown)}"
        )
    for column in legacy:
        messages.append(
            f"column '{column}' is not part of the import contract: "
            f"it is derived by the system and must be removed from the file"
        )

    if not messages:
        return None
    return "CSV header contract violated; nothing was imported. " + "; ".join(messages)


# --------------------------------------------------------------------------- #
# File reading
# --------------------------------------------------------------------------- #


def load_csv_rows(path: str) -> Tuple[List[str], List[Dict[str, str]]]:
    """Read a CSV file into stripped headers and raw rows."""
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as fh:
            sample = fh.read(1024)
            fh.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
                reader = csv.DictReader(fh, dialect=dialect)
            except csv.Error:
                # Fall back to a comma reader; a single-column header without a
                # delimiter is a valid (if minimal) contract file.
                reader = csv.DictReader(fh, delimiter=",")
            if not reader.fieldnames:
                raise CommandError("CSV file is empty or has no headers.")
            fieldnames = [name.strip() for name in reader.fieldnames]
            rows = [row for row in reader]
            return fieldnames, rows
    except FileNotFoundError:
        raise CommandError(f'File "{path}" not found.')


# --------------------------------------------------------------------------- #
# Command-specific parse and write phases
# --------------------------------------------------------------------------- #


def import_borrowers_file(
    path: str, *, dry_run: bool = False, skip_existing: bool = False
) -> ImportSummary:
    fieldnames, raw_rows = load_csv_rows(path)
    header_error = check_headers(
        fieldnames, BORROWER_REQUIRED, BORROWER_OPTIONAL, CLASSIFICATION_COLUMNS
    )
    if header_error:
        raise CommandError(header_error)

    parsed = []
    errors: List[str] = []
    for row_number, row in enumerate(raw_rows, start=2):
        try:
            borrower_id = parse_text(row.get("borrower_id"), row_number, "borrower_id")
            full_name = parse_text(row.get("full_name"), row_number, "full_name")
            borrower_type = parse_text(
                row.get("borrower_type", ""), row_number, "borrower_type", required=False
            ) or "PERSON"
            if borrower_type not in BORROWER_TYPES:
                raise RowError(
                    row_number,
                    f"borrower_type '{borrower_type}' is not recognized; "
                    f"expected one of {', '.join(BORROWER_TYPES)}",
                )
            parsed.append(
                {
                    "row_number": row_number,
                    "borrower_id": borrower_id,
                    "full_name": full_name,
                    "borrower_type": borrower_type,
                    "primary_address": parse_text(
                        row.get("primary_address", ""),
                        row_number,
                        "primary_address",
                        required=False,
                    ),
                    "mobile": parse_text(
                        row.get("mobile", ""), row_number, "mobile", required=False
                    ),
                    "borrower_group": parse_text(
                        row.get("borrower_group", ""),
                        row_number,
                        "borrower_group",
                        required=False,
                    ) or None,
                }
            )
        except RowError as exc:
            errors.append(str(exc))

    errors.extend(_uniqueness_errors(parsed, ("borrower_id",)))
    if errors:
        raise CommandError(
            f"Finished with {len(errors)} errors; no rows were written.\n"
            + "\n".join(errors)
        )

    summary = ImportSummary()
    with transaction.atomic():
        for row in parsed:
            exists = Borrower.objects.filter(borrower_id=row["borrower_id"]).exists()
            if dry_run:
                summary.updated += 1 if exists else 0
                summary.created += 0 if exists else 1
                continue
            if skip_existing and exists:
                summary.skipped += 1
                continue
            _, created = upsert_borrower(
                borrower_id=row["borrower_id"],
                defaults={
                    "borrower_type": row["borrower_type"],
                    "full_name": row["full_name"],
                    "primary_address": row["primary_address"],
                    "mobile": row["mobile"],
                    "borrower_group": row["borrower_group"],
                },
            )
            summary.created += 1 if created else 0
            summary.updated += 0 if created else 1
    return summary


def import_accounts_file(
    path: str, *, dry_run: bool = False, skip_existing: bool = False
) -> ImportSummary:
    fieldnames, raw_rows = load_csv_rows(path)
    header_error = check_headers(
        fieldnames,
        ACCOUNT_REQUIRED,
        ACCOUNT_OPTIONAL,
        (*ACCOUNT_FORBIDDEN, *CLASSIFICATION_COLUMNS),
    )
    if header_error:
        raise CommandError(header_error)

    parsed = []
    errors: List[str] = []
    for row_number, row in enumerate(raw_rows, start=2):
        try:
            loan_id = parse_text(row.get("loan_id"), row_number, "loan_id")
            borrower_id = parse_text(
                row.get("borrower_id"), row_number, "borrower_id"
            )
            parsed.append(
                {
                    "row_number": row_number,
                    "loan_id": loan_id,
                    "borrower_id": borrower_id,
                    "booking_date": parse_iso_date(
                        row.get("booking_date"), row_number, "booking_date"
                    ),
                    "maturity_date": parse_iso_date(
                        row.get("maturity_date"), row_number, "maturity_date"
                    ),
                    "original_principal": parse_decimal(
                        row.get("original_principal"), row_number, "original_principal"
                    ),
                    "interest_rate": parse_decimal(
                        row.get("interest_rate"), row_number, "interest_rate"
                    ),
                    "loan_type": parse_text(
                        row.get("loan_type"), row_number, "loan_type"
                    ),
                    "account_officer_id": parse_text(
                        row.get("account_officer_id"),
                        row_number,
                        "account_officer_id",
                    ),
                    "loan_security": parse_choice(
                        row.get("loan_security"),
                        row_number,
                        "loan_security",
                        LOAN_SECURITY_TYPES,
                    ),
                    "transaction_type": (
                        parse_text(
                            row.get("transaction_type", ""),
                            row_number,
                            "transaction_type",
                            required=False,
                        )
                        or None
                    ),
                }
            )
        except RowError as exc:
            errors.append(str(exc))

    errors.extend(_uniqueness_errors(parsed, ("loan_id",)))

    # Referential integrity (validation phase): borrowers must exist.
    for row in parsed:
        if not Borrower.objects.filter(borrower_id=row["borrower_id"]).exists():
            errors.append(
                f"Row for loan_id '{row['loan_id']}': borrower '{row['borrower_id']}' "
                f"does not exist; import the borrower first."
            )

    if errors:
        raise CommandError(
            f"Finished with {len(errors)} errors; no rows were written.\n"
            + "\n".join(errors)
        )

    summary = ImportSummary()
    with transaction.atomic():
        for row in parsed:
            exists = LoanAccount.objects.filter(loan_id=row["loan_id"]).exists()
            if dry_run:
                summary.updated += 1 if exists else 0
                summary.created += 0 if exists else 1
                continue
            if skip_existing and exists:
                summary.skipped += 1
                continue
            borrower = Borrower.objects.get(borrower_id=row["borrower_id"])
            _, created = upsert_loan_account(
                loan_id=row["loan_id"],
                defaults={
                    "borrower": borrower,
                    "booking_date": row["booking_date"],
                    "maturity_date": row["maturity_date"],
                    "original_principal": row["original_principal"],
                    "interest_rate": row["interest_rate"],
                    "loan_type": row["loan_type"],
                    "loan_security": row["loan_security"],
                    "account_officer_id": row["account_officer_id"],
                    "transaction_type": row["transaction_type"],
                },
            )
            summary.created += 1 if created else 0
            summary.updated += 0 if created else 1
    return summary


def import_exposures_file(
    path: str,
    *,
    dry_run: bool = False,
    snapshot_type: str = "EVENT",
    conn=None,
    cutoff: Optional[date] = None,
) -> ImportSummary:
    """Import exposure observations; days past due comes from the iAccs schedule.

    ``conn`` is the read-only iAccs connection (see ``services/iaccs/connection``)
    and is required: DPD is computed per loan via ``services/iaccs/dpd.py``.
    """
    if conn is None:
        raise CommandError(
            "Exposure imports require a live iAccs connection (MYSQL56_* env) "
            "to compute days past due from the repayment schedule."
        )

    if cutoff is None:
        raise CommandError("A cutoff date is required for exposure imports.")

    fieldnames, raw_rows = load_csv_rows(path)
    header_error = check_headers(
        fieldnames,
        EXPOSURE_REQUIRED,
        EXPOSURE_OPTIONAL,
        (*EXPOSURE_FORBIDDEN, *CLASSIFICATION_COLUMNS),
    )
    if header_error:
        raise CommandError(header_error)

    from .iaccs import dpd as iaccs_dpd

    parsed = []
    errors: List[str] = []
    for row_number, row in enumerate(raw_rows, start=2):
        try:
            loan_id = parse_text(row.get("loan_id"), row_number, "loan_id")
            as_of_date = parse_iso_date(row.get("as_of_date"), row_number, "as_of_date")
            parsed.append(
                {
                    "row_number": row_number,
                    "loan_id": loan_id,
                    "as_of_date": as_of_date,
                    "principal_outstanding": parse_decimal(
                        row.get("principal_outstanding"),
                        row_number,
                        "principal_outstanding",
                    ),
                    "accrued_interest": parse_decimal(
                        row.get("accrued_interest"), row_number, "accrued_interest"
                    ),
                    "accrued_penalty": parse_decimal(
                        row.get("accrued_penalty"), row_number, "accrued_penalty"
                    ),
                    "shouldbepay": (
                        parse_decimal(
                            row.get("shouldbepay", ""),
                            row_number,
                            "shouldbepay",
                            required=False,
                        )
                        if (row.get("shouldbepay") or "").strip()
                        else None
                    ),
                    "actualpay": (
                        parse_decimal(
                            row.get("actualpay", ""),
                            row_number,
                            "actualpay",
                            required=False,
                        )
                        if (row.get("actualpay") or "").strip()
                        else None
                    ),
                }
            )
        except RowError as exc:
            errors.append(str(exc))

    errors.extend(
        _uniqueness_errors(parsed, ("loan_id", "as_of_date"))
    )

    # Referential integrity + provenance + DPD (validation phase).
    for row in parsed:
        account = LoanAccount.objects.filter(loan_id=row["loan_id"]).first()
        if account is None:
            errors.append(
                f"Row for loan_id '{row['loan_id']}': loan account does not exist; "
                f"import the account first."
            )
            continue

        iaccs_snapshot = Exposure.objects.filter(
            account=account, as_of_date=row["as_of_date"], source=IACCS
        ).exists() or DelinquencyStatus.objects.filter(
            account=account, as_of_date=row["as_of_date"], source=IACCS
        ).exists()
        if iaccs_snapshot:
            errors.append(
                f"Row for loan_id '{row['loan_id']}' as of {row['as_of_date']}: "
                f"an iAccs-tagged snapshot already exists for this date; "
                f"CSV imports must not override same-date iAccs data."
            )
            continue

        try:
            row["days_past_due"] = iaccs_dpd.compute_dpd_for_loan(
                conn, row["loan_id"], row["as_of_date"]
            )
        except ValueError as exc:
            errors.append(
                f"Row for loan_id '{row['loan_id']}': {exc}"
            )

    if errors:
        raise CommandError(
            f"Finished with {len(errors)} errors; no rows were written.\n"
            + "\n".join(errors)
        )

    summary = ImportSummary()
    with transaction.atomic():
        for row in parsed:
            account = LoanAccount.objects.get(loan_id=row["loan_id"])
            exists = Exposure.objects.filter(
                account=account, as_of_date=row["as_of_date"]
            ).exists()
            if dry_run:
                summary.updated += 1 if exists else 0
                summary.created += 0 if exists else 1
                continue
            _, created = upsert_exposure(
                account=account,
                as_of_date=row["as_of_date"],
                defaults={
                    "principal_outstanding": row["principal_outstanding"],
                    "accrued_interest": row["accrued_interest"],
                    "accrued_penalty": row["accrued_penalty"],
                    "days_past_due": row["days_past_due"],
                    "shouldbepay": row["shouldbepay"],
                    "actualpay": row["actualpay"],
                    "snapshot_type": snapshot_type,
                    "source": CSV,
                },
            )
            summary.created += 1 if created else 0
            summary.updated += 0 if created else 1
    return summary


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _uniqueness_errors(
    parsed: List[dict], key_fields: Tuple[str, ...]
) -> List[str]:
    """Within-file duplicate natural keys reject the file (spec R8)."""
    errors: List[str] = []
    seen: Dict[tuple, int] = {}
    for row in parsed:
        key = tuple(row.get(f) for f in key_fields)
        if key in seen:
            errors.append(
                f"Row {row['row_number']}: duplicate {'/'.join(key_fields)} "
                f"{' / '.join(str(k) for k in key)}; each "
                f"{'/'.join(key_fields)} must appear once per file"
            )
        else:
            seen[key] = row["row_number"]
    return errors