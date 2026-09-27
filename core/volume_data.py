"""Carga de volumen (>= 1.000 registros de negocio) para probar relaciones, permisos y paginación.

- Reproducible: random.Random con semilla fija; cada ejecución genera exactamente los mismos datos.
- Idempotente: si ya existen registros con prefijo VOL- no vuelve a cargarlos
  (`borrar_volumen()` los elimina físicamente para regenerarlos).
- Balanceado: la mitad de las actividades para cada delegación. Las cuentas de demostración
  (funcionario_centro, funcionario_norte, admins) reciben un bloque propio, así cada perfil tiene
  datos que mostrar.
- Parte de las evidencias trae un archivo real (PNG o PDF generado), para mostrar la carga en listados.
- Usa bulk_create por rendimiento (evita miles de INSERT individuales).
"""
import datetime
import io
import random

from django.contrib.auth.models import Group, User
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from PIL import Image, ImageDraw

from actividades.models import Activity, SocialCase
from agenda.models import Commitment, CommitmentFollowUp
from core.models import ActivityType, Delegation, Period, Position
from evidencias.models import Evidence, Validation, ruta_evidencia
from funcionarios.models import Employee

PREFIJO = 'VOL-'
SEMILLA = 2026
FUNCIONARIOS_POR_DELEGACION = 8
# Parte de las actividades de cada delegación que se asigna a las cuentas de demostración.
CUOTA_DEMO = {'funcionario_centro': 0.20, 'funcionario_norte': 0.20, 'admin_centro': 0.05, 'admin_norte': 0.05}
CARGOS_OPERATIVOS = ['Encargado de Atención Ciudadana', 'Encargado Social']

NOMBRES = ['Camila', 'Diego', 'Valentina', 'Matías', 'Fernanda', 'Tomás', 'Javiera', 'Benjamín', 'Catalina',
           'Joaquín', 'Antonia', 'Sebastián', 'Isidora', 'Nicolás', 'Florencia', 'Vicente']
APELLIDOS = ['González', 'Muñoz', 'Rojas', 'Díaz', 'Pérez', 'Soto', 'Contreras', 'Silva', 'Martínez', 'Sepúlveda']
SECTORES = {
    'Delegación Centro': ['Centro histórico', 'Las Compañías', 'La Florida', 'San Joaquín'],
    'Delegación Norte': ['El Milagro', 'Antena', 'Pampa', 'Juan XXIII'],
}
ACCIONES = ['Orientación y derivación', 'Recepción de documentos', 'Visita domiciliaria',
            'Coordinación con departamento municipal', 'Registro en sistema', 'Entrega de formulario']
TEMAS_COMPROMISO = ['Mantención de áreas verdes', 'Reparación de luminarias', 'Limpieza de microbasural',
                    'Operativo de salud', 'Reunión con junta de vecinos', 'Catastro de organizaciones',
                    'Señalética vial', 'Taller comunitario']
COLORES = [(173, 0, 0), (109, 1, 1), (179, 61, 0), (25, 135, 84), (13, 110, 253), (108, 117, 125)]


def ya_cargado():
    return Activity.all_objects.filter(number__startswith=PREFIJO).exists()


def borrar_volumen():
    """Elimina físicamente los datos de volumen (y sus archivos) para poder regenerarlos."""
    Evidence.all_objects.filter(activity__number__startswith=PREFIJO).hard_delete()  # post_delete borra archivos
    Activity.all_objects.filter(number__startswith=PREFIJO).hard_delete()
    Commitment.all_objects.filter(title__startswith=PREFIJO).hard_delete()
    Employee.objects.filter(user__username__startswith='vol_funcionario_').delete()
    User.objects.filter(username__startswith='vol_funcionario_').delete()


def _fecha_en(rng, periodo):
    dias = (periodo.end_date - periodo.start_date).days
    return periodo.start_date + datetime.timedelta(days=rng.randint(0, dias))


