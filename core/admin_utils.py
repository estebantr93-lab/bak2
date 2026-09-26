from django.apps import apps


def get_usuario_delegacion(user):
    if not user or not user.is_authenticated:
        return None
    Funcionario = apps.get_model('funcionarios', 'Funcionario')
    try:
        funcionario = Funcionario.objects.select_related('delegacion').get(user=user)
    except Funcionario.DoesNotExist:
        return None
    return funcionario.delegacion


def es_usuario_sin_restriccion(user):
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=['Administradores', 'Verificadores']).exists()


class ScopedModelAdmin:
    scope_by = 'delegacion'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if es_usuario_sin_restriccion(request.user):
            return qs
        delegacion = get_usuario_delegacion(request.user)
        if delegacion is None:
            return qs.none()
        return qs.filter(**{self.scope_by: delegacion})

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not es_usuario_sin_restriccion(request.user):
            delegacion = get_usuario_delegacion(request.user)
            if delegacion is not None:
                relacionado = db_field.related_model
                if relacionado is type(delegacion):
                    kwargs['queryset'] = relacionado.objects.filter(pk=delegacion.pk)
                elif any(campo.name == 'delegacion' for campo in relacionado._meta.fields):
                    kwargs['queryset'] = relacionado.objects.filter(delegacion=delegacion)
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
        return valor == delegacion

    def has_change_permission(self, request, obj=None):
        if not super().has_change_permission(request, obj):
            return False
        return self._objeto_en_alcance(request, obj)

    def has_delete_permission(self, request, obj=None):
        if not super().has_delete_permission(request, obj):
            return False
        return self._objeto_en_alcance(request, obj)
