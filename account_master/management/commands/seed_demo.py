"""Provision a complete fake demo database in one run.

Seeds deterministic role users, the foundational portfolio (``load_dummy_data``),
a cascade-driven exposure timeline per account, and the enrichment layers
(collection activities, remedial strategies, compromise agreements). Refuses
to run when the database holds organic (non-demo) exposure or delinquency
rows. See specs/demo-data/spec.md.
"""

import random

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from account_master.models import LoanAccount
from account_master.services import demo_seed


class Command(BaseCommand):
    help = (
        "Provision a complete fake demo database: role users, portfolio, and "
        "cascade-driven timelines. Refuses to run on databases with real data."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--seed",
            type=int,
            default=None,
            help="Integer seed for reproducible generated values (open-play variety without it).",
        )

    def handle(self, *args, **options):
        seed = options["seed"]

        # The organic-data boundary runs before any write.
        demo_seed.ensure_organic_free()

        self.stdout.write("Seeding demo role users...")
        demo_seed.seed_users()

        self.stdout.write("Loading foundational portfolio (borrowers/accounts)...")
        call_command("load_dummy_data")

        self.stdout.write("Purging previous demo state...")
        demo_seed.prepare_demo_accounts()

        accounts = list(
            LoanAccount.objects.filter(loan_id__in=demo_seed.DEMO_ACCOUNT_IDS).order_by(
                "loan_id"
            )
        )
        if len(accounts) != len(demo_seed.DEMO_ACCOUNT_IDS):
            raise CommandError(
                "Not all demo accounts were created by load_dummy_data; "
                "run it on an empty database."
            )

        rng = random.Random(seed)
        self.stdout.write("Writing cascade-driven exposure timelines...")
        demo_seed.run_timeline(accounts, rng)

        self.stdout.write("Seeding the litigation narrative...")
        demo_seed.seed_litigation(accounts)

        # Enrichment loaders draw on the module-level random; re-seed so a
        # seeded run reproduces them too.
        if seed is not None:
            random.seed(seed)
        self.stdout.write("Seeding collection activities...")
        call_command("load_dummy_collection_activities")
        if seed is not None:
            random.seed(seed)
        self.stdout.write("Seeding remedial strategies...")
        call_command("load_dummy_remedial_strategies")
        if seed is not None:
            random.seed(seed)
        self.stdout.write("Seeding compromise agreements...")
        call_command("load_dummy_compromise")

        self.stdout.write(
            self.style.SUCCESS(
                "\nDemo database seeded. Logins: demo-officer / demo-manager / "
                "demo-board / admin (password: demo-password-123). "
                "This database must never receive real imports."
            )
        )