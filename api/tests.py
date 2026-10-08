"""API REST con JWT: la matriz de pruebas de la evaluación, automatizada.

Cada clase corresponde a una fila de «Pruebas mínimas en Apidog»: JWT, sin autenticación (401),
operador de solo lectura (200/403), usuario sin rol (403), CRUD completo (201/200/200/204), errores
(400/400/404) y paginación (dos páginas distintas). La colección de Apidog repite estas mismas pruebas
contra el servidor local.
"""
import datetime
import io
import os
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

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
