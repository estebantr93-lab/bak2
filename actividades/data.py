import datetime

from core.models import Periodo, TipoActividad
from funcionarios.models import Funcionario

from .models import Actividad, AtencionSocial

FECHA_BASE = datetime.date(2026, 7, 10)


def build_actividades():
    periodo_actual = Periodo.objects.get(nombre='2026-S2 (actual)')
    func_centro = Funcionario.objects.get(nombre='Ana Pérez (Centro)')
    func_norte = Funcionario.objects.get(nombre='Carlos Rojas (Norte)')

    tipo_atc = TipoActividad.objects.get(codigo='ATC-01')
    tipo_tra = TipoActividad.objects.get(codigo='TRA-02')
    tipo_ope = TipoActividad.objects.get(codigo='OPE-03')
    tipo_soc = TipoActividad.objects.get(codigo='SOC-04')

    actividades_data = [
        ('ACT-2026-001', func_centro, tipo_atc, 'aprobada', 'EVID-CEN-001',
         'Atención de solicitud de certificado de residencia.'),
        ('ACT-2026-002', func_centro, tipo_tra, 'pendiente', 'EVID-CEN-002',
         'Tramitación de postulación a subsidio municipal.'),
        ('ACT-2026-003', func_centro, tipo_ope, 'rechazada', 'EVID-CEN-003',
         'Operativo de terreno en sector Las Compañías.'),
        ('ACT-2026-004', func_centro, tipo_soc, 'pendiente', 'EVID-CEN-004',
         'Atención social por situación de vulnerabilidad.'),
        ('ACT-2026-005', func_norte, tipo_atc, 'aprobada', 'EVID-NOR-001',
         'Atención de consulta sobre pago de patentes.'),
        ('ACT-2026-006', func_norte, tipo_tra, 'pendiente', 'EVID-NOR-002',
         'Tramitación de permiso de circulación.'),
        ('ACT-2026-007', func_norte, tipo_ope, 'rechazada', 'EVID-NOR-003',
         'Operativo de terreno en sector El Milagro.'),
        ('ACT-2026-008', func_norte, tipo_soc, 'pendiente', 'EVID-NOR-004',
         'Atención social por corte de suministro básico.'),
    ]

    actividades = {}
    for numero, funcionario, tipo, estado, codigo_evidencia, descripcion in actividades_data:
        actividad, _ = Actividad.objects.get_or_create(
            numero=numero,
            defaults={
                'funcionario': funcionario,
                'delegacion': funcionario.delegacion,
                'periodo': periodo_actual,
                'tipo_actividad': tipo,
                'fecha': FECHA_BASE,
                'descripcion': descripcion,
                'contacto': 'Vecino/a de la delegación',
                'telefono': '+56900000000',
                'codigo_evidencia': codigo_evidencia,
                'estado_validacion': estado,
            },
        )
        actividades[numero] = actividad

    AtencionSocial.objects.get_or_create(
        actividad=actividades['ACT-2026-004'], numero_gestion=1,
        defaults={'descripcion': 'Primera gestión: diagnóstico social y derivación a beneficio municipal.'},
    )
    AtencionSocial.objects.get_or_create(
        actividad=actividades['ACT-2026-008'], numero_gestion=1,
        defaults={'descripcion': 'Primera gestión: coordinación con empresa sanitaria para restablecer servicio.'},
    )

    return actividades
