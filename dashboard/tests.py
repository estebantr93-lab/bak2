
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from actividades.models import Activity
from core.admin_utils import (
    ROL_ADMIN_DELEGACION,
    ROL_FUNCIONARIO,
    ROL_SUPERADMIN,
    ROL_VERIFICADOR,
    get_rol,
)
from core.models import Delegation
from evidencias.models import Evidence
from funcionarios.models import Employee
from core.testing import CLAVE_TEST, sembrar_datos_demo


class RolesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        sembrar_datos_demo()

    def test_rol_de_cada_cuenta_demo(self):
        esperados = {
            'admin_sgr': ROL_SUPERADMIN,
            'admin_centro': ROL_ADMIN_DELEGACION,
            'admin_norte': ROL_ADMIN_DELEGACION,
            'funcionario_centro': ROL_FUNCIONARIO,
            'funcionario_norte': ROL_FUNCIONARIO,
            'verificador_leia': ROL_VERIFICADOR,
        }
        for username, rol in esperados.items():
            self.assertEqual(get_rol(User.objects.get(username=username)), rol, username)

    def test_existen_dos_delegaciones_con_un_admin_cada_una(self):
        self.assertEqual(Delegation.objects.count(), 2)
        for delegacion in Delegation.objects.all():
            admins = Employee.objects.filter(delegation=delegacion, user__groups__name='Administradores')
            self.assertEqual(admins.count(), 1, delegacion.name)

    def test_admins_de_delegacion_no_son_superusuarios_ni_gestionan_usuarios(self):
        for username in ['admin_centro', 'admin_norte']:
            user = User.objects.get(username=username)
            self.assertFalse(user.is_superuser)
            self.assertFalse(user.has_perm('auth.change_user'))
            self.assertFalse(user.has_perm('core.change_delegation'))


class DashboardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        sembrar_datos_demo()

    def _ingresar(self, username, password):
        self.assertTrue(self.client.login(username=username, password=password))
        return self.client.get(reverse('dashboard'))

    def test_dashboard_requiere_login(self):
        response = self.client.get(reverse('dashboard'))
        self.assertRedirects(response, reverse('login') + '?next=' + reverse('dashboard'))

    def test_admin_centro_solo_ve_su_delegacion(self):
        response = self._ingresar('admin_centro', CLAVE_TEST)
        self.assertContains(response, 'Ana Pérez (Centro)')
        self.assertContains(response, 'María Soto (Admin Centro)')
        self.assertNotContains(response, 'Carlos Rojas (Norte)')
        self.assertNotContains(response, 'Jorge Díaz (Admin Norte)')
        self.assertNotContains(response, 'Delegación Norte')
        nombres = [s['delegation'].name for s in response.context['secciones']]
        self.assertEqual(nombres, ['Delegación Centro'])

    def test_admin_norte_solo_ve_su_delegacion(self):
        response = self._ingresar('admin_norte', CLAVE_TEST)
        self.assertContains(response, 'Carlos Rojas (Norte)')
        self.assertNotContains(response, 'Ana Pérez (Centro)')
        self.assertNotContains(response, 'Delegación Centro')

    def test_resumen_agrupado_por_rol(self):
        response = self._ingresar('admin_centro', CLAVE_TEST)
        grupos = response.context['secciones'][0]['grupos']
        self.assertEqual([g['rol'] for g in grupos], [ROL_ADMIN_DELEGACION, ROL_FUNCIONARIO])
        fila_ana = grupos[1]['filas'][0]
        self.assertEqual(fila_ana['employee'].name, 'Ana Pérez (Centro)')
        self.assertEqual(
            fila_ana['act_total'],
            Activity.objects.filter(employee__name='Ana Pérez (Centro)', period__is_closed=False).count(),
        )
        self.assertEqual(
            fila_ana['evi_pendientes'],
            Evidence.objects.filter(
                activity__employee__name='Ana Pérez (Centro)', status='pending',
                activity__period__is_closed=False,
            ).count(),
        )

    def test_funcionario_solo_ve_su_propio_resumen(self):
        response = self._ingresar('funcionario_centro', CLAVE_TEST)
        self.assertContains(response, 'Ana Pérez (Centro)')
        self.assertNotContains(response, 'María Soto (Admin Centro)')
        self.assertNotContains(response, 'Carlos Rojas (Norte)')
        self.assertEqual(response.context['totales']['employees'], 1)

    def test_superadmin_ve_ambas_delegaciones(self):
        response = self._ingresar('admin_sgr', CLAVE_TEST)
        nombres = [s['delegation'].name for s in response.context['secciones']]
        self.assertEqual(nombres, ['Delegación Centro', 'Delegación Norte'])
        self.assertEqual(response.context['totales']['employees'], 4)

    def test_usuario_sin_rol_recibe_403(self):
        User.objects.create_user(username='sin_rol', password='x')
        response = self._ingresar('sin_rol', 'x')
        self.assertEqual(response.status_code, 403)

    def test_funcionario_sin_perfil_recibe_403(self):
        from django.contrib.auth.models import Group

        user = User.objects.create_user(username='sin_perfil', password='x')
        user.groups.add(Group.objects.get(name='Funcionarios'))
        response = self._ingresar('sin_perfil', 'x')
        self.assertEqual(response.status_code, 403)

    def test_periodo_elegido_se_recuerda_en_la_sesion(self):
        from core.models import Period

        cerrado = Period.objects.get(is_closed=True)
        self.client.login(username='admin_centro', password=CLAVE_TEST)
        self.client.get(reverse('dashboard'), {'period': cerrado.pk})
        self.assertEqual(self.client.session['dashboard_periodo_id'], cerrado.pk)
        # Sin parámetro, la siguiente visita usa el período recordado.
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.context['period'], cerrado)


