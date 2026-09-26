from django import forms
from django.core.exceptions import ValidationError

from .models import Periodo


class PeriodoForm(forms.ModelForm):
    class Meta:
        model = Periodo
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        fecha_inicio = cleaned_data.get('fecha_inicio')
        fecha_termino = cleaned_data.get('fecha_termino')

        if fecha_inicio and fecha_termino:
            if fecha_inicio >= fecha_termino:
                raise ValidationError('La fecha de inicio debe ser anterior a la fecha de término.')
            solapados = Periodo.objects.filter(
                fecha_inicio__lte=fecha_termino, fecha_termino__gte=fecha_inicio,
            ).exclude(pk=self.instance.pk)
            if solapados.exists():
                raise ValidationError('El período se solapa con otro período ya existente.')
        return cleaned_data
