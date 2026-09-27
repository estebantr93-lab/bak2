from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError

from .models import Meta as MetaModel


class MetaForm(forms.ModelForm):
    class Meta:
        model = MetaModel
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        ponderador = cleaned_data.get('ponderador')
        cargo = cleaned_data.get('cargo')
        periodo = cleaned_data.get('periodo')

        # Meta > 0 y ponderador > 0 los valida Meta.clean(); aquí solo la regla entre registros.
        if cargo and periodo and ponderador is not None and ponderador > 0:
            otras = MetaModel.objects.filter(cargo=cargo, periodo=periodo).exclude(pk=self.instance.pk)
            suma = sum((m.ponderador for m in otras), Decimal('0')) + ponderador
            if suma > 100:
                raise ValidationError(
                    f'La suma de ponderadores para este cargo y período no puede superar 100% (quedaría en {suma}%).'
                )
        return cleaned_data
