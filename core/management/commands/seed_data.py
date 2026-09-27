from django.core.management.base import BaseCommand
from django.db import transaction

from actividades.data import build_actividades
from actividades.models import Activity, SocialCase
from agenda.data import build_agenda
from agenda.models import Commitment, CommitmentFollowUp
from colaboracion.data import build_colaboracion
from colaboracion.models import Alert, Comment, AuditLog
from core.data import build_core
from core.models import Position, Delegation, Parameter, Period, ActivityType
from core.volume_data import borrar_volumen, build_volumen
from evidencias.data import build_evidencias
from evidencias.models import Evidence, Validation
from funcionarios.data import CLAVES_GENERADAS, USUARIOS_DEMO, build_funcionarios
from funcionarios.models import Employee
from medicion.data import build_medicion
from medicion.models import Indicator, Weighting
from medicion.models import Goal


class Command(BaseCommand):
    help = 'Carga datos de demostración reproducibles del SGR (idempotente).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--volumen', nargs='?', const=500, type=int, default=0, metavar='ACTIVIDADES',
            help='Agrega datos de volumen (por defecto 500 actividades, más de 1.000 registros de negocio).',
        )
        parser.add_argument(
            '--rehacer-volumen', action='store_true',
            help='Borra los datos de volumen existentes (prefijo VOL-) y los vuelve a generar.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write('Cargando datos de demostración del SGR...')

        build_core()
        self.stdout.write(self.style.SUCCESS('  core: delegaciones, cargos, tipos, períodos y parámetros OK'))

        build_funcionarios()
        self.stdout.write(self.style.SUCCESS('  funcionarios: grupos, permisos y usuarios de prueba OK'))

        build_actividades()
        self.stdout.write(self.style.SUCCESS('  actividades: registros de actividad y atención social OK'))

        build_medicion()
        self.stdout.write(self.style.SUCCESS('  medicion: metas, ponderaciones e indicadores OK'))

        build_evidencias()
        self.stdout.write(self.style.SUCCESS('  evidencias: evidencias y validaciones OK'))

        build_agenda()
        self.stdout.write(self.style.SUCCESS('  agenda: compromisos y seguimientos OK'))

        build_colaboracion()
        self.stdout.write(self.style.SUCCESS('  colaboracion: comentario, alerta y traza de ejemplo OK'))

        if options['rehacer_volumen']:
            borrar_volumen()
            options['volumen'] = options['volumen'] or 500
            self.stdout.write('  volumen: datos anteriores eliminados')
        if options['volumen']:
            creados = build_volumen(options['volumen'])
            if creados is None:
                self.stdout.write('  volumen: ya estaba cargado (no se duplica)')
            else:
                detalle = ', '.join(f'{k}: {v}' for k, v in creados.items())
                self.stdout.write(self.style.SUCCESS(f'  volumen: {sum(creados.values())} registros ({detalle})'))

        self._imprimir_resumen()

    def _imprimir_resumen(self):
        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING('Resumen de conteos:'))
        conteos = [
            ('Delegaciones', Delegation.objects.count()),
            ('Cargos', Position.objects.count()),
            ('Tipos de actividad', ActivityType.objects.count()),
            ('Períodos', Period.objects.count()),
            ('Parámetros', Parameter.objects.count()),
            ('Funcionarios', Employee.objects.count()),
            ('Metas', Goal.objects.count()),
            ('Ponderaciones', Weighting.objects.count()),
            ('Indicadores', Indicator.objects.count()),
            ('Actividades', Activity.objects.count()),
            ('Atenciones sociales', SocialCase.objects.count()),
            ('Evidencias', Evidence.objects.count()),
            ('Validaciones', Validation.objects.count()),
            ('Compromisos', Commitment.objects.count()),
            ('Seguimientos de compromiso', CommitmentFollowUp.objects.count()),
            ('Comentarios', Comment.objects.count()),
            ('Alertas', Alert.objects.count()),
            ('Trazas de auditoría', AuditLog.objects.count()),
        ]
        for etiqueta, total in conteos:
            self.stdout.write(f'  - {etiqueta}: {total}')

        negocio = sum(total for etiqueta, total in conteos if etiqueta in (
            'Funcionarios', 'Actividades', 'Atenciones sociales', 'Evidencias', 'Validaciones',
            'Compromisos', 'Seguimientos de compromiso',
        ))
        self.stdout.write(self.style.SUCCESS(f'  Total de registros de negocio: {negocio}'))
        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING('Cuentas de prueba (usuario -> rol):'))
        roles = {
            'admin_sgr': 'Administrador general (superusuario) — acceso total',
            'admin_centro': 'Administrador Delegación Centro — solo ve y gestiona Centro',
            'admin_norte': 'Administrador Delegación Norte — solo ve y gestiona Norte',
            'funcionario_centro': 'Funcionario Delegación Centro — acceso limitado a su delegación',
            'funcionario_norte': 'Funcionario Delegación Norte — acceso limitado a su delegación',
            'verificador_leia': 'Verificador — revisión y aprobación de evidencias en todas las delegaciones',
        }
        for usuario in USUARIOS_DEMO:
            self.stdout.write(f'  - {usuario} -> {roles[usuario]}')
        if CLAVES_GENERADAS:
            # Solo ocurre si el .env no define DEMO_PASSWORD: se muestran una única vez.
            self.stdout.write('')
            self.stdout.write(self.style.WARNING(
                'DEMO_PASSWORD no está definido: se generaron contraseñas aleatorias (anótelas, no se vuelven a mostrar):'
            ))
            for usuario, clave in CLAVES_GENERADAS.items():
                self.stdout.write(f'  - {usuario}: {clave}')
            CLAVES_GENERADAS.clear()
        else:
            self.stdout.write('Contraseñas: las definidas en el .env (DEMO_PASSWORD / DEMO_PASSWORD_<USUARIO>).')
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Carga de datos de demostración completada.'))
