import os

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError

from .models import EXTENSIONES_IMAGEN, Evidencia

EXTENSIONES_PERMITIDAS = EXTENSIONES_IMAGEN | {'.pdf'}


class EvidenciaForm(forms.ModelForm):
    class Meta:
        model = Evidencia
        fields = ['descripcion', 'archivo']
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 2}),
            'archivo': forms.ClearableFileInput(attrs={'accept': '.jpg,.jpeg,.png,.pdf'}),
        }
        labels = {'descripcion': 'Descripción'}
        help_texts = {'archivo': 'JPG, PNG o PDF, máximo 2 MB.'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['archivo'].required = True

    def clean_archivo(self):
        archivo = self.cleaned_data.get('archivo')
        if not archivo:
            raise ValidationError('Debe adjuntar un archivo.')

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
