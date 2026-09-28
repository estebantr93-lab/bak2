from django import forms
from django.core.exceptions import ValidationError

from .models import Activity, SocialCase


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
            'action', 'contact', 'phone', 'is_agenda_item',
        ]  # evidence_code no: lo genera el sistema y es inmutable (RN-010 / RF-011)
        labels = {
            'number': 'Número', 'period': 'Período', 'activity_type': 'Tipo de actividad',
            'description': 'Descripción', 'action': 'Acción', 'phone': 'Teléfono',
            'is_agenda_item': 'Indicador de agenda',
        }
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        from core.admin_utils import ROL_FUNCIONARIO, filtrar_por_delegacion, get_rol, modificables
        from core.models import Period, ActivityType
        from funcionarios.models import Employee

        # Política única (core/admin_utils.modificables): un funcionario solo puede elegirse a sí mismo.
        funcionarios = modificables(filtrar_por_delegacion(Employee.objects.filter(is_active=True), user), user)
        if get_rol(user) == ROL_FUNCIONARIO:
            self.fields['employee'].initial = funcionarios.first()
        self.fields['employee'].queryset = funcionarios.select_related('delegation')
        self.fields['period'].queryset = Period.objects.filter(is_closed=False)
        self.fields['period'].required = True  # sin período se podría esquivar el cierre
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


class SocialCaseForm(forms.ModelForm):
    """Gestiones (1 a 3) de una actividad de atención social. Rango, máximo por actividad y
    categoría social se validan en el modelo; aquí solo se acota lo que el usuario puede elegir."""

    class Meta:
        model = SocialCase
        fields = ['activity', 'step_number', 'date', 'description', 'result']
        labels = {'activity': 'Actividad', 'step_number': 'Número de gestión (1 a 3)', 'date': 'Fecha de la gestión',
                  'description': 'Descripción', 'result': 'Resultado'}
        widgets = {'description': forms.Textarea(attrs={'rows': 3}),
                   'date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d')}

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        from core.admin_utils import filtrar_por_delegacion, modificables

        actividades = Activity.objects.filter(activity_type__category='social').select_related('delegation')
        self.fields['activity'].queryset = modificables(filtrar_por_delegacion(actividades, user), user)
        self.fields['activity'].empty_label = 'Seleccione…'

    def clean(self):
        cleaned_data = super().clean()
        actividad, paso = cleaned_data.get('activity'), cleaned_data.get('step_number')
        if self.instance.pk is None and actividad and paso:
            # La fila eliminada lógicamente sigue ocupando (actividad, número) en la BD: se reactiva
            # con los datos nuevos en vez de rechazar el registro con «ya existe».
            eliminada = SocialCase.all_objects.filter(activity=actividad, step_number=paso, deleted_at__isnull=False).first()
            if eliminada:
                eliminada.deleted_at = None
                self.instance = eliminada
        return cleaned_data
