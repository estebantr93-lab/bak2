from django.core.management.base import BaseCommand
from django.db import transaction

from actividades.data import build_actividades
from actividades.models import Actividad, AtencionSocial
from agenda.data import build_agenda
from agenda.models import Compromiso, SeguimientoCompromiso
from colaboracion.data import build_colaboracion
from colaboracion.models import Alerta, Comentario, TrazaAuditoria
from core.data import build_core
from core.models import Cargo, Delegacion, Parametro, Periodo, TipoActividad
from evidencias.data import build_evidencias
from evidencias.models import Evidencia, Validacion
from funcionarios.data import CLAVES_GENERADAS, USUARIOS_DEMO, build_funcionarios
from funcionarios.models import Funcionario
from medicion.data import build_medicion
from medicion.models import Indicador, Ponderacion
from medicion.models import Meta as MetaModel


class Command(BaseCommand):
    help = 'Carga datos de demostración reproducibles del SGR (idempotente).'

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

        self._imprimir_resumen()

    def _imprimir_resumen(self):
        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING('Resumen de conteos:'))
        conteos = [
            ('Delegaciones', Delegacion.objects.count()),
            ('Cargos', Cargo.objects.count()),
            ('Tipos de actividad', TipoActividad.objects.count()),
            ('Períodos', Periodo.objects.count()),
            ('Parámetros', Parametro.objects.count()),
            ('Funcionarios', Funcionario.objects.count()),
            ('Metas', MetaModel.objects.count()),
            ('Ponderaciones', Ponderacion.objects.count()),
            ('Indicadores', Indicador.objects.count()),
            ('Actividades', Actividad.objects.count()),
            ('Atenciones sociales', AtencionSocial.objects.count()),
            ('Evidencias', Evidencia.objects.count()),
            ('Validaciones', Validacion.objects.count()),
            ('Compromisos', Compromiso.objects.count()),
            ('Seguimientos de compromiso', SeguimientoCompromiso.objects.count()),
            ('Comentarios', Comentario.objects.count()),
            ('Alertas', Alerta.objects.count()),
            ('Trazas de auditoría', TrazaAuditoria.objects.count()),
        ]
        for etiqueta, total in conteos:
            self.stdout.write(f'  - {etiqueta}: {total}')

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
