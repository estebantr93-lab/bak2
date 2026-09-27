from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from core.admin_utils import es_usuario_sin_restriccion, filtrar_por_delegacion, get_usuario_delegacion
from funcionarios.models import Employee

from .models import Commitment


class CommitmentForm(forms.ModelForm):
    class Meta:
        model = Commitment
        fields = ['title', 'description', 'delegation', 'responsible', 'due_date', 'status', 'notes']
        labels = {
            'title': 'Título', 'description': 'Descripción', 'delegation': 'Delegación',
            'responsible': 'Responsable', 'due_date': 'Fecha de vencimiento', 'status': 'Estado',
            'notes': 'Observaciones',
        }
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'description': forms.Textarea(attrs={'rows': 2}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['responsible'].queryset = filtrar_por_delegacion(
            Employee.objects.filter(is_active=True), user,
        ).select_related('delegation')
        self.fields['responsible'].empty_label = 'Sin asignar'
        if not es_usuario_sin_restriccion(user):
            # Un usuario acotado solo crea compromisos de su propia delegación: el campo no se muestra.
            del self.fields['delegation']
            self.instance.delegation = get_usuario_delegacion(user)

    def clean_title(self):
        titulo = ' '.join(self.cleaned_data['title'].split())
        if len(titulo) < 5:
            raise ValidationError('El título debe tener al menos 5 caracteres.')
        return titulo

    def clean_due_date(self):
        vence = self.cleaned_data['due_date']
        # Un compromiso nuevo no puede nacer vencido; al editar se permite mantener la fecha original.
        if self.instance.pk is None and vence < timezone.localdate():
            raise ValidationError('La fecha de vencimiento no puede estar en el pasado.')
        return vence
