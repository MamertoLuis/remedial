"""
Seed the six strategy action catalogs from the remedial framework proposal.

Base action lists mirror the spec scenarios for ``strategy-actions``; every
approval-gated classification follows design D3: financial, legal and
contractual commitments are gated; communication/field actions are not.
RESCIND templates are part of the Compromise / Restructuring catalogs so the
officer-declared-failure flow reuses the catalog template/instance pattern.
"""

from django.db import migrations

# (strategy_type, code, name, requires_approval, ordering)
CATALOG = [
    # Intensive Collection - communication/field actions, agency is a contract
    ("Intensive Collection", "IC-CALL", "Call", False, 10),
    ("Intensive Collection", "IC-SMS", "SMS and Reminder", False, 20),
    ("Intensive Collection", "IC-LETTER", "Collection Letter / Demand Notice", False, 30),
    ("Intensive Collection", "IC-VISIT", "Personal Visit", False, 40),
    ("Intensive Collection", "IC-FIELD", "Field Collection", False, 50),
    ("Intensive Collection", "IC-GUARANTOR", "Guarantor Collection", False, 60),
    ("Intensive Collection", "IC-AGENCY", "Agency Engagement", True, 70),
    # Restructuring - every term change commits the bank contractually
    ("Restructuring", "RS-EXTENSION", "Term Extension", True, 10),
    ("Restructuring", "RS-AMORTIZATION", "Amortization Revision", True, 20),
    ("Restructuring", "RS-FREQUENCY", "Payment Frequency Change", True, 30),
    ("Restructuring", "RS-MORATORIUM", "Moratorium", True, 40),
    ("Restructuring", "RS-REVISION", "Interest / Penalty Revision", True, 50),
    ("Restructuring", "RS-SECURITY", "Additional Security", True, 60),
    ("Restructuring", "RS-CONSOLIDATION", "Consolidation", True, 70),
    ("Restructuring", "RS-RESCIND", "Rescind Arrangement", True, 80),
    # Compromise - settlements commit bank funds; rescind closes a failed one
    ("Compromise", "CP-FULL", "Full Settlement", True, 10),
    ("Compromise", "CP-PARTIAL-CONDONATION", "Partial Settlement with Condonation", True, 20),
    ("Compromise", "CP-INSTALLMENT", "Installment Settlement", True, 30),
    ("Compromise", "CP-DISCOUNTED", "Discounted Settlement", True, 40),
    ("Compromise", "CP-ASSET-PROCEEDS", "Settlement via Asset Sale Proceeds", True, 50),
    ("Compromise", "CP-RESCIND", "Rescind Agreement", True, 60),
    # Collateral Recovery (Foreclosure) - legal/settlement procedures
    ("Foreclosure", "CR-SURRENDER", "Voluntary Surrender", False, 10),
    ("Foreclosure", "CR-EXTRAJUDICIAL", "Extrajudicial Foreclosure", True, 20),
    ("Foreclosure", "CR-JUDICIAL", "Judicial Foreclosure", True, 30),
    ("Foreclosure", "CR-REPOSSESSION", "Repossession", True, 40),
    ("Foreclosure", "CR-DISPOSAL", "Acquisition and Disposal", True, 50),
    # Legal Action - legal procedures; final demand is a communication
    ("Legal Action", "LA-FINAL-DEMAND", "Final Demand", False, 10),
    ("Legal Action", "LA-COUNSEL", "Counsel Referral", True, 20),
    ("Legal Action", "LA-FILING", "Case Filing", True, 30),
    ("Legal Action", "LA-FORECLOSURE-PROCEEDINGS", "Foreclosure Proceedings", True, 40),
    ("Legal Action", "LA-JUDGMENT-ENFORCEMENT", "Judgment Enforcement", True, 50),
    ("Legal Action", "LA-ASSET-EXECUTION", "Asset Execution", True, 60),
    # Write-Off - booking/write-off approvals and post-write-off recovery
    ("Write-Off", "WO-APPROVAL", "Write-Off Approval", True, 10),
    ("Write-Off", "WO-AGENCY", "Agency Endorsement", True, 20),
    ("Write-Off", "WO-CONTINUED-COLLECTION", "Continued Collection", False, 30),
    ("Write-Off", "WO-RECOVERY-MONITORING", "Recovery Monitoring", False, 40),
]


def seed_catalogs(apps, schema_editor):
    StrategyActionCatalogEntry = apps.get_model(
        "account_master", "StrategyActionCatalogEntry"
    )
    for strategy_type, code, name, requires_approval, ordering in CATALOG:
        StrategyActionCatalogEntry.objects.get_or_create(
            strategy_type=strategy_type,
            code=code,
            defaults={
                "name": name,
                "requires_approval": requires_approval,
                "ordering": ordering,
            },
        )


def unseed_catalogs(apps, schema_editor):
    StrategyActionCatalogEntry = apps.get_model(
        "account_master", "StrategyActionCatalogEntry"
    )
    codes = [row[1] for row in CATALOG]
    StrategyActionCatalogEntry.objects.filter(code__in=codes).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("account_master", "0005_collateral_guarantor_strategyactioncatalogentry_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_catalogs, unseed_catalogs),
    ]
