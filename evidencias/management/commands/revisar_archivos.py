"""Revisa los archivos de evidencias: faltantes, dañados y huérfanos.

    python manage.py revisar_archivos                    # solo informa
    python manage.py revisar_archivos --reparar          # regenera los archivos de ejemplo dañados o faltantes
    python manage.py revisar_archivos --borrar-huerfanos # borra archivos que ninguna evidencia usa

--reparar solo toca evidencias de la carga de volumen (código EVI-VOL-…): son archivos de ejemplo.
Los archivos subidos por usuarios nunca se reemplazan; se informan para que se vuelvan a subir.
"""
import os
import random

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from core.volume_data import COLORES, PREFIJO, pdf_de_acta
from evidencias.archivos import png_de_texto, problema_del_archivo
from evidencias.models import Evidence

PREFIJO_DEMO = f'EVI-{PREFIJO}'
CARPETA = 'evidencias'


class Command(BaseCommand):
    help = 'Revisa los archivos de evidencias (faltantes, dañados y huérfanos) y opcionalmente los repara.'

    def add_arguments(self, parser):
        parser.add_argument('--reparar', action='store_true',
                            help='Regenera los archivos de ejemplo (EVI-VOL-…) dañados o faltantes.')
        parser.add_argument('--borrar-huerfanos', action='store_true',
                            help='Borra los archivos de la carpeta de evidencias que ninguna evidencia usa.')

    def handle(self, *args, **opciones):
        evidencias = Evidence.all_objects.exclude(file='').exclude(file__isnull=True).select_related('activity')
        problemas = []
        usados = set()
        for evidencia in evidencias:
            usados.add(evidencia.file.name)
            problema = problema_del_archivo(evidencia.file)
            if problema:
                problemas.append((evidencia, problema))

        huerfanos = sorted(self._archivos_en_disco() - usados)

        self.stdout.write(f'Evidencias con archivo: {len(usados)}')
        self.stdout.write(f'Con problemas: {len(problemas)}')
        for evidencia, problema in problemas[:20]:
            self.stdout.write(f'  - {evidencia.unique_code} ({evidencia.file.name}): {problema}')
        if len(problemas) > 20:
            self.stdout.write(f'  … y {len(problemas) - 20} más')
        self.stdout.write(f'Archivos huérfanos (sin evidencia): {len(huerfanos)}')

        if opciones['reparar']:
            self._reparar(problemas)
        if opciones['borrar_huerfanos']:
            storage = Evidence._meta.get_field('file').storage
            for nombre in huerfanos:
                storage.delete(nombre)
            self.stdout.write(self.style.SUCCESS(f'Huérfanos borrados: {len(huerfanos)}'))

        if not opciones['reparar'] and not opciones['borrar_huerfanos'] and (problemas or huerfanos):
            self.stdout.write('Use --reparar y/o --borrar-huerfanos para corregirlos.')

    def _archivos_en_disco(self):
        raiz = os.path.join(settings.MEDIA_ROOT, CARPETA)
        encontrados = set()
        for carpeta, _, archivos in os.walk(raiz):
            for archivo in archivos:
                ruta = os.path.relpath(os.path.join(carpeta, archivo), settings.MEDIA_ROOT)
                encontrados.add(ruta.replace(os.sep, '/'))
        return encontrados

    def _reparar(self, problemas):
        rng = random.Random(len(problemas))
        reparados, de_usuarios = 0, []
        for evidencia, _ in problemas:
            if not evidencia.unique_code.startswith(PREFIJO_DEMO):
                de_usuarios.append(evidencia.unique_code)
                continue
            nombre = evidencia.file.name
            if nombre.lower().endswith('.pdf'):
                contenido = pdf_de_acta(evidencia.activity.number)
            else:
                contenido = png_de_texto(evidencia.activity.number, rng.choice(COLORES))
            storage = evidencia.file.storage
            storage.delete(nombre)
            guardado = storage.save(nombre, ContentFile(contenido))
            if guardado != nombre:
                # El almacenamiento eligió otro nombre: se actualiza sin pasar por save()/señales.
                Evidence.all_objects.filter(pk=evidencia.pk).update(file=guardado)
            reparados += 1
        self.stdout.write(self.style.SUCCESS(f'Archivos de ejemplo regenerados: {reparados}'))
        if de_usuarios:
            self.stdout.write(self.style.WARNING(
                f'{len(de_usuarios)} archivo(s) subidos por usuarios no se pueden regenerar; '
                f'deben volver a subirse: {", ".join(de_usuarios[:10])}'
            ))
