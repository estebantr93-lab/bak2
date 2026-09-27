import io
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from core.models import Period, ActivityType
from evidencias.models import Evidence
from funcionarios.models import Employee
from core.testing import CLAVE_TEST, sembrar_datos_demo

from .models import Activity

MEDIA_TEMPORAL = tempfile.mkdtemp()


def imagen_png(nombre='foto.png', tamano=(20, 20)):
    buffer = io.BytesIO()
    Image.new('RGB', tamano, 'red').save(buffer, format='PNG')
    return SimpleUploadedFile(nombre, buffer.getvalue(), content_type='image/png')


class BaseWeb(TestCase):
    @classmethod
    def setUpTestData(cls):
        sembrar_datos_demo()
        cls.actividad_centro = Activity.objects.filter(delegation__name='Delegación Centro').first()
        cls.actividad_norte = Activity.objects.filter(delegation__name='Delegación Norte').first()

    def ingresar(self, username, password):
        self.assertTrue(self.client.login(username=username, password=password))

    def datos(self, **extra):
        datos = {
            'number': 'act-web-001',
            'employee': Employee.objects.get(name='Ana Pérez (Centro)').pk,
            'period': Period.objects.get(is_closed=False).pk,
            'activity_type': ActivityType.objects.get(code='ATC-01').pk,
            'date': '2026-07-15',
            'description': 'Atención registrada desde el CRUD web.',
            'evidence_code': 'EVID-WEB-001',
        }
        datos.update(extra)
        return datos


