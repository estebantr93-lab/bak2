from django import forms
from django.core.exceptions import ValidationError

from .models import Actividad


class ActividadForm(forms.ModelForm):
    """Formulario del Admin. Las reglas de negocio están en Actividad.clean() y
    un ModelForm las ejecuta solo; repetirlas aquí mostraba cada error dos veces."""

    class Meta:
        model = Actividad
        fields = '__all__'


class ActividadWebForm(ActividadForm):
    """ModelForm del CRUD fuera del Admin.

    La delegación se toma del funcionario y el estado de validación lo decide el
    verificador, por eso ninguno de los dos se edita aquí.
    """

    class Meta(ActividadForm.Meta):
        fields = [
            'numero', 'funcionario', 'periodo', 'tipo_actividad', 'fecha', 'descripcion',
            'accion', 'contacto', 'telefono', 'indicador_agenda', 'codigo_evidencia',
        ]
        labels = {
            'numero': 'Número', 'periodo': 'Período', 'tipo_actividad': 'Tipo de actividad',
            'descripcion': 'Descripción', 'accion': 'Acción', 'telefono': 'Teléfono',
            'indicador_agenda': 'Indicador de agenda', 'codigo_evidencia': 'Código de evidencia',
        }
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'descripcion': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        from core.admin_utils import ROL_FUNCIONARIO, filtrar_por_delegacion, get_rol
        from core.models import Periodo, TipoActividad
        from funcionarios.models import Funcionario

        funcionarios = filtrar_por_delegacion(Funcionario.objects.filter(activo=True), user)
        if get_rol(user) == ROL_FUNCIONARIO:
            # Un funcionario solo registra actividades propias.
            funcionarios = funcionarios.filter(user=user)
            self.fields['funcionario'].initial = funcionarios.first()
        self.fields['funcionario'].queryset = funcionarios.select_related('delegacion')
        self.fields['periodo'].queryset = Periodo.objects.filter(cerrado=False)
        self.fields['tipo_actividad'].queryset = TipoActividad.objects.filter(activo=True)
        for campo in ('funcionario', 'periodo', 'tipo_actividad'):
            self.fields[campo].empty_label = 'Seleccione…'

    def clean_numero(self):
        # Regla de un solo campo: normaliza y evita duplicados que solo difieren en mayúsculas.
        numero = self.cleaned_data['numero'].strip().upper()
        duplicado = Actividad.objects.filter(numero__iexact=numero).exclude(pk=self.instance.pk)
        if duplicado.exists():
            raise ValidationError('Ya existe una actividad con este número.')
        return numero

    def clean(self):
        cleaned_data = super().clean()
        funcionario = cleaned_data.get('funcionario')
        if funcionario is not None:
            self.instance.delegacion = funcionario.delegacion
        return cleaned_data
