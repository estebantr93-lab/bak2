import io
import shutil
import tempfile
from io import StringIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from core.models import Periodo, TipoActividad
from evidencias.models import Evidencia
from funcionarios.models import Funcionario

from .models import Actividad

MEDIA_TEMPORAL = tempfile.mkdtemp()


def imagen_png(nombre='foto.png', tamano=(20, 20)):
    buffer = io.BytesIO()
    Image.new('RGB', tamano, 'red').save(buffer, format='PNG')
    return SimpleUploadedFile(nombre, buffer.getvalue(), content_type='image/png')


class BaseWeb(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_data', stdout=StringIO())
        cls.actividad_centro = Actividad.objects.filter(delegacion__nombre='Delegación Centro').first()
        cls.actividad_norte = Actividad.objects.filter(delegacion__nombre='Delegación Norte').first()

    def ingresar(self, username, password):
        self.assertTrue(self.client.login(username=username, password=password))

    def datos(self, **extra):
        datos = {
            'numero': 'act-web-001',
            'funcionario': Funcionario.objects.get(nombre='Ana Pérez (Centro)').pk,
            'periodo': Periodo.objects.get(cerrado=False).pk,
            'tipo_actividad': TipoActividad.objects.get(codigo='ATC-01').pk,
            'fecha': '2026-07-15',
            'descripcion': 'Atención registrada desde el CRUD web.',
            'codigo_evidencia': 'EVID-WEB-001',
        }
        datos.update(extra)
        return datos


class ActividadCrudTests(BaseWeb):
    def test_anonimo_es_enviado_al_login(self):
        url = reverse('actividad_list')
        response = self.client.get(url)
        self.assertRedirects(response, reverse('login') + '?next=' + url)

    def test_sin_permiso_recibe_403(self):
        self.ingresar('verificador_leia', 'Verifica#2026SGR')
        self.assertEqual(self.client.get(reverse('actividad_list')).status_code, 403)

    def test_listado_respeta_scoping(self):
        self.ingresar('funcionario_centro', 'Centro#2026SGR')
        response = self.client.get(reverse('actividad_list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual({a.delegacion.nombre for a in response.context['actividades']}, {'Delegación Centro'})
        self.assertNotContains(response, self.actividad_norte.numero)

    def test_page_size_se_guarda_en_la_sesion(self):
        self.ingresar('admin_sgr', 'Admin#2026SGR')
        self.client.get(reverse('actividad_list'), {'page_size': 10})
        self.assertEqual(self.client.session['actividades_page_size'], 10)
        response = self.client.get(reverse('actividad_list'))
        self.assertEqual(response.context['page_size'], 10)
        # Un valor no permitido no cambia la preferencia.
        self.client.get(reverse('actividad_list'), {'page_size': 9999})
        self.assertEqual(self.client.session['actividades_page_size'], 10)

    def test_crear_actividad(self):
        self.ingresar('funcionario_centro', 'Centro#2026SGR')
        response = self.client.post(reverse('actividad_create'), self.datos(), follow=True)
        self.assertRedirects(response, reverse('actividad_list'))
        actividad = Actividad.objects.get(numero='ACT-WEB-001')  # clean_numero normaliza a mayúsculas
        self.assertEqual(actividad.delegacion.nombre, 'Delegación Centro')
        self.assertEqual(actividad.estado_validacion, 'pendiente')
        self.assertContains(response, 'registrada correctamente')

    def test_formulario_invalido_reabre_el_modal_con_errores(self):
        self.ingresar('funcionario_centro', 'Centro#2026SGR')
        response = self.client.post(reverse('actividad_create'), self.datos(numero=self.actividad_centro.numero.lower()))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['modal_abierto'])
        self.assertIn('numero', response.context['form'].errors)

    def test_funcionario_no_puede_registrar_a_nombre_de_otro(self):
        self.ingresar('funcionario_centro', 'Centro#2026SGR')
        otro = Funcionario.objects.get(nombre='María Soto (Admin Centro)')
        response = self.client.post(reverse('actividad_create'), self.datos(funcionario=otro.pk))
        self.assertIn('funcionario', response.context['form'].errors)

    def test_no_permite_periodo_cerrado(self):
        self.ingresar('admin_centro', 'AdminCentro#2026SGR')
        cerrado = Periodo.objects.get(cerrado=True)
        response = self.client.post(reverse('actividad_create'), self.datos(periodo=cerrado.pk))
        self.assertIn('periodo', response.context['form'].errors)

    def test_editar_actividad_propia(self):
        self.ingresar('admin_centro', 'AdminCentro#2026SGR')
        url = reverse('actividad_update', args=[self.actividad_centro.pk])
        self.assertTrue(self.client.get(url).context['modal_abierto'])
        datos = self.datos(
            numero=self.actividad_centro.numero, codigo_evidencia=self.actividad_centro.codigo_evidencia,
            descripcion='Descripción editada',
        )
        response = self.client.post(url, datos)
        self.assertRedirects(response, reverse('actividad_list'))
        self.actividad_centro.refresh_from_db()
        self.assertEqual(self.actividad_centro.descripcion, 'Descripción editada')

    def test_no_puede_editar_actividad_de_otra_delegacion(self):
        self.ingresar('admin_centro', 'AdminCentro#2026SGR')
        response = self.client.get(reverse('actividad_update', args=[self.actividad_norte.pk]))
        self.assertEqual(response.status_code, 404)

    def test_eliminar_solo_por_post(self):
        self.ingresar('admin_centro', 'AdminCentro#2026SGR')
        url = reverse('actividad_delete', args=[self.actividad_centro.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
        response = self.client.post(url)
        self.assertRedirects(response, reverse('actividad_list'))
        self.assertFalse(Actividad.objects.filter(pk=self.actividad_centro.pk).exists())

    def test_funcionario_no_tiene_permiso_de_eliminar_aunque_conozca_la_url(self):
        self.ingresar('funcionario_centro', 'Centro#2026SGR')
        response = self.client.post(reverse('actividad_delete', args=[self.actividad_centro.pk]))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Actividad.objects.filter(pk=self.actividad_centro.pk).exists())

    def test_admin_no_puede_eliminar_actividad_de_otra_delegacion(self):
        self.ingresar('admin_centro', 'AdminCentro#2026SGR')
        response = self.client.post(reverse('actividad_delete', args=[self.actividad_norte.pk]))
        self.assertEqual(response.status_code, 404)


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class EvidenciaArchivoTests(BaseWeb):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_TEMPORAL, ignore_errors=True)

    def subir(self, archivo, actividad=None):
        actividad = actividad or self.actividad_centro
        return self.client.post(
            reverse('evidencias_actividad', args=[actividad.pk]), {'descripcion': 'Foto', 'archivo': archivo},
        )

    def test_sube_imagen_valida_con_nombre_seguro(self):
        self.ingresar('funcionario_centro', 'Centro#2026SGR')
        response = self.subir(imagen_png('../../peligroso nombre.png'))
        self.assertRedirects(response, reverse('evidencias_actividad', args=[self.actividad_centro.pk]))
        evidencia = Evidencia.objects.filter(actividad=self.actividad_centro).exclude(archivo='').get()
        self.assertTrue(evidencia.archivo.name.startswith('evidencias/'))
        self.assertNotIn('peligroso', evidencia.archivo.name)
        self.assertNotIn('..', evidencia.archivo.name)
        self.assertTrue(evidencia.es_imagen)

    def test_rechaza_extension_no_permitida(self):
        self.ingresar('funcionario_centro', 'Centro#2026SGR')
        response = self.subir(SimpleUploadedFile('script.exe', b'MZ...'))
        self.assertIn('archivo', response.context['form'].errors)

    def test_rechaza_contenido_falso_con_extension_de_imagen(self):
        self.ingresar('funcionario_centro', 'Centro#2026SGR')
        response = self.subir(SimpleUploadedFile('falsa.png', b'esto no es una imagen'))
        self.assertIn('no es una imagen', str(response.context['form'].errors))

    def test_rechaza_archivo_mayor_a_2mb(self):
        self.ingresar('funcionario_centro', 'Centro#2026SGR')
        grande = SimpleUploadedFile('grande.pdf', b'%PDF-' + b'0' * (2 * 1024 * 1024))
        response = self.subir(grande)
        self.assertIn('2 MB', str(response.context['form'].errors))

    def test_acepta_pdf_valido(self):
        self.ingresar('funcionario_centro', 'Centro#2026SGR')
        response = self.subir(SimpleUploadedFile('acta.pdf', b'%PDF-1.4\n%%EOF'))
        self.assertEqual(response.status_code, 302)

    def test_no_puede_subir_a_actividad_de_otra_delegacion(self):
        self.ingresar('funcionario_centro', 'Centro#2026SGR')
        response = self.subir(imagen_png(), actividad=self.actividad_norte)
        self.assertEqual(response.status_code, 404)

    def test_eliminar_borra_el_archivo_fisico(self):
        self.ingresar('admin_centro', 'AdminCentro#2026SGR')
        self.subir(imagen_png())
        evidencia = Evidencia.objects.filter(actividad=self.actividad_centro).exclude(archivo='').get()
        storage, nombre = evidencia.archivo.storage, evidencia.archivo.name
        self.assertTrue(storage.exists(nombre))
        response = self.client.post(reverse('evidencia_delete', args=[evidencia.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(storage.exists(nombre))

    def test_funcionario_no_puede_eliminar_evidencia(self):
        self.ingresar('funcionario_centro', 'Centro#2026SGR')
        evidencia = Evidencia.objects.filter(actividad=self.actividad_centro).first()
        response = self.client.post(reverse('evidencia_delete', args=[evidencia.pk]))
        self.assertEqual(response.status_code, 403)
