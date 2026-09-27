import os

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from PIL import Image, UnidentifiedImageError

from actividades.models import Activity
from core.admin_utils import filtrar_por_delegacion

from .models import EXTENSIONES_IMAGEN, Evidence, Validation

EXTENSIONES_PERMITIDAS = EXTENSIONES_IMAGEN | {'.pdf'}


class EvidenciaForm(forms.ModelForm):
    """Carga/edición de evidencias. El verificador (permiso can_approve_evidence) además
    puede cambiar el estado; al hacerlo queda registrado quién revisó y una Validation."""

    class Meta:
        model = Evidence
        fields = ['activity', 'description', 'file', 'status', 'result']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 2}),
            'file': forms.ClearableFileInput(attrs={'accept': '.jpg,.jpeg,.png,.pdf'}),
        }
        labels = {'activity': 'Actividad', 'description': 'Descripción', 'file': 'Archivo',
                  'status': 'Estado', 'result': 'Resultado de la revisión'}
        help_texts = {'file': 'JPG, PNG o PDF, máximo 2 MB.'}

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields['activity'].queryset = filtrar_por_delegacion(
            Activity.objects.select_related('delegation'), user,
        )
        self.fields['activity'].empty_label = 'Seleccione…'
        # Al crear, el archivo es obligatorio; al editar se puede conservar el actual.
        self.fields['file'].required = self.instance.pk is None
        # El estado solo lo cambia quien puede aprobar, y solo al revisar una evidencia existente.
        if self.instance.pk is None or user is None or not user.has_perm('evidencias.can_approve_evidence'):
            del self.fields['status']
            del self.fields['result']

    def save(self, commit=True):
        evidencia = super().save(commit=False)
        revisa = 'status' in self.fields and 'status' in self.changed_data and evidencia.status != 'pending'
        if revisa:
            evidencia.reviewed_by = self.user
        if commit:
            evidencia.save()
            if revisa:
                Validation.objects.create(
                    evidence=evidencia, reviewer=self.user, status=evidencia.status,
                    comment=evidencia.result or 'Revisión desde el CRUD web.',
                )
        return evidencia

    def clean_file(self):
        archivo = self.cleaned_data.get('file')
        if archivo is False:  # casilla "Limpiar" de ClearableFileInput
            raise ValidationError('La evidencia debe conservar un archivo; para cambiarlo, adjunte uno nuevo.')
        if not archivo:
            if self.instance.pk is None:
                raise ValidationError('Debe adjuntar un archivo.')
            return archivo
        if not isinstance(archivo, UploadedFile):
            return archivo  # es el archivo ya guardado (no se reemplazó): no hay nada nuevo que validar

        maximo = settings.EVIDENCIA_TAMANO_MAXIMO_MB * 1024 * 1024
        if archivo.size > maximo:
            raise ValidationError(f'El archivo supera el máximo de {settings.EVIDENCIA_TAMANO_MAXIMO_MB} MB.')

        extension = os.path.splitext(archivo.name)[1].lower()
        if extension not in EXTENSIONES_PERMITIDAS:
            raise ValidationError('Tipo de archivo no permitido. Use JPG, PNG o PDF.')

        # El contenido real debe coincidir con la extensión: no se confía en el nombre.
        if extension in EXTENSIONES_IMAGEN:
            try:
                imagen = Image.open(archivo)
                imagen.verify()
            except (UnidentifiedImageError, OSError, SyntaxError):
                raise ValidationError('El archivo no es una imagen válida.')
            if imagen.format not in ('JPEG', 'PNG'):
                raise ValidationError('La imagen debe ser JPG o PNG.')
        else:
            if archivo.read(5) != b'%PDF-':
                raise ValidationError('El archivo no es un PDF válido.')
        archivo.seek(0)
        return archivo
