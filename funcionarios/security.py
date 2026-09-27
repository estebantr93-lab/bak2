from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

from actividades.models import Activity, SocialCase
from agenda.models import Commitment, CommitmentFollowUp
from core.models import Position, Delegation, Period, ActivityType
from evidencias.models import Evidence, Validation
from medicion.models import Indicator
from medicion.models import Goal

from .models import Employee


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
    ct_evidencia = ContentType.objects.get_for_model(Evidence)
    permiso_aprobar = Permission.objects.get(content_type=ct_evidencia, codename='can_approve_evidence')
    crud = ['add', 'change', 'delete', 'view']
    permisos_administradores = (
        _permisos(Activity, crud)
        + _permisos(SocialCase, crud)
        + _permisos(Evidence, crud)
        + _permisos(Validation, ['add', 'view'])
        + _permisos(Commitment, crud)
        + _permisos(CommitmentFollowUp, crud)
        + _permisos(Indicator, ['view'])
        + _permisos(Employee, ['change', 'view'])
        + _permisos(Delegation, ['view'])
        + _permisos(Position, ['view'])
        + _permisos(ActivityType, ['view'])
        + _permisos(Period, ['view'])
        + _permisos(Goal, ['view'])
        + [permiso_aprobar]
    )
    administradores.permissions.set(permisos_administradores)

    permisos_funcionarios = (
        _permisos(Activity, ['add', 'change', 'view'])
        + _permisos(SocialCase, ['add', 'change', 'view'])
        + _permisos(Evidence, ['add', 'view'])
        + _permisos(Commitment, ['view'])
        + _permisos(CommitmentFollowUp, ['add', 'view'])
        + _permisos(Employee, ['view'])
        + _permisos(ActivityType, ['view'])
        + _permisos(Period, ['view'])
    )
    grupo_funcionarios.permissions.set(permisos_funcionarios)

    permisos_verificadores = (
        _permisos(Evidence, ['view', 'change'])
        + _permisos(Validation, ['add', 'view'])
        + [permiso_aprobar]
    )
    verificadores.permissions.set(permisos_verificadores)

    return administradores, grupo_funcionarios, verificadores
