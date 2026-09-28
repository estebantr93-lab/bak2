import os

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from PIL import Image, UnidentifiedImageError

from actividades.models import Activity
from core.admin_utils import ROL_VERIFICADOR, filtrar_por_delegacion, get_rol, modificables

from .models import EXTENSIONES_IMAGEN, Evidence
from .services import ESTADOS_REVISION, registrar_revision

EXTENSIONES_PERMITIDAS = EXTENSIONES_IMAGEN | {'.pdf'}
# Lo único que cambia el verificador al revisar: no reasigna la evidencia ni reemplaza el archivo.
CAMPOS_REVISION = ('status', 'result')


class ReglasEvidenciaMixin:
    """Reglas de una evidencia que valen en la web y en el Admin (formulario e inline)."""

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
            except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError):
                # DecompressionBombError: pocos KB que declaran millones de píxeles (agotaría la memoria).
                raise ValidationError('El archivo no es una imagen válida.')
            if imagen.format not in ('JPEG', 'PNG'):
                raise ValidationError('La imagen debe ser JPG o PNG.')
        elif archivo.read(5) != b'%PDF-':
            raise ValidationError('El archivo no es un PDF válido.')
        archivo.seek(0)
        return archivo

    def clean(self):
        cleaned_data = super().clean()
        # Un rechazo sin motivo deja al funcionario sin saber qué corregir.
        if cleaned_data.get('status') == 'rejected' and not (cleaned_data.get('result') or '').strip():
            self.add_error('result', 'Indique el motivo del rechazo para que el funcionario pueda corregirla.')
        return cleaned_data


class EvidenciaForm(ReglasEvidenciaMixin, forms.ModelForm):
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
        self.fields['activity'].queryset = modificables(
            filtrar_por_delegacion(Activity.objects.select_related('delegation'), user), user,
        )
        self.fields['activity'].empty_label = 'Seleccione…'
        # Al crear, el archivo es obligatorio; al editar se puede conservar el actual.
        self.fields['file'].required = self.instance.pk is None
        # El estado solo lo cambia quien puede aprobar, y solo al revisar una evidencia existente.
        if self.instance.pk is None or user is None or not user.has_perm('evidencias.can_approve_evidence'):
            del self.fields['status']
            del self.fields['result']
        elif get_rol(user) == ROL_VERIFICADOR:
            # El verificador revisa: no reasigna la evidencia ni reemplaza el archivo del funcionario.
            # El archivo se quita del formulario (deshabilitado, Django lo leería del disco y fallaría
            # si falta); la actividad y la descripción se muestran sin poder editarlas.
            del self.fields['file']
            for nombre in list(self.fields):
                if nombre not in CAMPOS_REVISION:
                    self.fields[nombre].disabled = True

    def save(self, commit=True):
        evidencia = super().save(commit=commit)
        if commit and 'status' in self.fields and 'status' in self.changed_data and evidencia.status in ESTADOS_REVISION:
            registrar_revision(evidencia, self.user, evidencia.status, evidencia.result or 'Revisión desde el CRUD web.')
        return evidencia


class EvidenciaAdminForm(ReglasEvidenciaMixin, forms.ModelForm):
    """Formulario del Admin (y de la evidencia en línea dentro de una actividad): mismas reglas que la web."""

    class Meta:
        model = Evidence
        fields = '__all__'
