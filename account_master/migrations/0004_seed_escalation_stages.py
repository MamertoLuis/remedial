from django.db import migrations

# The fixed escalation ladder template (First Demand → Warning → Legal Intent).
# Durations are a safe default and remain tunable later in Django admin.
STAGES = [
    {"stage_no": 1, "label": "First Demand", "duration_days": 30, "is_terminal": False},
    {"stage_no": 2, "label": "Warning", "duration_days": 30, "is_terminal": False},
    {"stage_no": 3, "label": "Legal Intent", "duration_days": 30, "is_terminal": True},
]


def seed_escalation_stages(apps, schema_editor):
    """Seed the ladder template idempotently, keyed on stage_no."""
    EscalationStage = apps.get_model("account_master", "EscalationStage")
    for stage in STAGES:
        EscalationStage.objects.update_or_create(
            stage_no=stage["stage_no"], defaults=stage
        )


def unseed_escalation_stages(apps, schema_editor):
    """Reverse: remove only the seeded template rows."""
    EscalationStage = apps.get_model("account_master", "EscalationStage")
    EscalationStage.objects.filter(
        stage_no__in=[stage["stage_no"] for stage in STAGES]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("account_master", "0003_alter_alertrule_rule_type_escalationstage_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_escalation_stages, unseed_escalation_stages),
    ]
