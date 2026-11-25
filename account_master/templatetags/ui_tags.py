"""ui-workspace template tags: status→chip mapping and table helpers.

The status→chip mapping is the SINGLE source of truth for chip styling.
Every status value from the model choice lists maps to a severity; the
`status_chip_class` tag returns the Tailwind pill classes.
"""
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

# Severity by status value. Covers every value in the project's choice lists:
# LoanAccount.LOAN_STATUS_CHOICES, DelinquencyStatus.CLASSIFICATION_CHOICES,
# Alert.AlertType, RemedialStrategy.StrategyStatus, CompromiseStatus,
# CompromiseInstallment.InstallmentStatus, EscalationState.Status.
STATUS_SEVERITY = {
    # Loan status
    "PERFORMING": "ok",
    "PAST_DUE": "watch",
    "NPL": "critical",
    "WRITEOFF": "neutral",
    "CLOSED": "neutral",
    # Classification (DelinquencyStatus)
    "C": "ok",
    "SM": "watch",
    "SS": "watch",
    "D": "critical",
    "L": "critical",
    # Alert type
    "CRITICAL": "critical",
    "WARNING": "watch",
    "INFO": "neutral",
    "SUCCESS": "ok",
    # Remedial strategy status
    "ACTIVE": "ok",
    "COMPLETED": "neutral",
    "CANCELLED": "neutral",
    # Compromise agreement status
    "RESCINDED": "critical",
    "SUPERSEDED": "neutral",
    # Compromise installment status
    "PAID": "ok",
    "UNPAID": "watch",
    # Escalation state status
    "PENDING": "watch",
    "PAUSED": "watch",
    "CLOSED_ESC": "neutral",
    # Alert status
    "NEW": "watch",
    "ACKNOWLEDGED": "neutral",
    "RESOLVED": "ok",
    "DISMISSED": "neutral",
    # Alert severity
    "HIGH": "critical",
    "MEDIUM": "watch",
    "LOW": "neutral",
}

CHIP_CLASSES = {
    "ok": "chip chip-ok",
    "watch": "chip chip-watch",
    "critical": "chip chip-critical",
    "neutral": "chip chip-neutral",
}


@register.filter
def status_severity(value):
    """Map a status value to its severity (ok/watch/critical/neutral)."""
    if value is None:
        return "neutral"
    return STATUS_SEVERITY.get(str(value).upper(), "neutral")


@register.simple_tag
def status_chip_class(value):
    """Return the chip CSS classes for a status value."""
    return CHIP_CLASSES[status_severity(value)]


@register.filter
def row_cell(row, column_name):
    """Render one cell value from a django-tables2 BoundRow by column name.

    Used by the data_table details-expansion row so a row's cells can be
    rendered twice (visible columns + collapsed <details>).
    """
    try:
        return row.get_cell(column_name)
    except Exception:
        return ""


@register.tag
class Capture(template.Node):
    """Capture a block's rendered output into a context variable.

    Usage::

        {% capture as filter_fields %}
          <select name="status">...</select>
        {% endcapture %}
        {% include 'partials/filter_bar.html' with filter_fields=filter_fields|safe %}
    """

    def __init__(self, nodelist, var_name):
        self.nodelist = nodelist
        self.var_name = var_name

    def render(self, context):
        output = self.nodelist.render(context)
        context[self.var_name] = output
        return ""


@register.filter
def with_describedby(field):
    """Render a form field widget with an ``aria-describedby`` attribute
    pointing at its help-text and error spans (when they exist).
    """
    field_id = field.id_for_label
    parts = []
    if field.help_text:
        parts.append("{}-help".format(field_id))
    if field.errors:
        parts.append("{}-error".format(field_id))
    attrs = {}
    if parts:
        attrs["aria-describedby"] = " ".join(parts)
    return mark_safe(field.as_widget(attrs=attrs))


@register.simple_tag(takes_context=True)
def query_url(context, page_number):
    """Build the current URL query string with ``page`` replaced, preserving
    every other GET parameter (filter values).
    """
    request = context.get("request")
    params = []
    if request is not None:
        for key, value in request.GET.items():
            if key != "page":
                params.append("{}={}".format(key, value))
    params.append("page={}".format(page_number))
    return "?" + "&".join(params)


@register.tag(name="capture")
def do_capture(parser, token):
    bits = token.split_contents()
    if len(bits) != 3 or bits[1] != "as":
        raise template.TemplateSyntaxError(
            "capture requires: {% capture as variable_name %}...{% endcapture %}"
        )
    nodelist = parser.parse(("endcapture",))
    parser.delete_first_token()
    return Capture(nodelist, bits[2])
