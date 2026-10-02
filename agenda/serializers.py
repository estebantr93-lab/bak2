"""API REST de compromisos (Unidad 3 · Clase 1): qué datos entran y salen en JSON.

Campos explícitos: solo se publica lo necesario. Las reglas son las mismas del formulario web
(`CommitmentForm`) y del modelo (`Commitment.clean`), así la API no es una puerta trasera para
guardar datos que la web rechazaría.
"""
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import serializers

from core.admin_utils import es_usuario_sin_restriccion, filtrar_por_delegacion, get_usuario_delegacion
from core.models import Delegation
from funcionarios.models import Employee

from .models import Commitment


class CommitmentSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Commitment
        fields = ['id', 'title', 'description', 'delegation', 'responsible', 'due_date', 'status', 'status_display',
                  'notes', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_fields(self):
        campos = super().get_fields()
        user = self.context['request'].user
        # Las opciones de delegación y responsable salen del alcance del usuario, como en la web.
        campos['responsible'].queryset = filtrar_por_delegacion(Employee.objects.filter(is_active=True), user)
        campos['delegation'].queryset = filtrar_por_delegacion(Delegation.objects.all(), user, 'pk')
        if not es_usuario_sin_restriccion(user):
            # Un usuario acotado trabaja solo en su delegación: se completa sola y no se puede cambiar.
            campos['delegation'].required = False
        return campos

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

    def validate(self, datos):
        user = self.context['request'].user
        if not es_usuario_sin_restriccion(user):
            datos['delegation'] = get_usuario_delegacion(user)
        elif self.instance is None and 'delegation' not in datos:
            raise serializers.ValidationError({'delegation': 'Este campo es requerido.'})
        # Reglas del modelo (responsable de la misma delegación, «realizado» con observaciones) sobre
        # el registro como quedaría: en un PATCH se combinan los datos nuevos con los guardados.
        compromiso = Commitment(**{**self._valores_actuales(), **datos})
        try:
            compromiso.clean()
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.message_dict)
        return datos

    def _valores_actuales(self):
        if self.instance is None:
            return {}
        return {campo: getattr(self.instance, campo)
                for campo in ('title', 'description', 'delegation', 'responsible', 'due_date', 'status', 'notes')}
