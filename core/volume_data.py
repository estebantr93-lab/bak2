"""Carga de volumen (>= 1.000 registros de negocio) para probar relaciones, permisos y paginación.

Reproducible: usa random.Random con semilla fija, así cada ejecución genera exactamente los
mismos datos. Idempotente: si ya existen registros con prefijo VOL- no vuelve a cargarlos.
Usa bulk_create por rendimiento (evita miles de INSERT individuales).
"""
import datetime
import random

from django.contrib.auth.models import Group, User

from actividades.models import Activity, SocialCase
from agenda.models import Commitment, CommitmentFollowUp
from core.models import ActivityType, Delegation, Period, Position
from evidencias.models import Evidence
from funcionarios.models import Employee

PREFIJO = 'VOL-'
SEMILLA = 2026

NOMBRES = ['Camila', 'Diego', 'Valentina', 'Matías', 'Fernanda', 'Tomás', 'Javiera', 'Benjamín', 'Catalina',
           'Joaquín', 'Antonia', 'Sebastián', 'Isidora', 'Nicolás', 'Florencia', 'Vicente']
APELLIDOS = ['González', 'Muñoz', 'Rojas', 'Díaz', 'Pérez', 'Soto', 'Contreras', 'Silva', 'Martínez', 'Sepúlveda']
SECTORES = ['Las Compañías', 'La Florida', 'El Milagro', 'Antena', 'San Joaquín', 'Pampa', 'Centro histórico']
ACCIONES = ['Orientación y derivación', 'Recepción de documentos', 'Visita domiciliaria',
            'Coordinación con departamento municipal', 'Registro en sistema', 'Entrega de formulario']
TEMAS_COMPROMISO = ['Mantención de áreas verdes', 'Reparación de luminarias', 'Limpieza de microbasural',
                    'Operativo de salud', 'Reunión con junta de vecinos', 'Catastro de organizaciones',
                    'Señalética vial', 'Taller comunitario']


def ya_cargado():
    return Activity.all_objects.filter(number__startswith=PREFIJO).exists()


def _fecha_en(rng, periodo):
    dias = (periodo.end_date - periodo.start_date).days
    return periodo.start_date + datetime.timedelta(days=rng.randint(0, dias))


def build_volumen(total_actividades=500):
    """Genera ~2,2 registros de negocio por actividad (>= 1.000 con el valor por defecto)."""
    if ya_cargado():
        return None
    rng = random.Random(SEMILLA)
    delegaciones = list(Delegation.objects.order_by('pk'))
    cargos = list(Position.objects.exclude(name='Coordinador de Delegación').order_by('pk'))
    tipos = list(ActivityType.objects.filter(is_active=True).order_by('pk'))
    periodos = list(Period.objects.order_by('start_date'))
    grupo_funcionarios = Group.objects.get(name='Funcionarios')

    # 1) Funcionarios adicionales (8 por delegación). Sin contraseña utilizable: son datos, no cuentas de acceso.
    usuarios = []
    for i in range(8 * len(delegaciones)):
        user = User(username=f'vol_funcionario_{i + 1:02d}', email=f'vol{i + 1:02d}@demo.sgr.local')
        user.set_unusable_password()
        usuarios.append(user)
    User.objects.bulk_create(usuarios)
    usuarios = list(User.objects.filter(username__startswith='vol_funcionario_').order_by('username'))
    grupo_funcionarios.user_set.add(*usuarios)
    empleados = Employee.objects.bulk_create([
        Employee(
            user=user, delegation=delegaciones[i % len(delegaciones)], position=rng.choice(cargos),
            name=f'{rng.choice(NOMBRES)} {rng.choice(APELLIDOS)} {rng.choice(APELLIDOS)}',
        )
        for i, user in enumerate(usuarios)
    ])
    empleados = list(Employee.objects.filter(user__username__startswith='vol_funcionario_').select_related('delegation'))

    # 2) Actividades repartidas entre funcionarios, tipos y períodos.
    estados = ['pending'] * 5 + ['approved'] * 4 + ['rejected']
    actividades = []
    for n in range(1, total_actividades + 1):
        empleado = rng.choice(empleados)
        periodo = rng.choice(periodos)
        actividades.append(Activity(
            number=f'{PREFIJO}{n:05d}', employee=empleado, delegation=empleado.delegation, period=periodo,
            activity_type=rng.choice(tipos), date=_fecha_en(rng, periodo),
            description=f'{rng.choice(ACCIONES)} en sector {rng.choice(SECTORES)}.',
            action=rng.choice(ACCIONES), contact=f'Vecino/a {rng.choice(APELLIDOS)}',
            phone=f'+569{rng.randint(10000000, 99999999)}', is_agenda_item=rng.random() < 0.2,
            evidence_code=f'EV-{PREFIJO}{n:05d}', validation_status=rng.choice(estados),
        ))
    Activity.objects.bulk_create(actividades, batch_size=500)
    actividades = list(Activity.objects.filter(number__startswith=PREFIJO).select_related('activity_type'))

    # 3) Evidencias (60 % de las actividades) con el mismo estado de validación.
    evidencias = [
        Evidence(
            unique_code=f'EVI-{PREFIJO}{a.pk:06d}', activity=a, status=a.validation_status,
            description=f'Respaldo de {a.number}',
        )
        for a in actividades if rng.random() < 0.6
    ]
    Evidence.objects.bulk_create(evidencias, batch_size=500)

    # 4) Gestiones de atención social (1 a 3) para las actividades de tipo social.
    gestiones = []
    for a in actividades:
        if a.activity_type.category == 'social':
            for paso in range(1, rng.randint(1, 3) + 1):
                gestiones.append(SocialCase(activity=a, step_number=paso,
                                            description=f'Gestión {paso}: {rng.choice(ACCIONES).lower()}.'))
    SocialCase.objects.bulk_create(gestiones, batch_size=500)

    # 5) Compromisos y sus seguimientos.
    estados_compromiso = ['registered', 'pending', 'in_progress', 'done']
    compromisos = []
    for n in range(1, total_actividades // 4 + 1):
        empleado = rng.choice(empleados)
        estado = rng.choice(estados_compromiso)
        compromisos.append(Commitment(
            title=f'{PREFIJO}{n:04d} {rng.choice(TEMAS_COMPROMISO)} ({rng.choice(SECTORES)})',
            delegation=empleado.delegation, responsible=empleado, status=estado,
            due_date=datetime.date(2026, 6, 1) + datetime.timedelta(days=rng.randint(0, 240)),
            notes='Cerrado con informe de terreno.' if estado == 'done' else '',
        ))
    Commitment.objects.bulk_create(compromisos, batch_size=500)
    compromisos = list(Commitment.objects.filter(title__startswith=PREFIJO))
    seguimientos = [
        CommitmentFollowUp(commitment=c, responsible=c.responsible, new_status=c.status,
                           description=f'Avance registrado para «{c.title[:40]}».')
        for c in compromisos for _ in range(rng.randint(0, 2))
    ]
    CommitmentFollowUp.objects.bulk_create(seguimientos, batch_size=500)

    return {
        'Funcionarios': len(empleados), 'Actividades': len(actividades), 'Evidencias': len(evidencias),
        'Atenciones sociales': len(gestiones), 'Compromisos': len(compromisos), 'Seguimientos': len(seguimientos),
    }
