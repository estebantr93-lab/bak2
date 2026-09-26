from django import forms
from django.core.exceptions import ValidationError

from .models import Actividad


class ActividadForm(forms.ModelForm):
    class Meta:
        model = Actividad
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        periodo = cleaned_data.get('periodo')
        codigo_evidencia = cleaned_data.get('codigo_evidencia')
        funcionario = cleaned_data.get('funcionario')
        delegacion = cleaned_data.get('delegacion')

        if periodo and periodo.cerrado:
            raise ValidationError('Período cerrado: no se pueden registrar actividades.')
        if not codigo_evidencia:
            raise ValidationError({'codigo_evidencia': 'El código de evidencia es obligatorio.'})
        if funcionario and delegacion and funcionario.delegacion_id != delegacion.id:
            raise ValidationError('La delegación debe coincidir con la delegación del funcionario.')
        return cleaned_data
