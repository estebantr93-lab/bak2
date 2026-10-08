"""Serializers de la API: qué entra y sale en JSON para cada uno de los seis recursos.

Campos explícitos (nunca '__all__'): solo se publica lo necesario.
"""
from rest_framework import serializers

from actividades.models import Activity, SocialCase
from agenda.models import Commitment
from core.models import ActivityType
from evidencias.models import Evidence
from funcionarios.models import Employee


# ---------------------------------------------------------------------------------------------------
# Modelos principales (CRUD)
# ---------------------------------------------------------------------------------------------------

class ActivitySerializer(serializers.ModelSerializer):
    employee = serializers.PrimaryKeyRelatedField(queryset=Employee.objects.filter(is_active=True))
    activity_type = serializers.PrimaryKeyRelatedField(queryset=ActivityType.objects.filter(is_active=True))
    validation_status_display = serializers.CharField(source='get_validation_status_display', read_only=True)
    # Informativo: en un período cerrado la actividad no se puede crear, modificar ni eliminar.
    period_is_closed = serializers.BooleanField(source='period.is_closed', read_only=True, default=None)

    class Meta:
        model = Activity
        fields = ['id', 'number', 'employee', 'delegation', 'period', 'period_is_closed', 'activity_type', 'date', 'description',
                  'action', 'contact', 'phone', 'is_agenda_item', 'evidence_code', 'validation_status',
                  'validation_status_display', 'created_at', 'updated_at']
        # La delegación sale del funcionario; el código y el estado los maneja el sistema.
        read_only_fields = ['id', 'delegation', 'period_is_closed', 'evidence_code', 'validation_status',
                            'created_at', 'updated_at']
        extra_kwargs = {'period': {'required': True, 'allow_null': False}}

    def validate(self, datos):
        if 'employee' in datos:
            datos['delegation'] = datos['employee'].delegation
        return datos


class SocialCaseSerializer(serializers.ModelSerializer):
    activity = serializers.PrimaryKeyRelatedField(queryset=Activity.objects.all())

    class Meta:
        model = SocialCase
        fields = ['id', 'activity', 'step_number', 'date', 'description', 'result', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class CommitmentSerializer(serializers.ModelSerializer):
    responsible = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.filter(is_active=True), required=False, allow_null=True,
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Commitment
        fields = ['id', 'title', 'description', 'delegation', 'responsible', 'due_date', 'status', 'status_display',
                  'notes', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class EvidenceSerializer(serializers.ModelSerializer):
    """El archivo se envía como multipart/form-data. En la respuesta se entrega la URL protegida, que exige
    sesión en el sitio."""

    activity = serializers.PrimaryKeyRelatedField(queryset=Activity.objects.all())
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Evidence
        fields = ['id', 'unique_code', 'activity', 'description', 'file', 'status', 'status_display', 'result',
                  'registered_at', 'created_at', 'updated_at']
        # El estado y el resultado cambian solo con la revisión del verificador (recurso Validation).
        read_only_fields = ['id', 'unique_code', 'status', 'result', 'registered_at', 'created_at', 'updated_at']
        extra_kwargs = {'file': {'required': True, 'allow_null': False}}

    def get_fields(self):
        campos = super().get_fields()
        if self.instance is not None:
            campos['file'].required = False  # al actualizar, el archivo se reemplaza solo si se envía uno
        return campos
