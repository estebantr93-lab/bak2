"""Validación de los archivos subidos y entrega protegida (evidencias es el único módulo con archivos).

Actividades, compromisos, atenciones y validaciones no reciben archivos: el respaldo de cada uno es
una evidencia. Por eso todas las reglas viven en evidencias/archivos.py y las usan la web y el Admin.
"""
import io
import shutil
import struct
import tempfile
import zlib

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from actividades.models import Activity
from core.testing import SesionTestMixin, sembrar_datos_demo

from .archivos import pdf_de_texto, validar_archivo_subido
from .forms import EvidenciaAdminForm
from .models import Evidence

MEDIA_TEMPORAL = tempfile.mkdtemp()


def imagen(formato='PNG', tamano=(20, 20), **opciones):
    buffer = io.BytesIO()
    Image.new('RGB', tamano, (173, 0, 0)).save(buffer, format=formato, **opciones)
    return buffer.getvalue()


def jpeg_con_gps():
    exif = Image.Exif()
    exif[0x8825] = {1: 'S', 2: (29.0, 54.0, 0.0), 3: 'W', 4: (71.0, 15.0, 0.0)}  # GPSInfo: La Serena
    return imagen('JPEG', exif=exif.tobytes())


def png_que_declara(ancho, alto):
    """PNG de pocos bytes cuya cabecera declara otro tamaño (no se crea la imagen real)."""
    datos = bytearray(imagen('PNG', (1, 1)))
    ihdr = struct.pack('>II', ancho, alto) + bytes(datos[24:29])
    datos[16:29] = ihdr
    datos[29:33] = struct.pack('>I', zlib.crc32(b'IHDR' + ihdr) & 0xffffffff)
    return bytes(datos)


def pdf_con(objeto_extra, comprimido=False):
    """PDF válido de una página con un objeto adicional (en claro o dentro de un flujo Flate)."""
    base = pdf_de_texto(['Acta'])
    if comprimido:
        flujo = zlib.compress(objeto_extra)
        objeto_extra = b'<< /Type /ObjStm /Filter /FlateDecode /Length ' + str(len(flujo)).encode() + b' >>\nstream\n' + flujo + b'\nendstream'
    inicio = base.index(b'xref')
    return base[:inicio] + b'9 0 obj\n' + objeto_extra + b'\nendobj\n' + base[inicio:]


def subido(nombre, datos):
    return SimpleUploadedFile(nombre, datos)


