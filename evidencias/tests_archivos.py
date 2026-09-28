"""Integridad de los archivos de evidencias: PDF de ejemplo válido, detección de archivos
faltantes o dañados, comando revisar_archivos y aviso en el listado."""
import io
import shutil
import tempfile

from django.core.files.base import ContentFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from actividades.models import Activity
from core.testing import CLAVE_TEST, sembrar_datos_demo

from .archivos import es_pdf_valido, pdf_de_texto, png_de_texto, problema_del_archivo
from .models import Evidence

MEDIA_TEMPORAL = tempfile.mkdtemp()


class PdfDeEjemploTests(TestCase):
    def test_pdf_generado_tiene_pagina_xref_y_desplazamientos_correctos(self):
        datos = pdf_de_texto(['Acta de respaldo VOL-00001', 'Texto (con paréntesis)'])
        self.assertTrue(es_pdf_valido(datos))
        # Cada entrada de la tabla xref apunta exactamente al inicio de su objeto.
        inicio_xref = int(datos.rsplit(b'startxref\n', 1)[1].split(b'\n')[0])
        self.assertTrue(datos[inicio_xref:].startswith(b'xref'))
        entradas = datos[inicio_xref:].split(b'\n')[3:8]
        for numero, entrada in enumerate(entradas, start=1):
            desplazamiento = int(entrada.split()[0])
            self.assertTrue(datos[desplazamiento:].startswith(f'{numero} 0 obj'.encode()))

    def test_pdf_antiguo_de_la_carga_se_reconoce_como_danado(self):
        self.assertFalse(es_pdf_valido(b'%PDF-1.4\n% SGR\nActa de respaldo VOL-1\n%%EOF\n'))


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class RevisarArchivosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        sembrar_datos_demo()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_TEMPORAL, ignore_errors=True)

    def crear(self, codigo, nombre, contenido):
        actividad = Activity.objects.filter(delegation__name='Delegación Centro').first()
        evidencia = Evidence.objects.create(unique_code=codigo, activity=actividad, description='Respaldo')
        evidencia.file.save(nombre, ContentFile(contenido))
        return evidencia

    def ejecutar(self, *args):
        salida = io.StringIO()
        call_command('revisar_archivos', *args, stdout=salida)
        return salida.getvalue()

    def test_detecta_faltantes_danados_y_huerfanos(self):
        buena = self.crear('EVI-OK', 'a.png', png_de_texto('ok', (173, 0, 0)))
        danado = self.crear('EVI-VOL-000001', 'b.pdf', b'%PDF-1.4\nsin paginas\n%%EOF\n')
        faltante = self.crear('EVI-USR-1', 'c.png', png_de_texto('x', (0, 0, 0)))
        faltante.file.storage.delete(faltante.file.name)
        huerfano = Evidence._meta.get_field('file').storage.save('evidencias/huerfano.png', ContentFile(b'x'))

        self.assertIsNone(problema_del_archivo(buena.file))
        self.assertIn('PDF dañado', problema_del_archivo(danado.file))
        self.assertIn('no existe', problema_del_archivo(faltante.file))

        salida = self.ejecutar()
        self.assertIn('Con problemas: 2', salida)
        self.assertIn('Archivos huérfanos (sin evidencia): 1', salida)
        self.assertTrue(Evidence._meta.get_field('file').storage.exists(huerfano))  # sin opciones no borra

    def test_reparar_solo_regenera_archivos_de_ejemplo_y_borra_huerfanos(self):
        danado = self.crear('EVI-VOL-000002', 'd.pdf', b'%PDF-1.4\n%%EOF\n')
        de_usuario = self.crear('EVI-USR-2', 'e.pdf', b'%PDF-1.4\n%%EOF\n')
        storage = Evidence._meta.get_field('file').storage
        huerfano = storage.save('evidencias/huerfano2.png', ContentFile(b'x'))

        salida = self.ejecutar('--reparar', '--borrar-huerfanos')

        danado.refresh_from_db()
        self.assertIsNone(problema_del_archivo(danado.file))
        # El archivo subido por un usuario no se inventa: se informa para volver a subirlo.
        self.assertIsNotNone(problema_del_archivo(de_usuario.file))
        self.assertIn('EVI-USR-2', salida)
        self.assertFalse(storage.exists(huerfano))

    def test_listado_avisa_archivo_no_disponible(self):
        evidencia = self.crear('EVI-USR-3', 'f.png', png_de_texto('x', (0, 0, 0)))
        evidencia.file.storage.delete(evidencia.file.name)
        self.client.login(username='admin_centro', password=CLAVE_TEST)
        response = self.client.get(reverse('evidencia_list'), {'q': 'EVI-USR-3'})
        self.assertContains(response, 'Archivo no disponible')
        self.assertNotContains(response, f'src="{evidencia.file.url}"')
