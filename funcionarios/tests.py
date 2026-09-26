from io import StringIO

from django.contrib.auth.models import Group, Permission, User
from django.core.management import call_command
from django.test import TestCase

from core.models import Cargo, Delegacion

from .models import Funcionario
from .security import configurar_grupos_y_permisos


class FuncionarioModelTests(TestCase):
    def test_str_devuelve_el_nombre(self):
        delegacion = Delegacion.objects.create(nombre='Centro', direccion='Calle 1')
        cargo = Cargo.objects.create(nombre='Encargado')
        user = User.objects.create_user(username='func1', password='x')
        funcionario = Funcionario.objects.create(
            user=user, delegacion=delegacion, cargo=cargo, nombre='Ana Pérez',
        )
        self.assertEqual(str(funcionario), 'Ana Pérez')

    def test_user_solo_puede_tener_un_funcionario(self):
        delegacion = Delegacion.objects.create(nombre='Centro', direccion='Calle 1')
        cargo = Cargo.objects.create(nombre='Encargado')
        user = User.objects.create_user(username='func1', password='x')
        Funcionario.objects.create(user=user, delegacion=delegacion, cargo=cargo, nombre='Ana Pérez')
        with self.assertRaises(Exception):
            Funcionario.objects.create(user=user, delegacion=delegacion, cargo=cargo, nombre='Otra Persona')


class GruposYPermisosTests(TestCase):
    def setUp(self):
        configurar_grupos_y_permisos()

    def test_crea_los_tres_grupos(self):
        for nombre in ['Administradores', 'Funcionarios', 'Verificadores']:
            self.assertTrue(Group.objects.filter(name=nombre).exists())

    def test_grupo_funcionarios_no_tiene_permiso_de_aprobar_evidencia(self):
        grupo = Group.objects.get(name='Funcionarios')
        permiso = Permission.objects.get(codename='can_approve_evidencia')
        self.assertNotIn(permiso, grupo.permissions.all())

    def test_grupo_verificadores_tiene_permiso_de_aprobar_evidencia(self):
        grupo = Group.objects.get(name='Verificadores')
        permiso = Permission.objects.get(codename='can_approve_evidencia')
        self.assertIn(permiso, grupo.permissions.all())

    def test_es_idempotente(self):
        antes = Group.objects.get(name='Funcionarios').permissions.count()
        configurar_grupos_y_permisos()
        despues = Group.objects.get(name='Funcionarios').permissions.count()
        self.assertEqual(antes, despues)


class SeedFuncionariosTests(TestCase):
    def test_seed_asigna_delegacion_correcta_a_cada_funcionario(self):
        call_command('seed_data', stdout=StringIO())
        centro = Funcionario.objects.get(nombre='Ana Pérez (Centro)')
        norte = Funcionario.objects.get(nombre='Carlos Rojas (Norte)')
        self.assertEqual(centro.delegacion.nombre, 'Delegación Centro')
        self.assertEqual(norte.delegacion.nombre, 'Delegación Norte')

    def test_funcionario_centro_pertenece_al_grupo_funcionarios(self):
        call_command('seed_data', stdout=StringIO())
        user = User.objects.get(username='funcionario_centro')
        self.assertTrue(user.groups.filter(name='Funcionarios').exists())
        self.assertFalse(user.is_superuser)

    def test_admin_sgr_es_superusuario(self):
        call_command('seed_data', stdout=StringIO())
        user = User.objects.get(username='admin_sgr')
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)
