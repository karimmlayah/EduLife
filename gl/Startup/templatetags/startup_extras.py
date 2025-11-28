from django import template

register = template.Library()

@register.filter
def split(value, delimiter='/'):
    """Split a string by the given delimiter."""
    if not value:
        return []
    return value.split(delimiter)
@register.filter
def div(value, arg):
    """Divide the value by the arg."""
    try:
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError):
        return 0