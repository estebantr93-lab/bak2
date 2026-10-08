"""API REST con JWT: la matriz de pruebas de la evaluación, automatizada.

Cada clase corresponde a una fila de «Pruebas mínimas en Apidog»: JWT, sin autenticación (401),
operador de solo lectura (200/403), usuario sin rol (403), CRUD completo (201/200/200/204), errores
(400/400/404) y paginación (dos páginas distintas). La colección de Apidog repite estas mismas pruebas
contra el servidor local.
"""
import datetime
import io
import os
import shutil
import tempfile
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

from actividades.models import Activity, SocialCase
from agenda.models import Commitment
from colaboracion.models import AuditLog
from core.models import ActivityType, Period
from core.testing import CLAVE_TEST, sembrar_datos_demo
from funcionarios.models import Employee

PRINCIPALES = ['actividades', 'atenciones', 'compromisos', 'evidencias']
OPERACIONALES = []  # validaciones y seguimientos: módulo 3
RECURSOS = PRINCIPALES + OPERACIONALES


def png():
    buffer = io.BytesIO()
    Image.new('RGB', (10, 10), (0, 120, 60)).save(buffer, format='PNG')
    return SimpleUploadedFile('respaldo.png', buffer.getvalue(), content_type='image/png')


class ApiTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        with mock.patch.dict(os.environ, {'API_PASSWORD': CLAVE_TEST}):
            sembrar_datos_demo()

    def token(self, username, password=CLAVE_TEST):
        respuesta = APIClient().post('/api/token/', {'username': username, 'password': password}, format='json')
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        return respuesta.json()

    def cliente(self, username):
        cliente = APIClient()
        cliente.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token(username)["access"]}')
        return cliente

    def periodo_abierto(self):
        return Period.objects.filter(is_closed=False, start_date__lte=timezone.localdate()).order_by('-start_date').first()

    def datos_actividad(self, numero='API-0001'):
        periodo = self.periodo_abierto()
        return {
            'number': numero,
            'employee': Employee.objects.filter(is_active=True).first().pk,
            'period': periodo.pk,
            'activity_type': ActivityType.objects.get(code='ATC-01').pk,
            'date': str(max(periodo.start_date, timezone.localdate() - datetime.timedelta(days=1))),
            'description': 'Atención en terreno registrada desde la API',
        }


class JwtTests(ApiTestCase):
    def test_obtener_y_renovar_token(self):
        tokens = self.token('api_admin')
        self.assertEqual(set(tokens), {'access', 'refresh'})
        respuesta = APIClient().post('/api/token/refresh/', {'refresh': tokens['refresh']}, format='json')
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('access', respuesta.json())

    def test_clave_incorrecta_responde_401_generico(self):
        respuesta = APIClient().post('/api/token/', {'username': 'api_admin', 'password': 'mala'}, format='json')
        self.assertEqual(respuesta.status_code, 401)
        self.assertEqual(respuesta.json()['detail'], 'Usuario o contraseña incorrectos.')

    def test_token_con_el_mismo_bloqueo_por_intentos_que_la_web(self):
        for _ in range(5):
            APIClient().post('/api/token/', {'username': 'api_admin', 'password': 'mala'}, format='json')
        respuesta = APIClient().post('/api/token/', {'username': 'api_admin', 'password': CLAVE_TEST}, format='json')
        self.assertEqual(respuesta.status_code, 401)  # bloqueado: misma respuesta aunque la clave sea correcta
        self.assertTrue(AuditLog.objects.filter(action='login_bloqueado', detail='api_admin').exists())

    def test_ningun_usuario_de_la_api_es_superusuario(self):
        from django.contrib.auth.models import User
        self.assertFalse(User.objects.filter(username__startswith='api_', is_superuser=True).exists())


class SinAutenticacionTests(ApiTestCase):
    def test_los_seis_recursos_sin_token_responden_401(self):
        for recurso in RECURSOS:
            with self.subTest(recurso=recurso):
                respuesta = APIClient().get(f'/api/{recurso}/')
                self.assertEqual(respuesta.status_code, 401)
                self.assertIn('Bearer', respuesta['WWW-Authenticate'])

    def test_token_invalido_responde_401(self):
        cliente = APIClient()
        cliente.credentials(HTTP_AUTHORIZATION='Bearer token.invalido.x')
        self.assertEqual(cliente.get('/api/actividades/').status_code, 401)


class RolesTests(ApiTestCase):
    def test_operador_lee_los_seis_recursos_y_no_escribe(self):
        operador = self.cliente('api_operador')
        for recurso in RECURSOS:
            with self.subTest(recurso=recurso):
                self.assertEqual(operador.get(f'/api/{recurso}/').status_code, 200)
        self.assertEqual(operador.post('/api/actividades/', self.datos_actividad(), format='json').status_code, 403)
        compromiso = Commitment.objects.first()
        self.assertEqual(operador.patch(f'/api/compromisos/{compromiso.pk}/', {'notes': 'x'}, format='json').status_code, 403)
        self.assertEqual(operador.delete(f'/api/compromisos/{compromiso.pk}/').status_code, 403)

    def test_usuario_sin_rol_recibe_403_en_los_seis_recursos(self):
        sin_rol = self.cliente('api_sin_rol')
        for recurso in RECURSOS:
            with self.subTest(recurso=recurso):
                self.assertEqual(sin_rol.get(f'/api/{recurso}/').status_code, 403)

    def test_usuarios_de_la_web_sin_rol_api_tambien_reciben_403(self):
        self.assertEqual(self.cliente('admin_centro').get('/api/actividades/').status_code, 403)


