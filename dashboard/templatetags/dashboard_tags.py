from django import template

register = template.Library()

SEMAFORO_TEXTO = {'green': 'En meta', 'amber': 'En riesgo', 'red': 'Bajo meta'}


@register.filter
def iniciales(nombre):
    """'Ana Pérez (Centro)' → 'AP' (para los avatares)."""
    palabras = [p for p in str(nombre).split() if p[:1].isalpha()]
    return ''.join(p[0] for p in palabras[:2]).upper() or '?'


@register.filter
def semaforo_texto(valor):
    """El semáforo siempre se muestra con texto, nunca solo con color."""
    return SEMAFORO_TEXTO.get(valor, 'Sin meta')


@register.filter
def tope(valor, maximo=100):
    """Limita un porcentaje para anchos de barra (el cumplimiento puede superar el 100 %)."""
    try:
        return min(float(valor), float(maximo))
    except (TypeError, ValueError):
        return 0
