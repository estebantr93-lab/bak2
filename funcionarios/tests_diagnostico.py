"""Login sin rol o sin perfil: el usuario ve el mensaje genérico; el motivo queda en la traza y lo
explica el comando diagnosticar_acceso."""
from io import StringIO

from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from colaboracion.models import AuditLog
from core.models import Delegation, Position
from core.testing import sembrar_datos_demo
from funcionarios.models import Employee

CLAVE = 'Clave#Segura2026'
CORREO = 'tamara.berrios02@inacapmail.cl'


class DiagnosticoDeAccesoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        sembrar_datos_demo()

    def setUp(self):
        self.user = User.objects.create_user(CORREO, email=CORREO, password=CLAVE)

    def diagnostico(self, cuenta=CORREO):
        salida = StringIO()
        call_command('diagnosticar_acceso', cuenta, stdout=salida)
        return salida.getvalue()

    def ingresar(self):
        return self.client.post(reverse('login'), {'username': CORREO, 'password': CLAVE})

    def dar_perfil(self, user=None):
        Employee.objects.create(user=user or self.user, name='Tamara Berríos', delegation=Delegation.objects.first(),
                                position=Position.objects.first())

    def motivo(self):
        return AuditLog.objects.filter(action='login_rechazado', detail=CORREO).latest('date').changes['motivo'][1]

    def test_sin_grupo(self):
        self.assertContains(self.ingresar(), 'Usuario o contraseña incorrectos.')
        self.assertEqual(self.motivo(), 'sin rol asignado')
        texto = self.diagnostico()
        self.assertIn('Ingreso rechazado el', texto)
        self.assertIn('sin rol asignado', texto)
        self.assertIn('NO puede iniciar sesión', texto)
        self.assertIn('Grupos elegidos', texto)

    def test_grupo_con_otro_nombre_no_da_rol(self):
        self.user.groups.add(Group.objects.create(name='Funcionario'))
        self.dar_perfil()
        self.assertContains(self.ingresar(), 'Usuario o contraseña incorrectos.')
        self.assertEqual(self.motivo(), 'sin rol asignado')
        self.assertIn('debe ser exactamente «Funcionarios»', self.diagnostico())

    def test_con_grupo_pero_sin_perfil_el_motivo_queda_en_la_traza(self):
        self.user.groups.add(Group.objects.get(name='Administradores'))
        response = self.ingresar()
        self.assertContains(response, 'Usuario o contraseña incorrectos.')
        self.assertNotContains(response, 'perfil')
        self.assertEqual(self.motivo(), 'rol administrador de delegación sin perfil de funcionario con delegación')
        self.assertIn('Funcionarios → Añadir', self.diagnostico())

    def test_perfil_vinculado_a_otra_cuenta(self):
        self.user.groups.add(Group.objects.get(name='Funcionarios'))
        otra = User.objects.create_user('tamara', password=CLAVE)
        self.dar_perfil(otra)
        self.assertIn('usuario «tamara»', self.diagnostico())

    def test_completa_puede_iniciar_sesion_y_se_busca_tambien_por_correo(self):
        self.user.groups.add(Group.objects.get(name='Funcionarios'))
        self.dar_perfil()
        self.assertRedirects(self.ingresar(), reverse('dashboard'), fetch_redirect_response=False)
        self.user.username = 'tberrios'
        self.user.save()
        texto = self.diagnostico(CORREO.upper())
        self.assertIn('usuario exacto «tberrios»', texto)
