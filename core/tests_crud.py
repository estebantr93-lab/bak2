import datetime
import io

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from openpyxl import load_workbook

from actividades.models import Activity, SocialCase
from agenda.models import Commitment
from core.testing import SesionTestMixin, sembrar_datos_demo
from evidencias.models import Evidence, Validation
from funcionarios.models import Employee

CRUDS = {
    # prefijo: (modelo, camino a la delegación)
    'actividad': (Activity, 'delegation'),
    'atencion': (SocialCase, 'activity__delegation'),
    'evidencia': (Evidence, 'activity__delegation'),
    'compromiso': (Commitment, 'delegation'),
}


class BaseCrud(SesionTestMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        sembrar_datos_demo()


class SeguridadComunTests(BaseCrud):
    def test_anonimo_va_al_login_en_todos_los_crud(self):
        for prefijo in CRUDS:
            for accion in ('list', 'create', 'export'):
                url = reverse(f'{prefijo}_{accion}')
                response = self.client.get(url)
                self.assertRedirects(response, f"{reverse('login')}?next={url}", msg_prefix=url)

    def test_listados_respetan_scoping_de_delegacion(self):
        self.ingresar('admin_centro')
        for prefijo, (modelo, camino) in CRUDS.items():
            response = self.client.get(reverse(f'{prefijo}_list'), {'page_size': 30})
            self.assertEqual(response.status_code, 200, prefijo)
            delegaciones = {
                modelo.objects.filter(pk=f['obj'].pk).values_list(f'{camino}__name', flat=True).get()
                for f in response.context['rows']
            }
            self.assertTrue(delegaciones <= {'Delegación Centro'}, (prefijo, delegaciones))

    def test_objeto_de_otra_delegacion_da_404_al_editar_y_eliminar(self):
        self.ingresar('admin_centro')
        for prefijo, (modelo, camino) in CRUDS.items():
            ajeno = modelo.objects.filter(**{f'{camino}__name': 'Delegación Norte'}).first()
            self.assertIsNotNone(ajeno, prefijo)
            self.assertEqual(self.client.get(reverse(f'{prefijo}_update', args=[ajeno.pk])).status_code, 404)
            self.assertEqual(self.client.post(reverse(f'{prefijo}_delete', args=[ajeno.pk])).status_code, 404)
            self.assertIsNone(modelo.all_objects.get(pk=ajeno.pk).deleted_at)

    def test_eliminar_es_por_post_y_logico(self):
        self.ingresar('admin_centro')
        for prefijo, (modelo, camino) in CRUDS.items():
            obj = modelo.objects.filter(**{f'{camino}__name': 'Delegación Centro'}).first()
            url = reverse(f'{prefijo}_delete', args=[obj.pk])
            self.assertEqual(self.client.get(url).status_code, 405)
            self.assertRedirects(self.client.post(url), reverse(f'{prefijo}_list'))
            self.assertIsNotNone(modelo.all_objects.get(pk=obj.pk).deleted_at, prefijo)
            self.assertNotIn(obj, list(self.client.get(reverse(f'{prefijo}_list')).context['page_obj']))

    def test_funcionario_no_puede_eliminar_en_ningun_crud(self):
        self.ingresar('funcionario_centro')
        for prefijo, (modelo, camino) in CRUDS.items():
            obj = modelo.objects.filter(**{f'{camino}__name': 'Delegación Centro'}).first()
            self.assertEqual(self.client.post(reverse(f'{prefijo}_delete', args=[obj.pk])).status_code, 403)

    def test_verificador_sin_permiso_sobre_compromisos_recibe_403(self):
        self.ingresar('verificador_leia')
        self.assertEqual(self.client.get(reverse('compromiso_list')).status_code, 403)
        self.assertEqual(self.client.get(reverse('compromiso_export')).status_code, 403)


class ExportacionExcelTests(BaseCrud):
    def _libro(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response['Content-Type'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        self.assertIn('attachment;', response['Content-Disposition'])
        return load_workbook(io.BytesIO(response.content)).active

    def test_excel_tiene_encabezados_y_solo_datos_del_alcance(self):
        self.ingresar('admin_centro')
        hoja = self._libro(self.client.get(reverse('actividad_export')))
        encabezados = [c.value for c in hoja[1]]
        self.assertEqual(encabezados[:3], ['Número', 'Fecha', 'Funcionario'])
        esperadas = Activity.objects.filter(delegation__name='Delegación Centro')
        self.assertEqual(hoja.max_row - 1, esperadas.count())
        numeros = {fila[0] for fila in hoja.iter_rows(min_row=2, values_only=True)}
        self.assertEqual(numeros, set(esperadas.values_list('number', flat=True)))

    def test_excel_excluye_eliminados(self):
        self.ingresar('admin_centro')
        eliminada = Activity.objects.filter(delegation__name='Delegación Centro').first()
        eliminada.delete()
        hoja = self._libro(self.client.get(reverse('actividad_export')))
        numeros = {fila[0] for fila in hoja.iter_rows(min_row=2, values_only=True)}
        self.assertNotIn(eliminada.number, numeros)

    def test_todos_los_crud_exportan(self):
        self.ingresar('admin_sgr')
        for prefijo, (modelo, _) in CRUDS.items():
            hoja = self._libro(self.client.get(reverse(f'{prefijo}_export')))
            self.assertEqual(hoja.max_row - 1, modelo.objects.count(), prefijo)


class CompromisoTests(BaseCrud):
    def datos(self, **extra):
        responsable = Employee.objects.get(name='Ana Pérez (Centro)')
        datos = {
            'title': 'Reunión con junta de vecinos', 'description': '', 'responsible': responsable.pk,
            'due_date': (timezone.localdate() + datetime.timedelta(days=10)).isoformat(),
            'status': 'pending', 'notes': '',
        }
        datos.update(extra)
        return datos

    def test_admin_centro_crea_compromiso_en_su_delegacion(self):
        self.ingresar('admin_centro')
        response = self.client.post(reverse('compromiso_create'), self.datos(), follow=True)
        self.assertContains(response, 'registrado correctamente')
        creado = Commitment.objects.get(title='Reunión con junta de vecinos')
        self.assertEqual(creado.delegation.name, 'Delegación Centro')

    def test_fecha_en_el_pasado_se_rechaza(self):
        self.ingresar('admin_centro')
        response = self.client.post(reverse('compromiso_create'), self.datos(due_date='2020-01-01'))
        self.assertIn('due_date', response.context['form'].errors)
        self.assertTrue(response.context['modal_abierto'])

    def test_realizado_exige_observaciones(self):
        self.ingresar('admin_centro')
        response = self.client.post(reverse('compromiso_create'), self.datos(status='done'))
        self.assertIn('notes', response.context['form'].errors)

    def test_responsable_debe_ser_de_la_misma_delegacion(self):
        self.ingresar('admin_sgr')
        norte = Employee.objects.get(name='Carlos Rojas (Norte)')
        centro = Employee.objects.get(name='Ana Pérez (Centro)').delegation
        response = self.client.post(
            reverse('compromiso_create'), self.datos(responsible=norte.pk, delegation=centro.pk),
        )
        self.assertIn('responsible', response.context['form'].errors)

    def test_titulo_demasiado_corto(self):
        self.ingresar('admin_centro')
        response = self.client.post(reverse('compromiso_create'), self.datos(title='  ab '))
        self.assertIn('title', response.context['form'].errors)


class AtencionSocialTests(BaseCrud):
    def setUp(self):
        self.social = Activity.objects.filter(
            delegation__name='Delegación Centro', activity_type__category='social',
        ).first()

    def test_rango_de_gestion_1_a_3(self):
        self.ingresar('admin_centro')
        response = self.client.post(reverse('atencion_create'), {
            'activity': self.social.pk, 'step_number': 4, 'description': 'Cuarta gestión',
        })
        self.assertIn('step_number', response.context['form'].errors)

    def test_gestion_duplicada_se_rechaza(self):
        self.ingresar('admin_centro')
        existente = SocialCase.objects.filter(activity=self.social).first()
        response = self.client.post(reverse('atencion_create'), {
            'activity': self.social.pk, 'step_number': existente.step_number, 'description': 'Repetida',
        })
        self.assertFalse(response.context['form'].is_valid())

    def test_solo_actividades_de_tipo_social(self):
        self.ingresar('admin_sgr')
        no_social = Activity.objects.exclude(activity_type__category='social').first()
        response = self.client.post(reverse('atencion_create'), {
            'activity': no_social.pk, 'step_number': 2, 'description': 'x',
        })
        self.assertIn('activity', response.context['form'].errors)

    def test_crear_segunda_gestion(self):
        self.ingresar('funcionario_centro')
        libre = next(n for n in (1, 2, 3) if not SocialCase.objects.filter(activity=self.social, step_number=n).exists())
        response = self.client.post(reverse('atencion_create'), {
            'activity': self.social.pk, 'step_number': libre, 'description': 'Seguimiento en terreno',
        })
        self.assertRedirects(response, reverse('atencion_list'))


class EvidenciaRevisionTests(BaseCrud):
    def test_verificador_aprueba_y_queda_registro(self):
        self.ingresar('verificador_leia')
        evidencia = Evidence.objects.filter(status='pending').first()
        response = self.client.get(reverse('evidencia_update', args=[evidencia.pk]))
        self.assertIn('status', response.context['form'].fields)
        datos = {'activity': evidencia.activity_id, 'description': evidencia.description,
                 'status': 'approved', 'result': 'Documento conforme'}
        # Las evidencias del seed no traen archivo; se asigna uno para que la edición no exija adjuntarlo.
        if not evidencia.file:
            evidencia.file.name = 'evidencias/prueba.pdf'
            evidencia.save(update_fields=['file'])
        response = self.client.post(reverse('evidencia_update', args=[evidencia.pk]), datos)
        self.assertRedirects(response, reverse('evidencia_list'))
        evidencia.refresh_from_db()
        self.assertEqual(evidencia.status, 'approved')
        self.assertEqual(evidencia.reviewed_by.username, 'verificador_leia')
        self.assertTrue(Validation.objects.filter(evidence=evidencia, status='approved').exists())

    def test_funcionario_no_ve_el_campo_estado(self):
        self.ingresar('funcionario_centro')
        response = self.client.get(reverse('evidencia_list'))
        self.assertNotIn('status', response.context['form'].fields)
        self.assertEqual(User.objects.get(username='funcionario_centro').has_perm('evidencias.change_evidence'), False)