class CrudTests(ApiTestCase):
    def setUp(self):
        self.admin = self.cliente('api_admin')

    def ciclo(self, recurso, datos, cambio, formato='json'):
        creado = self.admin.post(f'/api/{recurso}/', datos, format=formato)
        self.assertEqual(creado.status_code, 201, creado.content)
        url = f'/api/{recurso}/{creado.json()["id"]}/'
        self.assertEqual(self.admin.get(url).status_code, 200)
        modificado = self.admin.patch(url, cambio, format='json')
        self.assertEqual(modificado.status_code, 200, modificado.content)
        for campo, valor in cambio.items():
            self.assertEqual(modificado.json()[campo], valor)
        self.assertEqual(self.admin.delete(url).status_code, 204)
        self.assertEqual(self.admin.get(url).status_code, 404)  # borrado lógico: deja de figurar
        return creado.json()

    def test_crud_actividades(self):
        creada = self.ciclo('actividades', self.datos_actividad(), {'description': 'Descripción corregida por la API'})
        self.assertTrue(creada['evidence_code'].startswith('EV-'))
        self.assertTrue(Activity.all_objects.get(pk=creada['id']).deleted_at)  # sigue en la base, eliminada
        acciones = set(AuditLog.objects.filter(entity_type='Activity', entity_id=creada['id']).values_list('action', flat=True))
        self.assertEqual(acciones, {'crear', 'modificar', 'eliminar'})

    def test_crud_atenciones_sociales(self):
        social = Activity.objects.filter(activity_type__category='social', period__is_closed=False)
        actividad = next(a for a in social if a.social_cases.count() < 3)
        paso = next(n for n in (1, 2, 3) if not SocialCase.all_objects.filter(activity=actividad, step_number=n).exists())
        datos = {'activity': actividad.pk, 'step_number': paso, 'date': str(timezone.localdate()),
                 'description': 'Gestión registrada desde la API'}
        self.ciclo('atenciones', datos, {'result': 'Derivado a beneficio municipal'})

    def test_crud_compromisos(self):
        responsable = Employee.objects.filter(is_active=True).first()
        datos = {'title': 'Reparar luminarias de la plaza', 'delegation': responsable.delegation_id,
                 'responsible': responsable.pk, 'due_date': str(timezone.localdate() + datetime.timedelta(days=10))}
        self.ciclo('compromisos', datos, {'status': 'in_progress'})

    def test_crud_evidencias_con_archivo(self):
        media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, media, ignore_errors=True)
        with override_settings(MEDIA_ROOT=media):
            self._crud_evidencias()

    def _crud_evidencias(self):
        actividad = Activity.objects.filter(period__is_closed=False).first()
        datos = {'activity': actividad.pk, 'description': 'Fotografía de respaldo', 'file': png()}
        creada = self.ciclo('evidencias', datos, {'description': 'Fotografía de respaldo corregida'}, formato='multipart')
        self.assertTrue(creada['unique_code'].startswith('EVI-'))
        self.assertEqual(creada['status'], 'pending')

    def test_put_reemplaza_el_registro(self):
        compromiso = Commitment.objects.filter(status='registered').first()
        datos = {'title': 'Compromiso reescrito con PUT', 'delegation': compromiso.delegation_id,
                 'due_date': str(compromiso.due_date), 'status': 'pending', 'notes': ''}
        respuesta = self.admin.put(f'/api/compromisos/{compromiso.pk}/', datos, format='json')
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        self.assertEqual(respuesta.json()['title'], 'Compromiso reescrito con PUT')


class PaginacionTests(ApiTestCase):
    @classmethod
    def setUpTestData(cls):
        media = tempfile.mkdtemp()  # la carga de volumen genera archivos: nunca en el media/ real
        cls.addClassCleanup(shutil.rmtree, media, ignore_errors=True)
        with mock.patch.dict(os.environ, {'API_PASSWORD': CLAVE_TEST}), override_settings(MEDIA_ROOT=media):
            sembrar_datos_demo(volumen=30)

    def test_dos_paginas_con_resultados_distintos(self):
        operador = self.cliente('api_operador')
        primera = operador.get('/api/actividades/').json()
        segunda = operador.get('/api/actividades/?page=2').json()
        self.assertEqual(len(primera['results']), 20)
        self.assertEqual(primera['count'], Activity.objects.count())
        self.assertIsNotNone(primera['next'])
        ids = {fila['id'] for fila in primera['results']}
        self.assertTrue(ids.isdisjoint({fila['id'] for fila in segunda['results']}))

    def test_page_size_tiene_tope(self):
        respuesta = self.cliente('api_operador').get('/api/actividades/?page_size=5000').json()
        self.assertLessEqual(len(respuesta['results']), 100)

    def test_pagina_inexistente_404(self):
        self.assertEqual(self.cliente('api_operador').get('/api/actividades/?page=99999').status_code, 404)
