from django import template

register = template.Library()

@register.filter(name='comma_decimal')
def comma_decimal(value):
    if value is None:
        return ''
    try:
        return str(value).replace('.', ',')
    except Exception:
        return value