class ReglasDelArchivoTests(TestCase):
    def rechaza(self, nombre, datos, texto):
        with self.assertRaises(ValidationError) as error:
            validar_archivo_subido(subido(nombre, datos))
        self.assertIn(texto, ' '.join(error.exception.messages))

    def test_acepta_jpg_png_y_pdf_reales(self):
        for nombre, datos in (('a.jpg', imagen('JPEG')), ('a.jpeg', imagen('JPEG')), ('a.png', imagen('PNG')),
                              ('a.pdf', pdf_de_texto(['Acta de respaldo']))):
            with self.subTest(nombre=nombre):
                self.assertTrue(validar_archivo_subido(subido(nombre, datos)).size > 0)

    def test_tamano_extension_y_archivo_vacio(self):
        self.rechaza('a.pdf', b'', 'vacío')
        self.rechaza('a.pdf', b'%PDF-' + b'0' * (2 * 1024 * 1024), '2 MB')
        for nombre in ('a.exe', 'a.html', 'a.svg', 'a.gif', 'a.php.jpg.exe', 'sin_extension'):
            self.rechaza(nombre, imagen('PNG'), 'no permitido')

    def test_el_contenido_debe_coincidir_con_la_extension(self):
        self.rechaza('foto.png', imagen('JPEG'), 'no coincide con la extensión')
        self.rechaza('foto.jpg', imagen('PNG'), 'no coincide con la extensión')
        self.rechaza('foto.png', imagen('GIF'), 'no coincide con la extensión')
        self.rechaza('foto.jpg', b'<html><script>alert(1)</script>', 'no es una imagen válida')
        self.rechaza('acta.pdf', imagen('PNG'), 'no es un PDF válido')

    def test_pdf_falso_o_incompleto_se_rechaza(self):
        self.rechaza('acta.pdf', b'%PDF-1.4\n%%EOF', 'no es un PDF válido')  # sin páginas ni xref
        self.rechaza('acta.pdf', b'%PDF-1.4\n<html>hola</html>', 'no es un PDF válido')

    def test_imagen_enorme_se_rechaza_sin_procesarla(self):
        self.rechaza('foto.png', png_que_declara(9000, 7000), '50 megapíxeles')
        self.rechaza('foto.png', png_que_declara(20000, 20000), '50 megapíxeles')

    def test_la_foto_se_guarda_sin_metadatos_ni_contenido_agregado(self):
        limpia = validar_archivo_subido(subido('foto.jpg', jpeg_con_gps()))
        self.assertNotIn(0x8825, Image.open(limpia).getexif())  # sin la ubicación GPS
        limpia.seek(0)
        poliglota = imagen('PNG') + b'<?php system($_GET["c"]); ?>'
        limpia = validar_archivo_subido(subido('foto.png', poliglota))
        self.assertNotIn(b'<?php', limpia.read())

    def test_pdf_con_codigo_o_archivos_incrustados_se_rechaza(self):
        for objeto in (b'<< /S /JavaScript /JS (app.alert(1)) >>', b'<< /S /Launch /F (cmd.exe) >>',
                       b'<< /EmbeddedFiles 10 0 R >>', b'<< /S /J#61vaScript /J#53 (x) >>'):
            with self.subTest(objeto=objeto):
                self.rechaza('acta.pdf', pdf_con(objeto), 'código o archivos incrustados')
        # Oculto en un flujo comprimido (/ObjStm), como guardan los PDF de Word o del navegador.
        self.rechaza('acta.pdf', pdf_con(b'<< /S /JavaScript /JS (app.alert(1)) >>', comprimido=True), 'código')

    def test_pdf_cifrado_se_rechaza(self):
        self.rechaza('acta.pdf', pdf_con(b'<< /Filter /Standard /V 1 >>').replace(b'/Root 1 0 R', b'/Root 1 0 R /Encrypt 9 0 R'), 'cifrado')

    def test_flujos_comprimidos_normales_se_aceptan(self):
        self.assertTrue(validar_archivo_subido(subido('acta.pdf', pdf_con(b'<< /Type /Metadata >>', comprimido=True))))

    def test_el_admin_aplica_las_mismas_reglas(self):
        form = EvidenciaAdminForm(data={'status': 'pending'}, files={'file': subido('foto.png', imagen('JPEG'))})
        self.assertFalse(form.is_valid())
        self.assertIn('no coincide con la extensión', str(form.errors['file']))


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class EntregaProtegidaTests(SesionTestMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        sembrar_datos_demo()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_TEMPORAL, ignore_errors=True)

    def setUp(self):
        self.ingresar('admin_centro')
        actividad = Activity.objects.filter(delegation__name='Delegación Centro', period__is_closed=False).first()
        respuesta = self.client.post(reverse('evidencia_create'), {
            'activity': actividad.pk, 'description': 'Respaldo protegido', 'file': subido('foto.jpg', jpeg_con_gps())})
        self.assertEqual(respuesta.status_code, 302)
        self.evidencia = Evidence.objects.get(description='Respaldo protegido')
        self.url = self.evidencia.file.url
        self.client.logout()

    def test_la_url_del_archivo_pasa_por_la_vista_protegida(self):
        self.assertTrue(self.url.startswith('/archivos/evidencias/'))
        self.assertEqual(self.client.get(self.url.replace('/archivos/', '/media/')).status_code, 404)

    def test_anonimo_va_al_login(self):
        respuesta = self.client.get(self.url)
        self.assertRedirects(respuesta, f"{reverse('login')}?next={self.url}", fetch_redirect_response=False)

    def test_misma_delegacion_y_verificador_lo_ven(self):
        for usuario in ('admin_centro', 'funcionario_centro', 'verificador_leia', 'admin_sgr'):
            with self.subTest(usuario=usuario):
                self.ingresar(usuario)
                respuesta = self.client.get(self.url)
                self.assertEqual(respuesta.status_code, 200)
                self.assertEqual(respuesta['Content-Type'], 'image/jpeg')
                self.assertEqual(respuesta['X-Content-Type-Options'], 'nosniff')
                self.assertIn('no-store', respuesta['Cache-Control'])
                self.assertIn(self.evidencia.unique_code, respuesta['Content-Disposition'])
                self.assertNotIn(0x8825, Image.open(io.BytesIO(b''.join(respuesta.streaming_content))).getexif())

    def test_otra_delegacion_recibe_404_aunque_tenga_el_enlace(self):
        for usuario in ('admin_norte', 'funcionario_norte'):
            with self.subTest(usuario=usuario):
                self.ingresar(usuario)
                self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_evidencia_eliminada_solo_la_ve_el_administrador_general(self):
        self.evidencia.delete()
        self.ingresar('admin_centro')
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.ingresar('admin_sgr')
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_nombres_inventados_o_rutas_del_disco_dan_404(self):
        self.ingresar('admin_sgr')
        for ruta in ('/archivos/evidencias/no-existe.jpg', '/archivos/../config/settings.py',
                     '/archivos/%2e%2e/%2e%2e/etc/passwd', '/archivos/' + self.evidencia.file.name + '.html'):
            with self.subTest(ruta=ruta):
                self.assertEqual(self.client.get(ruta).status_code, 404)
