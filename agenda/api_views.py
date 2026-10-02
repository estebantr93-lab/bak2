"""ViewSet de la API de compromisos: el CRUD REST sobre el mismo modelo y la misma base de datos.

Mismas capas de seguridad que el CRUD web (core/crud.py):
- autenticación (sesión de Django; JWT en la Clase 2) y permisos del modelo por rol;
- alcance por delegación: un compromiso de otra delegación responde 404;
- un funcionario solo modifica los suyos (403 en los demás);
- DELETE es un borrado lógico y cada cambio queda en la traza de auditoría.
"""
from rest_framework import permissions, viewsets
from django.http import Http404
from rest_framework.exceptions import NotFound, PermissionDenied

from core.admin_utils import filtrar_por_delegacion, puede_modificar, registrar_en_auditoria, tiene_acceso_al_sistema

from .models import Commitment
from .serializers import CommitmentSerializer

CAMPOS_AUDITADOS = ('title', 'description', 'delegation', 'responsible', 'due_date', 'status', 'notes')


class PermisosDelModelo(permissions.DjangoModelPermissions):
    """Permisos de Django por rol, incluido «ver» para GET (DRF solo exige los de escritura)."""

    perms_map = {**permissions.DjangoModelPermissions.perms_map, 'GET': ['%(app_label)s.view_%(model_name)s']}

    def has_permission(self, request, view):
        # Misma regla que el login y el dashboard: sin rol o sin perfil con delegación no hay acceso.
        return tiene_acceso_al_sistema(request.user) and super().has_permission(request, view)


def _valores(obj):
    return {campo: str(getattr(obj, campo) or '') for campo in CAMPOS_AUDITADOS}


class CommitmentViewSet(viewsets.ModelViewSet):
    queryset = Commitment.objects.all().order_by('id')  # objects: solo los no eliminados
    serializer_class = CommitmentSerializer
    permission_classes = [permissions.IsAuthenticated, PermisosDelModelo]

    def get_queryset(self):
        qs = super().get_queryset().select_related('delegation', 'responsible')
        return filtrar_por_delegacion(qs, self.request.user)

    def get_view_name(self):
        return 'Compromiso' if self.suffix == 'Instance' else 'Compromisos'

    def get_object(self):
        try:
            return super().get_object()
        except Http404:
            # Inexistente, eliminado o de otra delegación: la misma respuesta, sin revelar cuál.
            raise NotFound('Compromiso no encontrado.')

    def _exigir_modificable(self, obj):
        if not puede_modificar(self.request.user, obj):
            raise PermissionDenied('Solo puede modificar sus propios compromisos.')

    def perform_create(self, serializer):
        compromiso = serializer.save()
        cambios = {campo: ['', valor] for campo, valor in _valores(compromiso).items() if valor}
        registrar_en_auditoria(self.request.user, 'crear', compromiso, 'API REST', cambios=cambios)

    def perform_update(self, serializer):
        self._exigir_modificable(serializer.instance)
        antes = _valores(serializer.instance)
        compromiso = serializer.save()
        despues = _valores(compromiso)
        cambios = {campo: [antes[campo], despues[campo]] for campo in CAMPOS_AUDITADOS if antes[campo] != despues[campo]}
        if cambios:
            registrar_en_auditoria(self.request.user, 'modificar', compromiso, 'API REST', cambios=cambios)

    def perform_destroy(self, instance):
        self._exigir_modificable(instance)
        instance.delete()  # borrado lógico (deleted_at), igual que la web
        registrar_en_auditoria(self.request.user, 'eliminar', instance, 'API REST')
