"""ViewSets de la API REST: CRUD de los cuatro modelos principales y consulta de los dos operacionales.

- Autenticación JWT (Bearer) y permisos por rol de la API (api/permisos.py), definidos por defecto en
  REST_FRAMEWORK: sin token 401, sin rol o sin permiso para el método 403.
- Los listados se ordenan por id y se paginan de a 20 (api/paginacion.py).
- DELETE es un borrado lógico (deleted_at), responde 204 y el registro deja de aparecer en las consultas.
- Cada alta, cambio y eliminación queda en la traza de auditoría con el usuario y los valores cambiados.
"""
from django.db.models.deletion import ProtectedError
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError

from actividades.models import Activity, SocialCase
from agenda.models import Commitment
from core.admin_utils import motivo_no_modificable, registrar_en_auditoria
from evidencias.models import Evidence

from . import serializers

DETALLE_AUDITORIA = 'API REST'


def _valores(obj, campos):
    return {campo: str(getattr(obj, campo) if getattr(obj, campo) is not None else '') for campo in campos}


class CrudAuditadoViewSet(viewsets.ModelViewSet):
    """CRUD con traza de auditoría y con las reglas de bloqueo del dominio (período cerrado)."""

    def campos_auditados(self):
        return [campo for campo in self.get_serializer_class().Meta.fields
                if campo not in self.get_serializer_class().Meta.read_only_fields and not campo.endswith('_display')]

    def _exigir_modificable(self, obj):
        motivo = motivo_no_modificable(obj)
        if motivo:
            raise ValidationError({'non_field_errors': [motivo]})

    def perform_create(self, serializer):
        obj = serializer.save()
        cambios = {campo: ['', valor] for campo, valor in _valores(obj, self.campos_auditados()).items() if valor}
        registrar_en_auditoria(self.request.user, 'crear', obj, DETALLE_AUDITORIA, cambios=cambios)

    def perform_update(self, serializer):
        self._exigir_modificable(serializer.instance)
        campos = self.campos_auditados()
        antes = _valores(serializer.instance, campos)
        obj = serializer.save()
        despues = _valores(obj, campos)
        cambios = {campo: [antes[campo], despues[campo]] for campo in campos if antes[campo] != despues[campo]}
        if cambios:
            registrar_en_auditoria(self.request.user, 'modificar', obj, DETALLE_AUDITORIA, cambios=cambios)

    def perform_destroy(self, instance):
        self._exigir_modificable(instance)
        try:
            instance.delete()  # BaseModel: borrado lógico, también de los hijos declarados en soft_delete_cascade
        except ProtectedError:
            raise ValidationError({'non_field_errors': ['El registro tiene datos asociados y no se puede eliminar.']})
        registrar_en_auditoria(self.request.user, 'eliminar', instance, DETALLE_AUDITORIA)


class ActivityViewSet(CrudAuditadoViewSet):
    queryset = Activity.objects.select_related('employee', 'delegation', 'period', 'activity_type').order_by('id')
    serializer_class = serializers.ActivitySerializer


class SocialCaseViewSet(CrudAuditadoViewSet):
    queryset = SocialCase.objects.select_related('activity').order_by('id')
    serializer_class = serializers.SocialCaseSerializer


class CommitmentViewSet(CrudAuditadoViewSet):
    queryset = Commitment.objects.select_related('delegation', 'responsible').order_by('id')
    serializer_class = serializers.CommitmentSerializer


class EvidenceViewSet(CrudAuditadoViewSet):
    queryset = Evidence.objects.select_related('activity').order_by('id')
    serializer_class = serializers.EvidenceSerializer

