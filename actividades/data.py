import datetime

from django.utils import timezone

from core.data import periodo_actual as obtener_periodo_actual
from core.models import ActivityType
from funcionarios.models import Employee

from .models import Activity, SocialCase


def build_actividades():
    periodo_actual = obtener_periodo_actual()
    # Fecha de ejemplo dentro del período actual y no futura.
    fecha_base = min(periodo_actual.start_date + datetime.timedelta(days=40), timezone.localdate())
    func_centro = Employee.objects.get(name='Ana Pérez (Centro)')
    func_norte = Employee.objects.get(name='Carlos Rojas (Norte)')

    tipo_atc = ActivityType.objects.get(code='ATC-01')
    tipo_tra = ActivityType.objects.get(code='TRA-02')
    tipo_ope = ActivityType.objects.get(code='OPE-03')
    tipo_soc = ActivityType.objects.get(code='SOC-04')

    actividades_data = [
        ('ACT-2026-001', func_centro, tipo_atc, 'approved', 'EVID-CEN-001',
         'Atención de solicitud de certificado de residencia.'),
        ('ACT-2026-002', func_centro, tipo_tra, 'pending', 'EVID-CEN-002',
         'Tramitación de postulación a subsidio municipal.'),
        ('ACT-2026-003', func_centro, tipo_ope, 'rejected', 'EVID-CEN-003',
         'Operativo de terreno en sector Las Compañías.'),
        ('ACT-2026-004', func_centro, tipo_soc, 'pending', 'EVID-CEN-004',
         'Atención social por situación de vulnerabilidad.'),
        ('ACT-2026-005', func_norte, tipo_atc, 'approved', 'EVID-NOR-001',
         'Atención de consulta sobre pago de patentes.'),
        ('ACT-2026-006', func_norte, tipo_tra, 'pending', 'EVID-NOR-002',
         'Tramitación de permiso de circulación.'),
        ('ACT-2026-007', func_norte, tipo_ope, 'rejected', 'EVID-NOR-003',
         'Operativo de terreno en sector El Milagro.'),
        ('ACT-2026-008', func_norte, tipo_soc, 'pending', 'EVID-NOR-004',
         'Atención social por corte de suministro básico.'),
    ]

    actividades = {}
    for numero, funcionario, tipo, estado, codigo_evidencia, descripcion in actividades_data:
        actividad, _ = Activity.all_objects.get_or_create(
            number=numero,
            defaults={
                'employee': funcionario,
                'delegation': funcionario.delegation,
                'period': periodo_actual,
                'activity_type': tipo,
                'date': fecha_base,
                'description': descripcion,
                'contact': 'Vecino/a de la delegación',
                'phone': '+56900000000',
                'evidence_code': codigo_evidencia,
                'validation_status': estado,
            },
        )
        actividades[numero] = actividad

    SocialCase.all_objects.get_or_create(
        activity=actividades['ACT-2026-004'], step_number=1,
        defaults={'description': 'Primera gestión: diagnóstico social y derivación a beneficio municipal.',
                  'date': fecha_base, 'result': 'Derivado a programa municipal'},
    )
    SocialCase.all_objects.get_or_create(
        activity=actividades['ACT-2026-008'], step_number=1,
        defaults={'description': 'Primera gestión: coordinación con empresa sanitaria para restablecer servicio.',
                  'date': fecha_base, 'result': 'En seguimiento'},
    )

    return actividades
