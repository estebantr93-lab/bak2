from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

from actividades.models import Actividad, AtencionSocial
from agenda.models import Compromiso, SeguimientoCompromiso
from core.models import Periodo, TipoActividad
from evidencias.models import Evidencia, Validacion

from .models import Funcionario


def _permisos(model, acciones):
    ct = ContentType.objects.get_for_model(model)
    codenames = [f'{accion}_{model._meta.model_name}' for accion in acciones]
    return list(Permission.objects.filter(content_type=ct, codename__in=codenames))


def configurar_grupos_y_permisos():
    administradores, _ = Group.objects.get_or_create(name='Administradores')
    grupo_funcionarios, _ = Group.objects.get_or_create(name='Funcionarios')
    verificadores, _ = Group.objects.get_or_create(name='Verificadores')

    administradores.permissions.set(Permission.objects.all())

    permisos_funcionarios = (
        _permisos(Actividad, ['add', 'change', 'view'])
        + _permisos(AtencionSocial, ['add', 'change', 'view'])
        + _permisos(Evidencia, ['add', 'view'])
        + _permisos(Compromiso, ['view'])
        + _permisos(SeguimientoCompromiso, ['add', 'view'])
        + _permisos(Funcionario, ['view'])
        + _permisos(TipoActividad, ['view'])
        + _permisos(Periodo, ['view'])
    )
    grupo_funcionarios.permissions.set(permisos_funcionarios)

    ct_evidencia = ContentType.objects.get_for_model(Evidencia)
    permiso_aprobar = Permission.objects.get(content_type=ct_evidencia, codename='can_approve_evidencia')
    permisos_verificadores = (
        _permisos(Evidencia, ['view', 'change'])
        + _permisos(Validacion, ['add', 'view'])
        + [permiso_aprobar]
    )
    verificadores.permissions.set(permisos_verificadores)

    return administradores, grupo_funcionarios, verificadores
