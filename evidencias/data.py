from django.contrib.auth.models import User

from actividades.models import Activity

from .models import Evidence, Validation


def build_evidencias():
    verificador = User.objects.get(username='verificador_leia')

    evidencias_data = [
        ('ACT-2026-001', 'EVID-CEN-001', 'approved'),
        ('ACT-2026-002', 'EVID-CEN-002', 'pending'),
        ('ACT-2026-003', 'EVID-CEN-003', 'rejected'),
        ('ACT-2026-004', 'EVID-CEN-004', 'pending'),
        ('ACT-2026-005', 'EVID-NOR-001', 'approved'),
        ('ACT-2026-006', 'EVID-NOR-002', 'pending'),
        ('ACT-2026-007', 'EVID-NOR-003', 'rejected'),
        ('ACT-2026-008', 'EVID-NOR-004', 'pending'),
    ]

    evidencias = {}
    for numero_actividad, codigo_unico, estado in evidencias_data:
        actividad = Activity.objects.get(number=numero_actividad)
        evidencia, _ = Evidence.all_objects.get_or_create(
            unique_code=codigo_unico,
            defaults={
                'activity': actividad,
                'description': f'Evidencia asociada a {actividad.number}.',
                'status': estado,
                'reviewed_by': verificador if estado in ('approved', 'rejected') else None,
            },
        )
        evidencias[codigo_unico] = evidencia

        if estado in ('approved', 'rejected'):
            Validation.objects.get_or_create(
                evidence=evidencia, reviewer=verificador,
                defaults={
                    'status': estado,
                    'comment': 'Validación registrada durante la carga de datos de demostración.',
                },
            )

    return evidencias
