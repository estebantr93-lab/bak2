import datetime

from django.utils import timezone

from .models import Position, Delegation, Parameter, Period, ActivityType


def build_core():
    delegaciones = {}
    for nombre, direccion, telefono in [
        ('Delegación Centro', 'Av. Francisco de Aguirre 100, La Serena', '+56512345601'),
        ('Delegación Norte', 'Av. Balmaceda 2200, La Serena', '+56512345602'),
    ]:
        delegacion, _ = Delegation.objects.get_or_create(
            name=nombre, defaults={'address': direccion, 'phone': telefono},
        )
        delegaciones[nombre] = delegacion

    cargos = {}
    for nombre, area, descripcion in [
        ('Encargado de Atención Ciudadana', 'Atención al público', 'Recepción y gestión de solicitudes ciudadanas.'),
        ('Encargado Social', 'Bienestar social', 'Gestión de casos y atenciones sociales.'),
        ('Coordinador de Delegación', 'Jefatura', 'Coordinación general de la delegación.'),
        ('Verificador de Evidencias', 'Control de gestión', 'Revisión y validación de evidencias de actividades.'),
    ]:
        cargo, _ = Position.objects.get_or_create(
            name=nombre, defaults={'area': area, 'description': descripcion},
        )
        cargos[nombre] = cargo

    tipos = {}
    for codigo, nombre, categoria, subtipo in [
        ('ATC-01', 'Atención ciudadana', 'service', ''),
        ('TRA-02', 'Trámites', 'paperwork', ''),
        ('OPE-03', 'Operativo en terreno', 'field_work', ''),
        ('SOC-04', 'Atención social', 'social', ''),
        ('COM-05', 'Actividad comunitaria', 'field_work', 'Comunitario'),
    ]:
        tipo, _ = ActivityType.objects.get_or_create(
            code=codigo, defaults={'name': nombre, 'category': categoria, 'subtype': subtipo},
        )
        tipos[codigo] = tipo

    # Períodos relativos a la fecha de la carga, así la demo funciona el día que se presente:
    # el actual va de 3 meses atrás a 2 meses adelante (hoy queda dentro) y el cerrado son los 6 meses
    # anteriores. Si ya hay períodos (una carga anterior), se conservan: repetir la carga no los duplica.
    if not Period.objects.exists():
        (inicio_cerrado, fin_cerrado), (inicio_actual, fin_actual) = rangos_de_periodos(timezone.localdate())
        for inicio, termino, cerrado in [(inicio_cerrado, fin_cerrado, True), (inicio_actual, fin_actual, False)]:
            Period.objects.create(
                name=f'{nombre_de_rango(inicio, termino)} ({"cerrado" if cerrado else "actual"})',
                start_date=inicio, end_date=termino, is_closed=cerrado, min_threshold=80, max_cap=100,
            )
    periodos = {p.name: p for p in Period.objects.all()}

    for clave, valor, descripcion in [
        ('TOPE_MAXIMO', '100', 'Tope máximo de cumplimiento por ítem (RN-005); el vigente es el de cada período.'),
        ('UMBRAL_MINIMO', '80', 'Umbral mínimo colectivo de cumplimiento (RN-006).'),
        ('AJUSTE_FELICITACION', '10', 'Ajuste porcentual por felicitación ciudadana (RN-011).'),
        ('AJUSTE_RECLAMO', '-20', 'Ajuste porcentual por reclamo ciudadano (RN-011).'),
    ]:
        Parameter.objects.get_or_create(
            key=clave, defaults={'value': valor, 'description': descripcion, 'is_active': True},
        )

    return {'delegaciones': delegaciones, 'cargos': cargos, 'tipos': tipos, 'periodos': periodos}


MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']


def _primer_dia_del_mes(fecha, desplazamiento):
    indice = fecha.year * 12 + fecha.month - 1 + desplazamiento
    return datetime.date(indice // 12, indice % 12 + 1, 1)


def rangos_de_periodos(hoy):
    """((inicio, fin) del período cerrado, (inicio, fin) del actual) alrededor de hoy."""
    inicio_actual = _primer_dia_del_mes(hoy, -3)
    fin_actual = _primer_dia_del_mes(hoy, 3) - datetime.timedelta(days=1)
    inicio_cerrado = _primer_dia_del_mes(hoy, -9)
    return (inicio_cerrado, inicio_actual - datetime.timedelta(days=1)), (inicio_actual, fin_actual)


def nombre_de_rango(inicio, termino):
    """«jun–nov 2026» o, si cruza de año, «oct 2025–mar 2026»."""
    desde = MESES[inicio.month - 1] + ('' if inicio.year == termino.year else f' {inicio.year}')
    return f'{desde}–{MESES[termino.month - 1]} {termino.year}'


def periodo_actual():
    return Period.objects.filter(is_closed=False).order_by('-start_date').first()


def periodo_cerrado():
    return Period.objects.filter(is_closed=True).order_by('-start_date').first()
