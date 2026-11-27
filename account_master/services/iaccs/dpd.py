"""Shared days-past-due computation for any import path.

The aggregate-shortfall rule itself lives in
:func:`account_master.services.iaccs.mapper.compute_schedule_dpd`; this
module supplies the per-loan source inputs (repayment schedule and principal
repaid) so callers that are not the bulk branch loader — today the CSV
exposure import — compute DPD against the same iAccs ``amortsched`` / ``sldtl``
data, through the same read-only connection.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from . import loader, mapper


def compute_dpd_for_loan(conn: Any, loan_id: str, cutoff: date) -> int:
    """Aggregate-shortfall days past due for one loan key through *cutoff*.

    Parses the rendered ``loan_id`` back to the five-part key, fetches the
    loan's repayment schedule and principal repaid from the read-only iAccs
    connection, and applies the same rule as the bulk iaccs import.
    """
    loan_key = mapper.parse_loan_id(loan_id)
    schedule = loader.fetch_loan_schedule(conn, loan_key, cutoff)
    repaid = loader.fetch_loan_repayments(conn, loan_key, cutoff)
    return mapper.compute_schedule_dpd(schedule, repaid, cutoff)