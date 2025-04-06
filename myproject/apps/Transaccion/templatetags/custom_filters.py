from django import template # Importa el sistema de plantillas de Django para registrar filtros personalizados

register = template.Library()

@register.filter
def split(value, delimiter=' '):
    """Divide un string usando el delimitador dado."""
    return value.split(delimiter)
