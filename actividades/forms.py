from django import forms
from django.core.exceptions import ValidationError

from .models import Activity


class ActividadForm(forms.ModelForm):
    """Formulario del Admin. Las reglas de negocio están en Actividad.clean() y
    un ModelForm las ejecuta solo; repetirlas aquí mostraba cada error dos veces."""

    class Meta:
        model = Activity
        fields = '__all__'


class ActividadWebForm(ActividadForm):
    """ModelForm del CRUD fuera del Admin.

    La delegación se toma del funcionario y el estado de validación lo decide el
    verificador, por eso ninguno de los dos se edita aquí.
    """

    class Meta(ActividadForm.Meta):
        fields = [
            'number', 'employee', 'period', 'activity_type', 'date', 'description',
            'action', 'contact', 'phone', 'is_agenda_item', 'evidence_code',
        ]
        labels = {
            'number': 'Número', 'period': 'Período', 'activity_type': 'Tipo de actividad',
            'description': 'Descripción', 'action': 'Acción', 'phone': 'Teléfono',
            'is_agenda_item': 'Indicador de agenda', 'evidence_code': 'Código de evidencia',
        }
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        from core.admin_utils import ROL_FUNCIONARIO, filtrar_por_delegacion, get_rol
        from core.models import Period, ActivityType
        from funcionarios.models import Employee

        funcionarios = filtrar_por_delegacion(Employee.objects.filter(is_active=True), user)
        if get_rol(user) == ROL_FUNCIONARIO:
            # Un funcionario solo registra actividades propias.
            funcionarios = funcionarios.filter(user=user)
            self.fields['employee'].initial = funcionarios.first()
        self.fields['employee'].queryset = funcionarios.select_related('delegation')
        self.fields['period'].queryset = Period.objects.filter(is_closed=False)
        self.fields['activity_type'].queryset = ActivityType.objects.filter(is_active=True)
        for campo in ('employee', 'period', 'activity_type'):
            self.fields[campo].empty_label = 'Seleccione…'

    def clean_number(self):
        # Regla de un solo campo: normaliza y evita duplicados (también contra actividades eliminadas,
        # porque el número sigue ocupado en la base de datos).
        numero = self.cleaned_data['number'].strip().upper()
        duplicado = Activity.all_objects.filter(number__iexact=numero).exclude(pk=self.instance.pk)
        if duplicado.exists():
            raise ValidationError('Ya existe una actividad con este número.')
        return numero

    def clean(self):
        cleaned_data = super().clean()
        funcionario = cleaned_data.get('employee')
        if funcionario is not None:
            self.instance.delegation = funcionario.delegation
        return cleaned_data