class AislamientoAdminPorDelegacionTests(TestCase):
    """Los dos administradores de delegación no pueden ver ni editar lo del otro en el Admin."""

    @classmethod
    def setUpTestData(cls):
        sembrar_datos_demo()

    def setUp(self):
        self.client.login(username='admin_centro', password=CLAVE_TEST)

    def test_admin_centro_solo_lista_actividades_de_centro(self):
        response = self.client.get('/admin/actividades/activity/')
        self.assertEqual(response.status_code, 200)
        visibles = set(response.context['cl'].queryset.values_list('delegation__name', flat=True))
        self.assertEqual(visibles, {'Delegación Centro'})

    def test_admin_centro_no_puede_abrir_actividad_de_norte(self):
        actividad_norte = Activity.objects.filter(delegation__name='Delegación Norte').first()
        response = self.client.get(f'/admin/actividades/activity/{actividad_norte.pk}/change/')
        self.assertNotEqual(response.status_code, 200)

    def test_admin_centro_solo_lista_funcionarios_de_centro(self):
        response = self.client.get('/admin/funcionarios/employee/')
        visibles = set(response.context['cl'].queryset.values_list('delegation__name', flat=True))
        self.assertEqual(visibles, {'Delegación Centro'})

    def test_admin_centro_solo_ve_su_delegacion_en_maestra(self):
        response = self.client.get('/admin/core/delegation/')
        self.assertEqual(list(response.context['cl'].queryset.values_list('name', flat=True)), ['Delegación Centro'])

    def test_admin_centro_solo_lista_evidencias_de_centro(self):
        response = self.client.get('/admin/evidencias/evidence/')
        visibles = set(response.context['cl'].queryset.values_list('activity__delegation__name', flat=True))
        self.assertEqual(visibles, {'Delegación Centro'})

    def test_admin_centro_no_accede_a_usuarios(self):
        response = self.client.get('/admin/auth/user/')
        self.assertEqual(response.status_code, 403)

    def test_admin_centro_no_puede_mover_funcionario_a_otra_delegacion(self):
        ana = Employee.objects.get(name='Ana Pérez (Centro)')
        response = self.client.get(f'/admin/funcionarios/employee/{ana.pk}/change/')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('delegation', response.context['adminform'].form.fields)