def _archivo_evidencia(rng, n, texto):
    """Genera un PNG (con Pillow) o un PDF mínimo válido; ambos pasan las validaciones de la app."""
    if n % 3:
        imagen = Image.new('RGB', (320, 200), rng.choice(COLORES))
        dibujo = ImageDraw.Draw(imagen)
        dibujo.rectangle((12, 12, 308, 188), outline=(255, 255, 255), width=3)
        dibujo.text((24, 90), texto, fill=(255, 255, 255))
        buffer = io.BytesIO()
        imagen.save(buffer, format='PNG')
        return 'respaldo.png', buffer.getvalue()
    contenido = f'Acta de respaldo {texto}'.encode('latin-1', 'replace')
    return 'acta.pdf', b'%PDF-1.4\n% SGR\n' + contenido + b'\n%%EOF\n'


def build_volumen(total_actividades=500, con_archivos=True):
    """Genera ~2,5 registros de negocio por actividad (más de 1.000 con el valor por defecto)."""
    if ya_cargado():
        return None
    rng = random.Random(SEMILLA)
    delegaciones = list(Delegation.objects.order_by('pk'))
    cargos = list(Position.objects.filter(name__in=CARGOS_OPERATIVOS).order_by('pk'))
    tipos = list(ActivityType.objects.filter(is_active=True).order_by('pk'))
    periodos = list(Period.objects.order_by('start_date'))
    grupo_funcionarios = Group.objects.get(name='Funcionarios')
    verificador = User.objects.filter(groups__name='Verificadores').order_by('pk').first()

    # 1) Funcionarios adicionales: la misma cantidad en cada delegación y con cargos operativos.
    #    Sin contraseña utilizable: son datos, no cuentas de acceso.
    usuarios = []
    for i in range(FUNCIONARIOS_POR_DELEGACION * len(delegaciones)):
        user = User(username=f'vol_funcionario_{i + 1:02d}', email=f'vol{i + 1:02d}@demo.sgr.local')
        user.set_unusable_password()
        usuarios.append(user)
    User.objects.bulk_create(usuarios)
    usuarios = list(User.objects.filter(username__startswith='vol_funcionario_').order_by('username'))
    grupo_funcionarios.user_set.add(*usuarios)
    Employee.objects.bulk_create([
        Employee(
            user=user, delegation=delegaciones[i % len(delegaciones)], position=cargos[(i // 2) % len(cargos)],
            name=f'{rng.choice(NOMBRES)} {rng.choice(APELLIDOS)} {rng.choice(APELLIDOS)}',
        )
        for i, user in enumerate(usuarios)
    ])
    por_delegacion = {d.pk: [] for d in delegaciones}
    for e in Employee.objects.filter(user__username__startswith='vol_funcionario_').select_related('delegation'):
        por_delegacion[e.delegation_id].append(e)
    demo = {
        e.user.username: e
        for e in Employee.objects.filter(user__username__in=CUOTA_DEMO).select_related('user', 'delegation')
    }

    def elegir_funcionario(delegacion):
        """Reparte entre las cuentas de demo (según su cuota) y los funcionarios de volumen."""
        sorteo = rng.random()
        acumulado = 0
        for username, cuota in CUOTA_DEMO.items():
            empleado = demo.get(username)
            if empleado and empleado.delegation_id == delegacion.pk:
                acumulado += cuota
                if sorteo < acumulado:
                    return empleado
        return rng.choice(por_delegacion[delegacion.pk])

    # 2) Actividades: mitad para cada delegación, repartidas entre tipos y períodos.
    estados = ['pending'] * 5 + ['approved'] * 4 + ['rejected']
    actividades = []
    for n in range(1, total_actividades + 1):
        delegacion = delegaciones[n % len(delegaciones)]
        empleado = elegir_funcionario(delegacion)
        periodo = rng.choice(periodos)
        sector = rng.choice(SECTORES.get(delegacion.name, ['Sector urbano']))
        actividades.append(Activity(
            number=f'{PREFIJO}{n:05d}', employee=empleado, delegation=delegacion, period=periodo,
            activity_type=rng.choice(tipos), date=_fecha_en(rng, periodo),
            description=f'{rng.choice(ACCIONES)} en sector {sector}.',
            action=rng.choice(ACCIONES), contact=f'Vecino/a {rng.choice(APELLIDOS)}',
            phone=f'+569{rng.randint(10000000, 99999999)}', is_agenda_item=rng.random() < 0.2,
            evidence_code=f'EV-{PREFIJO}{n:05d}', validation_status=rng.choice(estados),
        ))
    Activity.objects.bulk_create(actividades, batch_size=500)
    actividades = list(
        Activity.objects.filter(number__startswith=PREFIJO).select_related('activity_type', 'delegation')
        .order_by('number')
    )

    # 3) Evidencias (70 % de las actividades), con el estado de validación de la actividad.
    #    Una de cada cuatro trae archivo real; las revisadas quedan con su Validation.
    evidencias = []
    for a in actividades:
        if rng.random() >= 0.7:
            continue
        evidencia = Evidence(
            unique_code=f'EVI-{PREFIJO}{a.pk:06d}', activity=a, status=a.validation_status,
            description=f'Respaldo de {a.number}',
            result='' if a.validation_status == 'pending' else 'Revisión de volumen de datos.',
            reviewed_by=None if a.validation_status == 'pending' else verificador,
        )
        if con_archivos and len(evidencias) % 4 == 0:
            nombre, contenido = _archivo_evidencia(rng, len(evidencias), a.number)
            evidencia.file.name = default_storage.save(ruta_evidencia(evidencia, nombre), ContentFile(contenido))
        evidencias.append(evidencia)
    Evidence.objects.bulk_create(evidencias, batch_size=500)
    revisadas = list(Evidence.objects.filter(activity__number__startswith=PREFIJO).exclude(status='pending'))
    validaciones = [
        Validation(evidence=e, reviewer=verificador, status=e.status, comment=e.result)
        for e in revisadas if verificador
    ]
    Validation.objects.bulk_create(validaciones, batch_size=500)

    # 4) Gestiones de atención social (1 a 3) para las actividades de tipo social.
    gestiones = []
    for a in actividades:
        if a.activity_type.category == 'social':
            for paso in range(1, rng.randint(1, 3) + 1):
                gestiones.append(SocialCase(activity=a, step_number=paso,
                                            description=f'Gestión {paso}: {rng.choice(ACCIONES).lower()}.'))
    SocialCase.objects.bulk_create(gestiones, batch_size=500)

    # 5) Compromisos (mitad por delegación) y sus seguimientos.
    estados_compromiso = ['registered', 'pending', 'in_progress', 'done']
    compromisos = []
    for n in range(1, total_actividades // 4 + 1):
        delegacion = delegaciones[n % len(delegaciones)]
        empleado = elegir_funcionario(delegacion)
        estado = rng.choice(estados_compromiso)
        sector = rng.choice(SECTORES.get(delegacion.name, ['Sector urbano']))
        compromisos.append(Commitment(
            title=f'{PREFIJO}{n:04d} {rng.choice(TEMAS_COMPROMISO)} ({sector})',
            delegation=delegacion, responsible=empleado, status=estado,
            due_date=datetime.date(2026, 6, 1) + datetime.timedelta(days=rng.randint(0, 240)),
            notes='Cerrado con informe de terreno.' if estado == 'done' else '',
        ))
    Commitment.objects.bulk_create(compromisos, batch_size=500)
    compromisos = list(Commitment.objects.filter(title__startswith=PREFIJO).order_by('title'))
    seguimientos = [
        CommitmentFollowUp(commitment=c, responsible=c.responsible, new_status=c.status,
                           description=f'Avance registrado para «{c.title[:40]}».')
        for c in compromisos for _ in range(rng.randint(0, 2))
    ]
    CommitmentFollowUp.objects.bulk_create(seguimientos, batch_size=500)

    return {
        'Funcionarios': len(usuarios), 'Actividades': len(actividades), 'Evidencias': len(evidencias),
        'Validaciones': len(validaciones), 'Atenciones sociales': len(gestiones),
        'Compromisos': len(compromisos), 'Seguimientos': len(seguimientos),
    }
