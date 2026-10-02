"""Explica por qué una cuenta puede o no puede iniciar sesión (mismas reglas que el login).

    python manage.py diagnosticar_acceso <usuario o correo>

Solo lee la base de datos: no cambia nada ni muestra contraseñas.
"""
from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.utils import timezone

from core.admin_utils import (
    GRUPO_ADMINISTRADORES, GRUPO_FUNCIONARIOS, GRUPO_VERIFICADORES, ROLES_ETIQUETAS, es_usuario_sin_restriccion,
    get_rol, tiene_acceso_al_sistema,
)
from colaboracion.models import AuditLog
from funcionarios.models import Employee

GRUPOS_DE_ROL = (GRUPO_ADMINISTRADORES, GRUPO_FUNCIONARIOS, GRUPO_VERIFICADORES)


def _normalizado(texto):
    """Para detectar nombres parecidos: sin mayúsculas, espacios extra ni la «s» final (Funcionario/Funcionarios)."""
    return ' '.join(texto.split()).casefold().rstrip('s')


class Command(BaseCommand):
    help = 'Explica por qué una cuenta puede o no puede iniciar sesión.'

    def add_arguments(self, parser):
        parser.add_argument('cuenta', help='Nombre de usuario (o correo) de la cuenta.')

    def handle(self, *args, cuenta, **opciones):
        buscado = cuenta.strip()
        parecidas = User.objects.filter(Q(username__iexact=buscado) | Q(email__iexact=buscado)).order_by('pk')
        if not parecidas:
            raise CommandError(f'No existe ninguna cuenta con usuario o correo «{buscado}».')
        if len(parecidas) > 1:
            self.stdout.write(self.style.WARNING(
                f'Hay {len(parecidas)} cuentas con ese usuario o correo; el login usa el NOMBRE DE USUARIO exacto. '
                'Revise que el grupo y el perfil estén en la misma cuenta con la que se ingresa.'))
        for user in parecidas:
            self._diagnosticar(user, buscado)

    def _diagnosticar(self, user, buscado):
        problemas = []
        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING(f'Cuenta #{user.pk}: usuario «{user.username}»  correo «{user.email}»'))
        if user.username != buscado:
            problemas.append(f'Para ingresar hay que escribir el usuario exacto «{user.username}» '
                             '(el login es por nombre de usuario, distingue espacios y mayúsculas).')
        if not user.is_active:
            problemas.append('La cuenta está inactiva (Usuarios → «Activo» desmarcado).')

        grupos = list(user.groups.values_list('name', flat=True))
        self.stdout.write(f'  Superusuario: {"sí" if user.is_superuser else "no"}')
        self.stdout.write(f'  Grupos: {", ".join(grupos) or "ninguno"}')
        faltantes = [g for g in GRUPOS_DE_ROL if not Group.objects.filter(name=g).exists()]
        if faltantes:
            problemas.append(f'No existen los grupos {", ".join(faltantes)} en esta base: ejecute «python manage.py seed_data».')
        for grupo in grupos:
            parecido = next((g for g in GRUPOS_DE_ROL if _normalizado(g) == _normalizado(grupo) and g != grupo), None)
            if parecido:
                problemas.append(f'El grupo «{grupo}» no es el del sistema: debe ser exactamente «{parecido}».')

        rol = get_rol(user)
        self.stdout.write(f'  Rol: {ROLES_ETIQUETAS.get(rol, "ninguno")}')
        if rol is None and not any('no es el del sistema' in p for p in problemas):
            problemas.append(f'Sin rol: agregue la cuenta a uno de los grupos {", ".join(GRUPOS_DE_ROL)} '
                             '(en Usuarios → Grupos, pasándolo a la columna «Grupos elegidos») y guarde.')

        perfil = Employee.objects.select_related('delegation').filter(user=user).first()
        if perfil:
            self.stdout.write(f'  Perfil de funcionario: «{perfil.name}», {perfil.delegation}, '
                              f'{"activo" if perfil.is_active else "DESACTIVADO"}')
            if not perfil.is_active and not es_usuario_sin_restriccion(user):
                problemas.append('El perfil de funcionario está desactivado (Funcionarios → «Activo»).')
        else:
            self.stdout.write('  Perfil de funcionario: ninguno vinculado a esta cuenta')
            if rol is not None and not es_usuario_sin_restriccion(user):
                otros = Employee.objects.filter(name__icontains=user.username.split('@')[0].split('.')[0])[:3]
                pista = (' Hay perfiles con nombre parecido vinculados a otras cuentas: '
                         + ', '.join(f'«{e.name}» → usuario «{e.user.username}»' for e in otros)) if otros else ''
                problemas.append('Administradores y funcionarios necesitan un perfil: Funcionarios → Añadir, con '
                                 f'Usuario «{user.username}», delegación y cargo.{pista}')

        rechazos = AuditLog.objects.filter(
            action__in=('login_rechazado', 'login_bloqueado'), detail=user.username.strip().lower(),
        ).order_by('-date')[:3]
        for rechazo in rechazos:
            motivo = (rechazo.changes or {}).get('motivo', ['', 'demasiados intentos fallidos'])[1]
            self.stdout.write(f'  Ingreso rechazado el {timezone.localtime(rechazo.date):%d-%m-%Y %H:%M}: {motivo} '
                              '(la persona vio «Usuario o contraseña incorrectos.»)')

        if tiene_acceso_al_sistema(user) and user.is_active and not problemas:
            self.stdout.write(self.style.SUCCESS('  Resultado: puede iniciar sesión.'))
            return
        estado = 'puede iniciar sesión, pero revise:' if tiene_acceso_al_sistema(user) and user.is_active else 'NO puede iniciar sesión:'
        self.stdout.write(self.style.ERROR(f'  Resultado: {estado}'))
        for problema in problemas:
            self.stdout.write(f'   - {problema}')
