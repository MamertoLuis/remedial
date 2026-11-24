"""iAccs source queries and single-hop import orchestration.

Data-path contract (see ``specs/iaccs-sync/spec.md``):

* Identity comes from the source: the five-part loan key renders ``loan_id``
  and the client key renders ``borrower_id``.
* Every source query is read-only (enforced by ``connection.query``).
* Writes go through the existing service layer (``upsert_borrower`` /
  ``upsert_loan_account`` / ``upsert_exposure``) so the derivation cascade
  (delinquency -> account status -> rule-based ECL) runs unchanged.
* Row-level failures are collected and reported without aborting the rest.

Query conventions mirror ``URBD_Financial_Analytics/scripts/loan_data.py``
and the mapping document ``loan-source-to-target-mapping.md``.

Intentional difference from ``loan_data.py``: the reference extractor's
aggregate query filters rows with ``HAVING SUM(...) <> 0``, which drops
fully-settled loans (outstanding == 0) from the aggregates. Those loans then
appear to have made no repayments, producing inflated schedule DPD. The
loader here deliberately omits that HAVING clause, so settled loans keep
``principal_outstanding == 0`` and ``days_past_due == 0`` (verified: of the
9,141 live loans, 617 settled loans differ from the reference extractor for
exactly this reason; balances agree on all 9,141).
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from django.db import transaction

from . import mapper
from .connection import query

logger = logging.getLogger(__name__)

#: Column used to bound postings/schedule by the as-of date, per convention.
_MASTER_SQL = """
SELECT
    l.LoanBR_CODE   AS loan_br,
    l.LoanSLT_CODE  AS loan_slt,
    l.LoanREF_NO    AS loan_ref,
    l.ClientIDLoan  AS client_id,
    CONCAT_WS(' ', cl.LName, cl.FName, cl.MName) AS client_name,
    st.SLTypeM_DESC AS product,
    l.LoanSTATUS    AS loan_status,
    cts.CTS_TypeDesc AS status_desc,
    l.LoanRESTRUCT  AS restructured,
    (SELECT MAX(a.APPRV_DATE) FROM loanapp a
        WHERE a.BR_CODE  = l.LoanBR_CODE
          AND a.SLC_CODE = l.LoanSLC_CODE
          AND a.SLT_CODE = l.LoanSLT_CODE
          AND a.REF_NO   = l.LoanREF_NO
          AND a.CLIENTID = l.ClientIDLoan
          AND a.STATUSID IN (%(min_status)s, %(max_status)s)) AS approval_date,
    l.LoanTR_DATE   AS release_date,
    l.LoanMAT_DATE  AS maturity_date,
    l.LoanPAMT      AS principal_approved,
    l.LoanINT_RATE  AS interest_rate,
    l.LoanProvisionAMT AS allowance
FROM loan l
LEFT JOIN sltype st
    ON st.SLTypeBR_CODE = l.LoanBR_CODE
   AND st.SLTypeSLC_CODE = l.LoanSLC_CODE
   AND st.SLTypeSLT_CODE = l.LoanSLT_CODE
LEFT JOIN cts_type cts ON cts.CTS_TypeCode = l.LoanSTATUS
LEFT JOIN client cl
    ON cl.ClientIDBrCode = l.LoanBR_CODE AND cl.ClientID = l.ClientIDLoan
WHERE l.LoanSLC_CODE = %(slc)s AND l.LoanBR_CODE = %(branch)s
"""

_AGGREGATES_SQL = """
SELECT
    d.SL_BRCODE AS loan_br,
    d.SLT_CODE  AS loan_slt,
    d.REF_NO    AS loan_ref,
    d.SL_CLIENTID AS client_id,
    SUM(CASE WHEN d.SLE_CODE = %(principal)s AND d.AMT > 0
             THEN d.AMT ELSE 0 END) AS total_advanced,
    SUM(CASE WHEN d.SLE_CODE = %(principal)s THEN d.AMT ELSE 0 END) AS outstanding,
    SUM(CASE WHEN d.SLE_CODE = %(principal)s AND d.TR_CODE IN %(collection)s
             AND d.AMT < 0 THEN -d.AMT ELSE 0 END) AS principal_collected,
    SUM(CASE WHEN d.SLE_CODE = %(interest)s AND d.TR_CODE IN %(collection)s
             AND d.AMT < 0 THEN -d.AMT ELSE 0 END) AS interest_collected,
    SUM(CASE WHEN d.SLE_CODE = %(penalty)s AND d.TR_CODE IN %(collection)s
             AND d.AMT < 0 THEN -d.AMT ELSE 0 END) AS penalty_collected
