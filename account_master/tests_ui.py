"""ui-workspace tests: money filters, status→chip mapping, and shared partials."""
from django.test import TestCase
from django.template import Context, Template, engines

from account_master.templatetags.ui_filters import peso, peso_compact
from account_master.templatetags.ui_tags import STATUS_SEVERITY, status_severity

from django_tables2 import Table, Column


def render(template_string, context=None):
    t = Template(template_string)
    return t.render(Context(context or {}))


class PesoFilterTests(TestCase):
    def test_thousands_and_decimals(self):
        self.assertEqual(peso(1234567.891), "₱1,234,567.89")

    def test_zero(self):
        self.assertEqual(peso(0), "₱0.00")

    def test_integer_input(self):
        self.assertEqual(peso(500), "₱500.00")

    def test_none_passthrough(self):
        self.assertIsNone(peso(None))

    def test_non_numeric_passthrough(self):
        self.assertEqual(peso("n/a"), "n/a")


class PesoCompactFilterTests(TestCase):
    def test_millions(self):
        self.assertEqual(peso_compact(53700000), "₱53.7M")

    def test_billions(self):
        self.assertEqual(peso_compact(1200000000), "₱1.2B")

    def test_thousands(self):
        self.assertEqual(peso_compact(950000), "₱950.0K")

    def test_small_values(self):
        self.assertEqual(peso_compact(950), "₱950.00")

    def test_negative(self):
        self.assertEqual(peso_compact(-2500000), "-₱2.5M")

    def test_none_passthrough(self):
        self.assertIsNone(peso_compact(None))


class StatusChipMappingTests(TestCase):
    def test_every_choice_value_is_mapped(self):
        # Every value from the project's model choice lists must map to a
        # severity (and therefore a chip style). Add new statuses here.
        choice_values = [
            # LoanAccount.LOAN_STATUS_CHOICES
            "PERFORMING", "PAST_DUE", "NPL", "WRITEOFF", "CLOSED",
            # DelinquencyStatus.CLASSIFICATION_CHOICES
            "C", "SM", "SS", "D", "L",
            # Alert.AlertType
            "CRITICAL", "WARNING", "INFO", "SUCCESS",
            # RemedialStrategy.StrategyStatus
            "ACTIVE", "COMPLETED", "CANCELLED",
            # CompromiseAgreement.CompromiseStatus
            "RESCINDED", "SUPERSEDED",
            # CompromiseInstallment.InstallmentStatus
            "PAID", "UNPAID",
            # EscalationState.Status
            "PENDING", "PAUSED",
        ]
        for value in choice_values:
            with self.subTest(value=value):
                self.assertIn(
                    value, STATUS_SEVERITY,
                    f"status value {value} is missing from the chip mapping",
                )

    def test_severity_mapping(self):
        self.assertEqual(status_severity("NPL"), "critical")
        self.assertEqual(status_severity("PAST_DUE"), "watch")
        self.assertEqual(status_severity("PERFORMING"), "ok")
        self.assertEqual(status_severity("CLOSED"), "neutral")
        self.assertEqual(status_severity("unknown-value"), "neutral")
        self.assertEqual(status_severity(None), "neutral")
        # case-insensitive
        self.assertEqual(status_severity("npl"), "critical")

    def test_chip_class_tag(self):
        out = render(
            "{% load ui_tags %}<span class=\"{% status_chip_class 'NPL' %}\">x</span>"
        )
        self.assertIn("chip", out)
        self.assertIn("chip-critical", out)

    def test_chip_partial_renders_label(self):
        out = render(
            "{% include 'partials/status_chip.html' with value='NPL' %}"
        )
        self.assertIn("chip-critical", out)
        self.assertIn("NPL", out)

    def test_chip_partial_human_label_override(self):
        out = render(
            "{% include 'partials/status_chip.html' with value='PAST_DUE' label='Past Due' %}"
        )
        self.assertIn("Past Due", out)


class QueryUrlTagTests(TestCase):
    def test_preserves_filter_params_and_replaces_page(self):
        request = type(
            "Req", (), {"GET": {"status": "NPL", "account_officer": "AO1", "page": "3"}}
        )()
        context = {"request": request}
        out = render(
            "{% load ui_tags %}{% query_url 5 %}", context
        )
        self.assertIn("status=NPL", out)
        self.assertIn("account_officer=AO1", out)
        self.assertIn("page=5", out)
        self.assertNotIn("page=3", out)


