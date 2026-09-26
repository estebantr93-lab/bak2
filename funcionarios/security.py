from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

from actividades.models import Actividad, AtencionSocial
from agenda.models import Compromiso, SeguimientoCompromiso
from core.models import Cargo, Delegacion, Periodo, TipoActividad
from evidencias.models import Evidencia, Validacion
from medicion.models import Indicador
from medicion.models import Meta as MetaModel

from .models import Funcionario


def _permisos(model, acciones):
    ct = ContentType.objects.get_for_model(model)
    codenames = [f'{accion}_{model._meta.model_name}' for accion in acciones]
    return list(Permission.objects.filter(content_type=ct, codename__in=codenames))


def configurar_grupos_y_permisos():
    administradores, _ = Group.objects.get_or_create(name='Administradores')
    grupo_funcionarios, _ = Group.objects.get_or_create(name='Funcionarios')
    verificadores, _ = Group.objects.get_or_create(name='Verificadores')

    # Administradores de delegación: gestionan todo lo operativo de SU delegación
    # (el alcance lo impone ScopedModelAdmin). No reciben permisos sobre usuarios,
    # grupos ni datos maestros, para que no puedan saltarse el aislamiento.
    ct_evidencia = ContentType.objects.get_for_model(Evidencia)
    permiso_aprobar = Permission.objects.get(content_type=ct_evidencia, codename='can_approve_evidencia')
    crud = ['add', 'change', 'delete', 'view']
    permisos_administradores = (
        _permisos(Actividad, crud)
        + _permisos(AtencionSocial, crud)
        + _permisos(Evidencia, crud)
        + _permisos(Validacion, ['add', 'view'])
        + _permisos(Compromiso, crud)
        + _permisos(SeguimientoCompromiso, crud)
        + _permisos(Indicador, ['view'])
        + _permisos(Funcionario, ['change', 'view'])
        + _permisos(Delegacion, ['view'])
        + _permisos(Cargo, ['view'])
        + _permisos(TipoActividad, ['view'])
        + _permisos(Periodo, ['view'])
        + _permisos(MetaModel, ['view'])
        + [permiso_aprobar]
    )
    administradores.permissions.set(permisos_administradores)

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

    permisos_verificadores = (
        _permisos(Evidencia, ['view', 'change'])
        + _permisos(Validacion, ['add', 'view'])
        + [permiso_aprobar]
    )
    verificadores.permissions.set(permisos_verificadores)

    return administradores, grupo_funcionarios, verificadores
