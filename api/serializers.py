"""Serializers de la API: qué entra y sale en JSON para cada uno de los seis recursos.

Campos explícitos (nunca '__all__'). Las reglas de negocio no se duplican: cada serializer ejecuta el
clean() del modelo sobre el registro como quedaría, así la API rechaza (400) lo mismo que la web.
"""
import copy

from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import serializers

from actividades.models import Activity, SocialCase
from agenda.models import Commitment, CommitmentFollowUp
from core.models import ActivityType
from evidencias.archivos import validar_archivo_subido
from evidencias.models import Evidence, Validation
from funcionarios.models import Employee


class ReglasDelModeloMixin:
    """Ejecuta Model.clean() con los datos nuevos combinados con los guardados (sirve también para PATCH)."""

    def validate(self, datos):
        datos = super().validate(datos)
        if self.instance is not None:
            registro = copy.copy(self.instance)
            for campo, valor in datos.items():
                setattr(registro, campo, valor)
        else:
            registro = self.Meta.model(**datos)
        self.completar(registro)
        try:
            registro.clean()
        except DjangoValidationError as error:
            raise serializers.ValidationError(
                error.message_dict if hasattr(error, 'error_dict') else {'non_field_errors': error.messages}
            )
        return datos

    def completar(self, registro):
        """Campos que el sistema deriva antes de validar (por ejemplo, la delegación del funcionario)."""


# ---------------------------------------------------------------------------------------------------
# Modelos principales (CRUD)
# ---------------------------------------------------------------------------------------------------

class ActivitySerializer(ReglasDelModeloMixin, serializers.ModelSerializer):
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

    def validate_number(self, valor):
        # Validación de campo: formato normalizado y sin duplicados (también contra registros eliminados).
        numero = valor.strip().upper()
        if len(numero) < 3:
            raise serializers.ValidationError('El número debe tener al menos 3 caracteres.')
        duplicado = Activity.all_objects.filter(number__iexact=numero)
        if self.instance is not None:
            duplicado = duplicado.exclude(pk=self.instance.pk)
        if duplicado.exists():
            raise serializers.ValidationError('Ya existe una actividad con este número.')
        return numero

    def validate_date(self, valor):
        if valor > timezone.localdate():
            raise serializers.ValidationError('La fecha no puede ser futura: se registran actividades ya realizadas.')
        return valor

    def validate(self, datos):
        if 'employee' in datos:
            datos['delegation'] = datos['employee'].delegation
        return super().validate(datos)


class SocialCaseSerializer(ReglasDelModeloMixin, serializers.ModelSerializer):
    activity = serializers.PrimaryKeyRelatedField(queryset=Activity.objects.all())

    class Meta:
        model = SocialCase
        fields = ['id', 'activity', 'step_number', 'date', 'description', 'result', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_step_number(self, valor):
        if not 1 <= valor <= 3:
            raise serializers.ValidationError('El número de gestión debe estar entre 1 y 3.')
        return valor


class CommitmentSerializer(ReglasDelModeloMixin, serializers.ModelSerializer):
    responsible = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.filter(is_active=True), required=False, allow_null=True,
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Commitment
        fields = ['id', 'title', 'description', 'delegation', 'responsible', 'due_date', 'status', 'status_display',
                  'notes', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_title(self, valor):
        titulo = ' '.join(valor.split())
        if len(titulo) < 5:
            raise serializers.ValidationError('El título debe tener al menos 5 caracteres.')
        return titulo

    def validate_due_date(self, valor):
        # Un compromiso nuevo no puede nacer vencido; al editar se permite mantener la fecha original.
        if self.instance is None and valor < timezone.localdate():
            raise serializers.ValidationError('La fecha de vencimiento no puede estar en el pasado.')
        return valor


class EvidenceSerializer(ReglasDelModeloMixin, serializers.ModelSerializer):
    """El archivo se envía como multipart/form-data. Pasa por las mismas reglas que la web (tipo, tamaño
    y contenido real). En la respuesta se entrega la URL protegida, que exige sesión en el sitio."""

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

    def validate_file(self, archivo):
        try:
            return validar_archivo_subido(archivo)
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.messages)


# ---------------------------------------------------------------------------------------------------
# Modelos operacionales (solo lectura)
# ---------------------------------------------------------------------------------------------------

class ValidationSerializer(serializers.ModelSerializer):
    reviewer = serializers.CharField(source='reviewer.username', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Validation
        fields = ['id', 'evidence', 'reviewer', 'date', 'status', 'status_display', 'comment']
        read_only_fields = fields


class CommitmentFollowUpSerializer(serializers.ModelSerializer):
    new_status_display = serializers.CharField(source='get_new_status_display', read_only=True)

    class Meta:
        model = CommitmentFollowUp
        fields = ['id', 'commitment', 'date', 'responsible', 'description', 'new_status', 'new_status_display']
        read_only_fields = fields
