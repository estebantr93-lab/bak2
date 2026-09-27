from django.apps import apps

from .soft_delete import es_soft_delete


def get_usuario_delegacion(user):
    if not user or not user.is_authenticated:
        return None
    Employee = apps.get_model('funcionarios', 'Employee')
    try:
        funcionario = Employee.objects.select_related('delegation').get(user=user)
    except Employee.DoesNotExist:
        return None
    return funcionario.delegation


GRUPO_ADMINISTRADORES = 'Administradores'
GRUPO_FUNCIONARIOS = 'Funcionarios'
GRUPO_VERIFICADORES = 'Verificadores'

ROL_SUPERADMIN = 'superadmin'
ROL_ADMIN_DELEGACION = 'admin_delegacion'
ROL_VERIFICADOR = 'reviewer'
ROL_FUNCIONARIO = 'employee'

ROLES_ETIQUETAS = {
    ROL_SUPERADMIN: 'Administrador general',
    ROL_ADMIN_DELEGACION: 'Administrador de delegación',
    ROL_VERIFICADOR: 'Verificador',
    ROL_FUNCIONARIO: 'Funcionario',
}


def get_rol(user):
    """Rol principal del usuario, en orden de mayor a menor alcance.

    Se guarda en el propio objeto user: durante una petición los hooks del Admin y las vistas lo
    consultan varias veces y así se evita repetir la consulta de grupos.
    """
    if not user or not user.is_authenticated:
        return None
    if not hasattr(user, '_sgr_rol'):
        user._sgr_rol = _calcular_rol(user)
    return user._sgr_rol


def _calcular_rol(user):
    if user.is_superuser:
        return ROL_SUPERADMIN
    # groups.all() aprovecha prefetch_related('user__groups') en listados.
    grupos = {grupo.name for grupo in user.groups.all()}
    if GRUPO_ADMINISTRADORES in grupos:
        return ROL_ADMIN_DELEGACION
    if GRUPO_VERIFICADORES in grupos:
        return ROL_VERIFICADOR
    if GRUPO_FUNCIONARIOS in grupos:
        return ROL_FUNCIONARIO
    return None


def es_usuario_sin_restriccion(user):
    """Solo el superusuario y los verificadores ven todas las delegaciones.

    Los administradores de delegación quedan acotados a la delegación de su
    perfil de Funcionario, igual que los funcionarios.
    """
    return get_rol(user) in (ROL_SUPERADMIN, ROL_VERIFICADOR)


def tiene_acceso_al_sistema(user):
    """Puede usar el sistema quien tiene rol y, salvo los roles globales, un perfil con delegación."""
    if get_rol(user) is None:
        return False
    return es_usuario_sin_restriccion(user) or get_usuario_delegacion(user) is not None


def filtrar_por_delegacion(queryset, user, campo='delegation'):
    """Scoping para vistas fuera del Admin: mismo criterio que ScopedModelAdmin."""
    if es_usuario_sin_restriccion(user):
        return queryset
    delegacion = get_usuario_delegacion(user)
    if delegacion is None:
        return queryset.none()
    return queryset.filter(**{campo: delegacion.pk})


class ScopedModelAdmin:
    scope_by = 'delegation'

    def get_list_filter(self, request):
        filtros = super().get_list_filter(request)
        if es_usuario_sin_restriccion(request.user):
            return filtros
        # Un usuario acotado ya ve una sola delegación: filtrar por ella no aporta y listaría las demás.
        return [f for f in filtros if f != self.scope_by]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if es_soft_delete(self.model):
            qs = qs.filter(deleted_at__isnull=True)  # el Admin tampoco lista eliminados lógicamente
        if es_usuario_sin_restriccion(request.user):
            return qs
        delegacion = get_usuario_delegacion(request.user)
        if delegacion is None:
            return qs.none()
        return qs.filter(**{self.scope_by: delegacion.pk})

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not es_usuario_sin_restriccion(request.user):
            delegacion = get_usuario_delegacion(request.user)
            if delegacion is not None:
                relacionado = db_field.related_model
                if relacionado is type(delegacion):
                    kwargs['queryset'] = relacionado.objects.filter(pk=delegacion.pk)
                elif any(campo.name == 'delegation' for campo in relacionado._meta.fields):
                    kwargs['queryset'] = relacionado.objects.filter(delegation=delegacion)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def has_add_permission(self, request):
        if not super().has_add_permission(request):
            return False
        if es_usuario_sin_restriccion(request.user):
            return True
        return get_usuario_delegacion(request.user) is not None

    def _objeto_en_alcance(self, request, obj):
        if obj is None:
            return True
        if es_usuario_sin_restriccion(request.user):
            return True
        delegacion = get_usuario_delegacion(request.user)
        if delegacion is None:
            return False
        valor = obj
        for paso in self.scope_by.split('__'):
            valor = getattr(valor, paso, None)
            if valor is None:
                return False
        return getattr(valor, 'pk', valor) == delegacion.pk

    def has_change_permission(self, request, obj=None):
        if not super().has_change_permission(request, obj):
            return False
        return self._objeto_en_alcance(request, obj)

    def has_delete_permission(self, request, obj=None):
        if not super().has_delete_permission(request, obj):
            return False
        return self._objeto_en_alcance(request, obj)
