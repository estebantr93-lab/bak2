from django import template
from django.forms import CheckboxInput, FileInput, RadioSelect, Select, SelectMultiple

register = template.Library()


@register.filter
def bootstrap(field):
    """Renderiza el widget de un campo con la clase Bootstrap que le corresponde."""
    widget = field.field.widget
    if isinstance(widget, CheckboxInput):
        clase = 'form-check-input'
    elif isinstance(widget, (Select, SelectMultiple)) and not isinstance(widget, RadioSelect):
        clase = 'form-select'
    elif isinstance(widget, FileInput):
        clase = 'form-control'
    else:
        clase = 'form-control'
    if field.errors:
        clase += ' is-invalid'
    existentes = widget.attrs.get('class', '')
    return field.as_widget(attrs={'class': f'{existentes} {clase}'.strip()})
