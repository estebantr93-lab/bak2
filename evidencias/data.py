from django.contrib.auth.models import User

from actividades.models import Actividad

from .models import Evidencia, Validacion


def build_evidencias():
    verificador = User.objects.get(username='verificador_leia')

    evidencias_data = [
        ('ACT-2026-001', 'EVID-CEN-001', 'aprobada'),
        ('ACT-2026-002', 'EVID-CEN-002', 'pendiente'),
        ('ACT-2026-003', 'EVID-CEN-003', 'rechazada'),
        ('ACT-2026-004', 'EVID-CEN-004', 'pendiente'),
        ('ACT-2026-005', 'EVID-NOR-001', 'aprobada'),
        ('ACT-2026-006', 'EVID-NOR-002', 'pendiente'),
        ('ACT-2026-007', 'EVID-NOR-003', 'rechazada'),
        ('ACT-2026-008', 'EVID-NOR-004', 'pendiente'),
    ]

    evidencias = {}
    for numero_actividad, codigo_unico, estado in evidencias_data:
        actividad = Actividad.objects.get(numero=numero_actividad)
        evidencia, _ = Evidencia.objects.get_or_create(
            codigo_unico=codigo_unico,
            defaults={
                'actividad': actividad,
                'descripcion': f'Evidencia asociada a {actividad.numero}.',
                'estado': estado,
                'revisada_por': verificador if estado in ('aprobada', 'rechazada') else None,
            },
        )
        evidencias[codigo_unico] = evidencia

        if estado in ('aprobada', 'rechazada'):
            Validacion.objects.get_or_create(
                evidencia=evidencia, verificador=verificador,
                defaults={
                    'estado': estado,
                    'comentario': 'Validación registrada durante la carga de datos de demostración.',
                },
            )

    return evidencias
