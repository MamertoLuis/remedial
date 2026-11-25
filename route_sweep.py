"""Route-render sweep for the ui-workspace shell.

Runs against the development database and uses Django's test client so
templates actually render. Usage:  uv run python route_sweep.py
Exit code 0 = no route crashed with a 500 (template/render failures surface
as 500). Non-zero = at least one route crashed.
"""
import os
import sys

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "remedial.settings.development")
django.setup()

from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from account_master.models import (
    Borrower,
    LoanAccount,
    RemedialStrategy,
    DelinquencyStatus,
    CollectionActivityLog,
    Exposure,
)
from compromise_agreement.models import CompromiseAgreement


def first(klass):
    try:
        return klass.objects.first()
    except Exception:
        return None


def entry(name, kwargs=None, query=None, expect_ok=True):
    return {"name": name, "kwargs": kwargs or {}, "query": query or {},
            "expect_ok": expect_ok}


def make_cases():
    c = [
        entry("dashboard"),
        entry("portfolio_summary"),
        entry("account_list"),
        entry("borrower_list"),
        entry("search", query={"q": "test"}),
        entry("reporting:reports_index"),
        entry("reporting:loan_portfolio_breakdown"),
        entry("reporting:past_due_aging_summary"),
        entry("reporting:npl_portfolio_analysis"),
        entry("reporting:top_20_npl_accounts"),
        entry("reporting:loan_officer_performance_summary"),
        entry("account_login"),
        entry("account_signup"),
    ]
    if b := first(Borrower):
        c.append(entry("borrower_detail", {"borrower_id": b.borrower_id}))
        c.append(entry("update_borrower", {"borrower_id": b.borrower_id}))
        c.append(entry("create_account_for_borrower", {"borrower_id": b.borrower_id}))
    if a := first(LoanAccount):
        c.append(entry("account_detail", {"loan_id": a.loan_id}))
        c.append(entry("update_account", {"loan_id": a.loan_id}))
        c.append(entry("collection_activity_list", {"loan_id": a.loan_id}))
        c.append(entry("escalation_ladder_detail", {"loan_id": a.loan_id}))
        if act := first(CollectionActivityLog):
            c.append(entry("update_collection_activity",
                           {"loan_id": a.loan_id, "activity_id": act.activity_id}))
        if exp := first(Exposure):
            c.append(entry("update_exposure", {"loan_id": a.loan_id, "exposure_id": exp.exposure_id}))
        if d := first(DelinquencyStatus):
            c.append(entry("update_delinquency_status",
                           {"loan_id": a.loan_id, "delinquency_id": d.delinquency_id}))
        if strat := first(RemedialStrategy):
            c.append(entry("remedial_strategy_detail",
                           {"loan_id": a.loan_id, "strategy_id": strat.strategy_id}))
            c.append(entry("update_remedial_strategy",
                           {"loan_id": a.loan_id, "strategy_id": strat.strategy_id}))
    if ca := first(CompromiseAgreement):
        c.append(entry("compromise_agreement_detail", {"pk": ca.pk}))
        c.append(entry("compromise_agreement_update", {"pk": ca.pk}))
    return c


def main():
    U = get_user_model()
    user = U.objects.filter(role="SYSTEM_ADMINISTRATOR").first() or U.objects.first()
    client = Client()
    client.force_login(user)

    failures = []
    ok = 0
    for case in make_cases():
        name, kwargs, query = case["name"], case["kwargs"], case["query"]
        try:
            url = reverse(name, kwargs=kwargs)
        except Exception as e:
            print(f"  SKIP {name}: reverse failed ({e})")
            continue
        resp = client.get(url, data=query if query else None, HTTP_HOST="localhost")
        if resp.status_code == 500:
            failures.append((url, name))
            print(f"  FAIL 500 {url} ({name})")
        else:
            ok += 1
            print(f"  OK {resp.status_code} {url} ({name})")

    print(f"\n{ok} routes OK, {len(failures)} crashed (500).")
    if failures:
        for u, n in failures:
            print(f"  FAIL 500 {u} ({n})")
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()