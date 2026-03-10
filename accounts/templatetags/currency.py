from django import template


register = template.Library()


@register.filter(name='vnd')
def vnd(value):
    try:
        amount = int(value or 0)
    except (TypeError, ValueError):
        return '0'
    return f'{amount:,}'.replace(',', '.')
