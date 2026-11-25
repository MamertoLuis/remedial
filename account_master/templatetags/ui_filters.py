"""ui-workspace template filters: money and number formatting.

- ``peso``: ₱ with thousands separators and two decimals (tables/details).
- ``peso_compact``: abbreviated KPI form (₱53.7M); pair with the full
  ``|peso`` figure in a ``title`` attribute via kpi_tile.
"""
from django import template

register = template.Library()


@register.filter
def peso(value):
    """Format a number as ₱1,234,567.89."""
    try:
        return "₱{:,.2f}".format(float(value))
    except (TypeError, ValueError):
        return value


@register.filter
def peso_compact(value):
    """Abbreviate a money figure: ₱53.7M, ₱1.2B, ₱950K, else ₱950.00."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return value
    sign = "-" if v < 0 else ""
    v = abs(v)
    if v >= 1_000_000_000:
        return "{sign}₱{amount:.1f}B".format(sign=sign, amount=v / 1_000_000_000)
    if v >= 1_000_000:
        return "{sign}₱{amount:.1f}M".format(sign=sign, amount=v / 1_000_000)
    if v >= 1_000:
        return "{sign}₱{amount:.1f}K".format(sign=sign, amount=v / 1_000)
    return "{sign}₱{amount:,.2f}".format(sign=sign, amount=v)