class CaptureTagTests(TestCase):
    def test_capture_stores_block_output(self):
        out = render(
            "{% load ui_tags %}"
            "{% capture as fields %}<select name=\"x\"><option>a</option></select>{% endcapture %}"
            "{{ fields }}"
        )
        self.assertIn("<select name=\"x\">", out)


class ComponentRenderTests(TestCase):
    def test_page_header(self):
        out = render(
            "{% include 'partials/page_header.html' with page_title='Borrowers' "
            "record_count=3 primary_action=primary %}",
            {"primary": {"url": "/borrowers/create/", "label": "New Borrower"}},
        )
        self.assertIn("Borrowers", out)
        self.assertIn("3 records", out)
        self.assertIn("New Borrower", out)
        self.assertIn('href="/borrowers/create/"', out)

    def test_empty_state(self):
        out = render(
            "{% include 'partials/empty_state.html' with title='No open alerts' "
            "message='Everything is clear' %}"
        )
        self.assertIn("No open alerts", out)
        self.assertIn("Everything is clear", out)

    def test_kpi_tile_money_title(self):
        out = render(
            "{% load ui_filters %}"
            "{% include 'partials/kpi_tile.html' with label='Total NPL' value=12500000 "
            "severity='critical' is_money=True %}",
        )
        self.assertIn("₱12.5M", out)
        self.assertIn('title="₱12,500,000.00"', out)
        self.assertIn("kpi-critical", out)
        self.assertIn("tabular-nums", out)

    def test_kpi_tile_links_when_url(self):
        out = render(
            "{% include 'partials/kpi_tile.html' with label='Total NPL' value=1 "
            "url='/accounts/?status=NPL' %}"
        )
        self.assertIn('href="/accounts/?status=NPL"', out)
        self.assertIn("kpi-link", out)

    def test_pagination_preserves_filters(self):
        # Build a fake page object with has_other_pages
        class FakePaginator:
            page_range = [1, 2, 3]
            num_pages = 3

        class FakePage:
            number = 2
            paginator = FakePaginator()
            has_previous = True
            has_next = True
            has_other_pages = True
            previous_page_number = 1
            next_page_number = 3

        request = type("Req", (), {"GET": {"status": "NPL"}})()
        out = render(
            "{% load ui_tags %}"
            "{% include 'partials/pagination.html' with page_obj=page hx_target='#table-container' %}",
            {"page": FakePage(), "request": request},
        )
        self.assertIn("Previous", out)
        self.assertIn("Next", out)
        self.assertIn("status=NPL", out)
        self.assertIn('hx-target="#table-container"', out)
        self.assertIn('aria-current="page"', out)

    def test_filter_bar_htmx(self):
        request = type("Req", (), {"path": "/accounts/"})()
        out = render(
            "{% include 'partials/filter_bar.html' with "
            "filter_fields='<select name=\"status\"><option>NPL</option></select>' "
            "clear_url='/accounts/' hx_target='#table-container' %}",
            {"request": request},
        )
        self.assertIn('hx-get="/accounts/"', out)
        self.assertIn('hx-target="#table-container"', out)
        self.assertIn('hx-push-url="true"', out)
        self.assertIn("Clear", out)
        self.assertIn('<select name="status">', out)

    def test_confirm_modal(self):
        out = render(
            "{% include 'partials/confirm_modal.html' with modal_id='del-modal' "
            "title='Delete borrower' message='This cannot be undone' "
            "form_action='/borrower/B001/delete/' confirm_label='Delete' %}"
        )
        self.assertIn('id="del-modal"', out)
        self.assertIn('aria-modal="true"', out)
        self.assertIn('action="/borrower/B001/delete/"', out)
        self.assertIn("Delete borrower", out)
        self.assertIn("This cannot be undone", out)
        self.assertIn("__appModalsWired", out)  # modal wiring script present


class TableOverrideTests(TestCase):
    class SampleTable(Table):
        id = Column()
        name = Column()
        collapse_columns = ["name"]

        class Meta:
            attrs = {"class": "app-table"}

    def test_override_renders_scope_and_class(self):
        table = self.SampleTable([{"id": 1, "name": "A"}])
        request = type("Req", (), {"GET": {}})()
        out = render(
            "{% load django_tables2 %}{% render_table table %}",
            {"table": table, "request": request},
        )
        self.assertIn('class="app-table"', out)
        self.assertIn('scope="col"', out)
        self.assertIn("app-cell-collapse", out)
        self.assertIn("app-row-details", out)
        self.assertIn("<summary>Details</summary>", out)