FROM sldtl d
WHERE d.SLC_CODE = %(slc)s AND d.SL_BRCODE = %(branch)s
  AND d.TR_DATE <= %(cutoff)s
  AND d.SLE_CODE IN (%(principal)s, %(interest)s, %(penalty)s)
GROUP BY d.SL_BRCODE, d.SLT_CODE, d.REF_NO, d.SL_CLIENTID
"""

_SCHEDULE_SQL = """
SELECT
    BR_CODE,
    SLT_CODE,
    REF_NO,
    CLIENTID,
    DUEDATE,
    PRINDUE,
    INTDUE
FROM amortsched
WHERE SLC_CODE = %(slc)s AND BR_CODE = %(branch)s AND DUEDATE <= %(cutoff)s
ORDER BY BR_CODE, SLT_CODE, REF_NO, CLIENTID, DUEDATE
"""

_BRANCH_SQL = """
SELECT DISTINCT LoanBR_CODE AS branch
FROM loan
WHERE LoanSLC_CODE = %(slc)s
ORDER BY LoanBR_CODE
"""


def _loan_key(row: dict) -> Tuple[int, int, int, int]:
    return (row["loan_br"], row["loan_slt"], row["loan_ref"], row["client_id"])


def fetch_loan_masters(conn, branch: int) -> List[dict]:
    """Loan master + borrower + product + status rows for *branch*."""
    return query(
        conn,
        _MASTER_SQL,
        {
            "slc": mapper.LOAN_SLC_CODE,
            "branch": branch,
            "min_status": min(mapper.APPROVED_STATUSES),
            "max_status": max(mapper.APPROVED_STATUSES),
        },
    )


def fetch_loan_aggregates(conn, branch: int, cutoff: date) -> List[dict]:
    """Per-loan principal/interest/penalty aggregates through *cutoff*."""
    return query(
        conn,
        _AGGREGATES_SQL,
        {
            "slc": mapper.LOAN_SLC_CODE,
            "branch": branch,
            "cutoff": cutoff,
            "principal": mapper.SLE_PRINCIPAL,
            "interest": mapper.SLE_INTEREST_PAID,
            "penalty": mapper.SLE_PENALTY,
            "collection": mapper.COLLECTION_TR_CODES,
        },
    )


def fetch_schedules(conn, branch: int, cutoff: date) -> Dict[Tuple, List[tuple]]:
    """Repayment schedule rows keyed by loan key, ordered by due date."""
    rows = query(
        conn,
        _SCHEDULE_SQL,
        {"slc": mapper.LOAN_SLC_CODE, "branch": branch, "cutoff": cutoff},
    )
    schedules: Dict[Tuple[int, int, int, int], List[tuple]] = defaultdict(list)
    for row in rows:
        key = (row["BR_CODE"], row["SLT_CODE"], row["REF_NO"], row["CLIENTID"])
        schedules[key].append(
            (row["DUEDATE"], row["PRINDUE"], row["INTDUE"])
        )
    return schedules


def fetch_branches(conn) -> List[int]:
    """Distinct live branches for the loan portfolio (SLC=12)."""
    rows = query(conn, _BRANCH_SQL, {"slc": mapper.LOAN_SLC_CODE})
    return [row["branch"] for row in rows]


def build_records(
    masters: List[dict],
    aggregates: List[dict],
    schedules: Dict[Tuple[int, int, int, int], List[tuple]],
) -> List[dict]:
    """Combine masters, aggregates and schedules into per-loan records.

    Aggregates without a master row are ignored (the ``loan`` master table
    is the source of the portfolio); masters without aggregates default to
    zero balances.
    """
    agg_by_key = {_loan_key(a): a for a in aggregates}
    records = []
    for master in masters:
        key = _loan_key(master)
        records.append(
            {
                "master": master,
                "aggregates": agg_by_key.get(key) or {},
                "schedule": schedules.get(key) or [],
            }
        )
    return records


def _run_loan(record: dict, cutoff: date) -> dict:
    """Upsert borrower, account and exposure for one loan record."""
    master = record["master"]
    agg = record["aggregates"]
    schedule = record["schedule"]

    borrower_id = mapper.render_borrower_id(master["loan_br"], master["client_id"])
    loan_id = mapper.render_loan_id(
        master["loan_br"], master["loan_slt"], master["loan_ref"], master["client_id"]
    )

    from account_master.services import (
        upsert_borrower,
        upsert_exposure,
        upsert_loan_account,
    )

    with transaction.atomic():
        borrower, borrower_created = upsert_borrower(
            borrower_id=borrower_id,
            defaults=mapper.build_borrower_defaults(master),
        )
        account, account_created = upsert_loan_account(
            loan_id=loan_id,
            defaults=mapper.build_loan_defaults(master, borrower),
        )
        exposure, exposure_created = upsert_exposure(
            account=account,
            as_of_date=cutoff,
            defaults=mapper.build_exposure_defaults(master, agg, schedule, cutoff),
        )

    return {
        "loan_id": loan_id,
        "borrower": borrower_id,
        "created": {
            "borrowers": borrower_created,
            "accounts": account_created,
            "exposures": exposure_created,
        },
    }


def import_loans(
    records: List[dict],
    cutoff: date,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Import every loan record, isolating per-row failures.

    Returns a summary with created/updated counts and collected errors.
    Error messages never include source credentials.
    """
    summary = {
        "borrowers_created": 0,
        "borrowers_updated": 0,
        "accounts_created": 0,
        "accounts_updated": 0,
        "exposures_created": 0,
        "exposures_updated": 0,
        "errors": [],
    }

    if dry_run:
        for record in records:
            master = record["master"]
            loan_id = mapper.render_loan_id(
                master["loan_br"],
                master["loan_slt"],
                master["loan_ref"],
                master["client_id"],
            )
            summary["borrowers_updated" if _borrower_exists(master) else "borrowers_created"] += 1
            summary["accounts_updated" if _account_exists(loan_id) else "accounts_created"] += 1
            summary["exposures_created"] += 1
        return summary

    for record in records:
        master = record["master"]
        loan_id = mapper.render_loan_id(
            master["loan_br"],
            master["loan_slt"],
            master["loan_ref"],
            master["client_id"],
        )
        # Base created/updated on pre-import existence so the summary stays
        # consistent with the dry-run report regardless of service-layer
        # return flags (some upserts always report ``created=False``).
        borrower_existed = _borrower_exists(master)
        account_existed = _account_exists(loan_id)
        exposure_existed = _exposure_exists(loan_id, cutoff)
        try:
            _run_loan(record, cutoff)
        except Exception as exc:  # noqa: BLE001 - isolate per-row failures
            summary["errors"].append(f"{loan_id}: {exc}")
            logger.warning("iAccs import failed for loan %s: %s", loan_id, exc)
            continue
        summary[f"borrowers_{'updated' if borrower_existed else 'created'}"] += 1
        summary[f"accounts_{'updated' if account_existed else 'created'}"] += 1
        summary[f"exposures_{'updated' if exposure_existed else 'created'}"] += 1

    return summary