class ActividadCrudTests(BaseWeb):
    def test_anonimo_es_enviado_al_login(self):
        url = reverse('actividad_list')
        response = self.client.get(url)
        self.assertRedirects(response, reverse('login') + '?next=' + url)

    def test_sin_permiso_recibe_403(self):
        self.ingresar('verificador_leia', CLAVE_TEST)
        self.assertEqual(self.client.get(reverse('actividad_list')).status_code, 403)

    def test_listado_respeta_scoping(self):
        self.ingresar('funcionario_centro', CLAVE_TEST)
        response = self.client.get(reverse('actividad_list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual({a.delegation.name for a in response.context['activities']}, {'Delegación Centro'})
        self.assertNotContains(response, self.actividad_norte.number)

    def test_page_size_se_guarda_en_la_sesion(self):
        self.ingresar('admin_sgr', CLAVE_TEST)
        self.client.get(reverse('actividad_list'), {'page_size': 10})
        self.assertEqual(self.client.session['actividades_page_size'], 10)
        response = self.client.get(reverse('actividad_list'))
        self.assertEqual(response.context['page_size'], 10)
        # Un valor no permitido no cambia la preferencia.
        self.client.get(reverse('actividad_list'), {'page_size': 9999})
        self.assertEqual(self.client.session['actividades_page_size'], 10)

    def test_crear_actividad(self):
        self.ingresar('funcionario_centro', CLAVE_TEST)
        response = self.client.post(reverse('actividad_create'), self.datos(), follow=True)
        self.assertRedirects(response, reverse('actividad_list'))
        actividad = Activity.objects.get(number='ACT-WEB-001')  # clean_numero normaliza a mayúsculas
        self.assertEqual(actividad.delegation.name, 'Delegación Centro')
        self.assertEqual(actividad.validation_status, 'pending')
        self.assertContains(response, 'registrada correctamente')

    def test_formulario_invalido_reabre_el_modal_con_errores(self):
        self.ingresar('funcionario_centro', CLAVE_TEST)
        response = self.client.post(reverse('actividad_create'), self.datos(number=self.actividad_centro.number.lower()))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['modal_abierto'])
        self.assertIn('number', response.context['form'].errors)

    def test_funcionario_no_puede_registrar_a_nombre_de_otro(self):
        self.ingresar('funcionario_centro', CLAVE_TEST)
        otro = Employee.objects.get(name='María Soto (Admin Centro)')
        response = self.client.post(reverse('actividad_create'), self.datos(employee=otro.pk))
        self.assertIn('employee', response.context['form'].errors)

    def test_no_permite_periodo_cerrado(self):
        self.ingresar('admin_centro', CLAVE_TEST)
        cerrado = Period.objects.get(is_closed=True)
        response = self.client.post(reverse('actividad_create'), self.datos(period=cerrado.pk))
        self.assertIn('period', response.context['form'].errors)

    def test_editar_actividad_propia(self):
        self.ingresar('admin_centro', CLAVE_TEST)
        url = reverse('actividad_update', args=[self.actividad_centro.pk])
        self.assertTrue(self.client.get(url).context['modal_abierto'])
        datos = self.datos(
            number=self.actividad_centro.number, evidence_code=self.actividad_centro.evidence_code,
            description='Descripción editada',
        )
        response = self.client.post(url, datos)
        self.assertRedirects(response, reverse('actividad_list'))
        self.actividad_centro.refresh_from_db()
        self.assertEqual(self.actividad_centro.description, 'Descripción editada')

    def test_no_puede_editar_actividad_de_otra_delegacion(self):
        self.ingresar('admin_centro', CLAVE_TEST)
        response = self.client.get(reverse('actividad_update', args=[self.actividad_norte.pk]))
        self.assertEqual(response.status_code, 404)

    def test_eliminar_solo_por_post(self):
        self.ingresar('admin_centro', CLAVE_TEST)
        url = reverse('actividad_delete', args=[self.actividad_centro.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
        response = self.client.post(url)
        self.assertRedirects(response, reverse('actividad_list'))
        self.assertFalse(Activity.objects.filter(pk=self.actividad_centro.pk).exists())

    def test_funcionario_no_tiene_permiso_de_eliminar_aunque_conozca_la_url(self):
        self.ingresar('funcionario_centro', CLAVE_TEST)
        response = self.client.post(reverse('actividad_delete', args=[self.actividad_centro.pk]))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Activity.objects.filter(pk=self.actividad_centro.pk).exists())

    def test_admin_no_puede_eliminar_actividad_de_otra_delegacion(self):
        self.ingresar('admin_centro', CLAVE_TEST)
        response = self.client.post(reverse('actividad_delete', args=[self.actividad_norte.pk]))
        self.assertEqual(response.status_code, 404)


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class EvidenciaArchivoTests(BaseWeb):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_TEMPORAL, ignore_errors=True)

    def subir(self, archivo, activity=None):
        activity = activity or self.actividad_centro
        return self.client.post(
            reverse('evidencias_actividad', args=[activity.pk]), {'description': 'Foto', 'file': archivo},
        )

    def test_sube_imagen_valida_con_nombre_seguro(self):
        self.ingresar('funcionario_centro', CLAVE_TEST)
        response = self.subir(imagen_png('../../peligroso nombre.png'))
        self.assertRedirects(response, reverse('evidencias_actividad', args=[self.actividad_centro.pk]))
        evidencia = Evidence.objects.filter(activity=self.actividad_centro).exclude(file='').get()
        self.assertTrue(evidencia.file.name.startswith('evidencias/'))
        self.assertNotIn('peligroso', evidencia.file.name)
        self.assertNotIn('..', evidencia.file.name)
        self.assertTrue(evidencia.es_imagen)

    def test_rechaza_extension_no_permitida(self):
        self.ingresar('funcionario_centro', CLAVE_TEST)
        response = self.subir(SimpleUploadedFile('script.exe', b'MZ...'))
        self.assertIn('file', response.context['form'].errors)

    def test_rechaza_contenido_falso_con_extension_de_imagen(self):
        self.ingresar('funcionario_centro', CLAVE_TEST)
        response = self.subir(SimpleUploadedFile('falsa.png', b'esto no es una imagen'))
        self.assertIn('no es una imagen', str(response.context['form'].errors))

    def test_rechaza_archivo_mayor_a_2mb(self):
        self.ingresar('funcionario_centro', CLAVE_TEST)
        grande = SimpleUploadedFile('grande.pdf', b'%PDF-' + b'0' * (2 * 1024 * 1024))
        response = self.subir(grande)
        self.assertIn('2 MB', str(response.context['form'].errors))

    def test_acepta_pdf_valido(self):
        self.ingresar('funcionario_centro', CLAVE_TEST)
        response = self.subir(SimpleUploadedFile('acta.pdf', b'%PDF-1.4\n%%EOF'))
        self.assertEqual(response.status_code, 302)

    def test_no_puede_subir_a_actividad_de_otra_delegacion(self):
        self.ingresar('funcionario_centro', CLAVE_TEST)
        response = self.subir(imagen_png(), activity=self.actividad_norte)
        self.assertEqual(response.status_code, 404)

    def test_eliminar_es_logico_y_conserva_el_archivo(self):
        self.ingresar('admin_centro', CLAVE_TEST)
        self.subir(imagen_png())
        evidencia = Evidence.objects.filter(activity=self.actividad_centro).exclude(file='').get()
        storage, nombre = evidencia.file.storage, evidencia.file.name
        response = self.client.post(reverse('evidencia_delete', args=[evidencia.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Evidence.objects.filter(pk=evidencia.pk).exists())
        self.assertIsNotNone(Evidence.all_objects.get(pk=evidencia.pk).deleted_at)
        self.assertTrue(storage.exists(nombre))
        # La evidencia eliminada ya no aparece en el listado.
        response = self.client.get(reverse('evidencias_actividad', args=[self.actividad_centro.pk]))
        self.assertNotIn(evidencia, list(response.context['evidence_items']))

    def test_hard_delete_borra_el_archivo_fisico(self):
        self.ingresar('admin_centro', CLAVE_TEST)
        self.subir(imagen_png())
        evidencia = Evidence.objects.filter(activity=self.actividad_centro).exclude(file='').get()
        storage, nombre = evidencia.file.storage, evidencia.file.name
        evidencia.hard_delete()
        self.assertFalse(storage.exists(nombre))

    def test_funcionario_no_puede_eliminar_evidencia(self):
        self.ingresar('funcionario_centro', CLAVE_TEST)
        evidencia = Evidence.objects.filter(activity=self.actividad_centro).first()
        response = self.client.post(reverse('evidencia_delete', args=[evidencia.pk]))
        self.assertEqual(response.status_code, 403)
