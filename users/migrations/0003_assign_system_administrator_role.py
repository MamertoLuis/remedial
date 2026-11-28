from django.db import migrations


def assign_system_administrator(apps, schema_editor):
    User = apps.get_model("users", "User")
    User.objects.filter(is_superuser=True).exclude(
        role="SYSTEM_ADMINISTRATOR"
    ).update(role="SYSTEM_ADMINISTRATOR")
    # Staff (non-superuser) users also get the role so the bootstrap operator
    # that maintains core-mirrored data through the admin UI is not locked out.
    User.objects.filter(is_staff=True).exclude(role="SYSTEM_ADMINISTRATOR").update(
        role="SYSTEM_ADMINISTRATOR"
    )


def restore_previous_roles(apps, schema_editor):
    User = apps.get_model("users", "User")
    # Roll back only the users this migration seeded; the role choice is
    # additive so the schema migration is fully reversible.
    # Historical models carry no Role inner class; use the literal default.
    User.objects.filter(is_superuser=True).exclude(role="ACCOUNT_OFFICER").update(
        role="ACCOUNT_OFFICER"
    )
    User.objects.filter(is_staff=True).exclude(role="ACCOUNT_OFFICER").update(
        role="ACCOUNT_OFFICER"
    )


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0002_alter_user_role"),
    ]

    operations = [
        migrations.RunPython(assign_system_administrator, restore_previous_roles),
    ]
