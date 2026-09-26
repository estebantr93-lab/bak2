import datetime

from .models import Cargo, Delegacion, Parametro, Periodo, TipoActividad


def build_core():
    delegaciones = {}
    for nombre, direccion, telefono in [
        ('Delegación Centro', 'Av. Francisco de Aguirre 100, La Serena', '+56512345601'),
        ('Delegación Norte', 'Av. Balmaceda 2200, La Serena', '+56512345602'),
    ]:
        delegacion, _ = Delegacion.objects.get_or_create(
            nombre=nombre, defaults={'direccion': direccion, 'telefono': telefono},
        )
        delegaciones[nombre] = delegacion

    cargos = {}
    for nombre, area, descripcion in [
        ('Encargado de Atención Ciudadana', 'Atención al público', 'Recepción y gestión de solicitudes ciudadanas.'),
        ('Encargado Social', 'Bienestar social', 'Gestión de casos y atenciones sociales.'),
        ('Coordinador de Delegación', 'Jefatura', 'Coordinación general de la delegación.'),
        ('Verificador de Evidencias', 'Control de gestión', 'Revisión y validación de evidencias de actividades.'),
    ]:
        cargo, _ = Cargo.objects.get_or_create(
            nombre=nombre, defaults={'area': area, 'descripcion': descripcion},
        )
        cargos[nombre] = cargo

    tipos = {}
    for codigo, nombre, categoria, subtipo in [
        ('ATC-01', 'Atención ciudadana', 'atencion', ''),
        ('TRA-02', 'Trámites', 'tramitacion', ''),
        ('OPE-03', 'Operativo en terreno', 'operativo', ''),
        ('SOC-04', 'Atención social', 'social', ''),
        ('COM-05', 'Actividad comunitaria', 'operativo', 'Comunitario'),
    ]:
        tipo, _ = TipoActividad.objects.get_or_create(
            codigo=codigo, defaults={'nombre': nombre, 'categoria': categoria, 'subtipo': subtipo},
        )
        tipos[codigo] = tipo

    periodos = {}
    for nombre, inicio, termino, cerrado in [
        ('2026-Q1 (cerrado)', datetime.date(2026, 1, 1), datetime.date(2026, 3, 31), True),
        ('2026-S2 (actual)', datetime.date(2026, 6, 1), datetime.date(2026, 9, 30), False),
    ]:
        periodo, _ = Periodo.objects.get_or_create(
            nombre=nombre, defaults={
                'fecha_inicio': inicio, 'fecha_termino': termino, 'cerrado': cerrado,
                'umbral_minimo': 80, 'tope_maximo': 150,
            },
        )
        periodos[nombre] = periodo

    for clave, valor, descripcion in [
        ('TOPE_MAXIMO', '150', 'Tope máximo de cumplimiento ponderado (RN-005).'),
        ('UMBRAL_MINIMO', '80', 'Umbral mínimo colectivo de cumplimiento (RN-006).'),
        ('AJUSTE_FELICITACION', '10', 'Ajuste porcentual por felicitación ciudadana (RN-011).'),
        ('AJUSTE_RECLAMO', '-20', 'Ajuste porcentual por reclamo ciudadano (RN-011).'),
    ]:
        Parametro.objects.get_or_create(
            clave=clave, defaults={'valor': valor, 'descripcion': descripcion, 'vigente': True},
        )

    return {'delegaciones': delegaciones, 'cargos': cargos, 'tipos': tipos, 'periodos': periodos}