def _borrower_exists(master: dict) -> bool:
    from account_master.models import Borrower

    borrower_id = mapper.render_borrower_id(master["loan_br"], master["client_id"])
    return Borrower.objects.filter(borrower_id=borrower_id).exists()


def _account_exists(loan_id: str) -> bool:
    from account_master.models import LoanAccount

    return LoanAccount.objects.filter(loan_id=loan_id).exists()


def _exposure_exists(loan_id: str, as_of_date: date) -> bool:
    from account_master.models import Exposure

    return Exposure.objects.filter(
        account_id=loan_id, as_of_date=as_of_date
    ).exists()


def sync_from_iaccs(
    conn,
    branch: Optional[int],
    cutoff: date,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Fetch source data and import it into the Django database.

    *branch* may be ``None`` to import every live branch. Returns the
    :func:`import_loans` summary plus a ``loans`` count.
    """
    branches = [branch] if branch is not None else fetch_branches(conn)
    totals: Dict[str, Any] = {
        "borrowers_created": 0,
        "borrowers_updated": 0,
        "accounts_created": 0,
        "accounts_updated": 0,
        "exposures_created": 0,
        "exposures_updated": 0,
        "errors": [],
        "loans": 0,
    }

    for single_branch in branches:
        masters = fetch_loan_masters(conn, single_branch)
        aggregates = fetch_loan_aggregates(conn, single_branch, cutoff)
        schedules = fetch_schedules(conn, single_branch, cutoff)
        records = build_records(masters, aggregates, schedules)
        totals["loans"] += len(records)
        summary = import_loans(records, cutoff, dry_run=dry_run)
        for key in totals:
            if key != "errors":
                totals[key] += summary.get(key, 0)
            else:
                totals[key].extend(summary.get(key, []))

    return totals