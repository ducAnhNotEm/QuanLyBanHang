from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def format_vnd(value):
    try:
        amount = int(Decimal(value))
    except (TypeError, ValueError, InvalidOperation):
        return ''

    return f"{amount:,}".replace(',', '.') + " VND"
