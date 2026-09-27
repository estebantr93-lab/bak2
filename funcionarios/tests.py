
from django.contrib.auth.models import Group, Permission, User
from django.test import TestCase

from core.models import Position, Delegation
from core.testing import sembrar_datos_demo

from .models import Employee
from .security import configurar_grupos_y_permisos


class FuncionarioModelTests(TestCase):
    def test_str_devuelve_el_nombre(self):
        delegacion = Delegation.objects.create(name='Centro', address='Calle 1')
        cargo = Position.objects.create(name='Encargado')
        user = User.objects.create_user(username='func1', password='x')
        funcionario = Employee.objects.create(
            user=user, delegation=delegacion, position=cargo, name='Ana Pérez',
        )
        self.assertEqual(str(funcionario), 'Ana Pérez')

    def test_user_solo_puede_tener_un_funcionario(self):
        delegacion = Delegation.objects.create(name='Centro', address='Calle 1')
        cargo = Position.objects.create(name='Encargado')
        user = User.objects.create_user(username='func1', password='x')
        Employee.objects.create(user=user, delegation=delegacion, position=cargo, name='Ana Pérez')
        with self.assertRaises(Exception):
            Employee.objects.create(user=user, delegation=delegacion, position=cargo, name='Otra Persona')


class GruposYPermisosTests(TestCase):
    def setUp(self):
        configurar_grupos_y_permisos()

    def test_crea_los_tres_grupos(self):
        for nombre in ['Administradores', 'Funcionarios', 'Verificadores']:
            self.assertTrue(Group.objects.filter(name=nombre).exists())

    def test_grupo_funcionarios_no_tiene_permiso_de_aprobar_evidencia(self):
        grupo = Group.objects.get(name='Funcionarios')
        permiso = Permission.objects.get(codename='can_approve_evidence')
        self.assertNotIn(permiso, grupo.permissions.all())

    def test_grupo_verificadores_tiene_permiso_de_aprobar_evidencia(self):
        grupo = Group.objects.get(name='Verificadores')
        permiso = Permission.objects.get(codename='can_approve_evidence')
        self.assertIn(permiso, grupo.permissions.all())

    def test_es_idempotente(self):
        antes = Group.objects.get(name='Funcionarios').permissions.count()
        configurar_grupos_y_permisos()
        despues = Group.objects.get(name='Funcionarios').permissions.count()
        self.assertEqual(antes, despues)


class SeedFuncionariosTests(TestCase):
    def test_seed_asigna_delegacion_correcta_a_cada_funcionario(self):
        sembrar_datos_demo()
        centro = Employee.objects.get(name='Ana Pérez (Centro)')
        norte = Employee.objects.get(name='Carlos Rojas (Norte)')
        self.assertEqual(centro.delegation.name, 'Delegación Centro')
        self.assertEqual(norte.delegation.name, 'Delegación Norte')

    def test_funcionario_centro_pertenece_al_grupo_funcionarios(self):
        sembrar_datos_demo()
        user = User.objects.get(username='funcionario_centro')
        self.assertTrue(user.groups.filter(name='Funcionarios').exists())
        self.assertFalse(user.is_superuser)

    def test_admin_sgr_es_superusuario(self):
        sembrar_datos_demo()
        user = User.objects.get(username='admin_sgr')
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)
