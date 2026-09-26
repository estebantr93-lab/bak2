from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from actividades.models import Actividad
from core.admin_utils import (
    ROL_ADMIN_DELEGACION,
    ROL_FUNCIONARIO,
    ROL_SUPERADMIN,
    ROL_VERIFICADOR,
    get_rol,
)
from core.models import Delegacion
from evidencias.models import Evidencia
from funcionarios.models import Funcionario


class RolesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_data', stdout=StringIO())

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
        self.assertEqual(Delegacion.objects.count(), 2)
        for delegacion in Delegacion.objects.all():
            admins = Funcionario.objects.filter(delegacion=delegacion, user__groups__name='Administradores')
            self.assertEqual(admins.count(), 1, delegacion.nombre)

    def test_admins_de_delegacion_no_son_superusuarios_ni_gestionan_usuarios(self):
        for username in ['admin_centro', 'admin_norte']:
            user = User.objects.get(username=username)
            self.assertFalse(user.is_superuser)
            self.assertFalse(user.has_perm('auth.change_user'))
            self.assertFalse(user.has_perm('core.change_delegacion'))


class DashboardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_data', stdout=StringIO())

    def _ingresar(self, username, password):
        self.assertTrue(self.client.login(username=username, password=password))
        return self.client.get(reverse('monitoreo:dashboard'))

    def test_dashboard_requiere_login(self):
        response = self.client.get(reverse('monitoreo:dashboard'))
        self.assertRedirects(response, reverse('login') + '?next=' + reverse('monitoreo:dashboard'))

    def test_admin_centro_solo_ve_su_delegacion(self):
        response = self._ingresar('admin_centro', 'AdminCentro#2026SGR')
        self.assertContains(response, 'Ana Pérez (Centro)')
        self.assertContains(response, 'María Soto (Admin Centro)')
        self.assertNotContains(response, 'Carlos Rojas (Norte)')
        self.assertNotContains(response, 'Jorge Díaz (Admin Norte)')
        self.assertNotContains(response, 'Delegación Norte')
        nombres = [s['delegacion'].nombre for s in response.context['secciones']]
        self.assertEqual(nombres, ['Delegación Centro'])

    def test_admin_norte_solo_ve_su_delegacion(self):
        response = self._ingresar('admin_norte', 'AdminNorte#2026SGR')
        self.assertContains(response, 'Carlos Rojas (Norte)')
        self.assertNotContains(response, 'Ana Pérez (Centro)')
        self.assertNotContains(response, 'Delegación Centro')

    def test_resumen_agrupado_por_rol(self):
        response = self._ingresar('admin_centro', 'AdminCentro#2026SGR')
        grupos = response.context['secciones'][0]['grupos']
        self.assertEqual([g['rol'] for g in grupos], [ROL_ADMIN_DELEGACION, ROL_FUNCIONARIO])
        fila_ana = grupos[1]['filas'][0]
        self.assertEqual(fila_ana['funcionario'].nombre, 'Ana Pérez (Centro)')
        self.assertEqual(
            fila_ana['act_total'],
            Actividad.objects.filter(funcionario__nombre='Ana Pérez (Centro)', periodo__cerrado=False).count(),
        )
        self.assertEqual(
            fila_ana['evi_pendientes'],
            Evidencia.objects.filter(
                actividad__funcionario__nombre='Ana Pérez (Centro)', estado='pendiente',
                actividad__periodo__cerrado=False,
            ).count(),
        )

    def test_funcionario_solo_ve_su_propio_resumen(self):
        response = self._ingresar('funcionario_centro', 'Centro#2026SGR')
        self.assertContains(response, 'Ana Pérez (Centro)')
        self.assertNotContains(response, 'María Soto (Admin Centro)')
        self.assertNotContains(response, 'Carlos Rojas (Norte)')
        self.assertEqual(response.context['totales']['funcionarios'], 1)

    def test_superadmin_ve_ambas_delegaciones(self):
        response = self._ingresar('admin_sgr', 'Admin#2026SGR')
        nombres = [s['delegacion'].nombre for s in response.context['secciones']]
        self.assertEqual(nombres, ['Delegación Centro', 'Delegación Norte'])
        self.assertEqual(response.context['totales']['funcionarios'], 4)

    def test_usuario_sin_rol_no_ve_datos(self):
        User.objects.create_user(username='sin_rol', password='x')
        response = self._ingresar('sin_rol', 'x')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['secciones'], [])
        self.assertContains(response, 'no tiene un rol asignado')


class AislamientoAdminPorDelegacionTests(TestCase):
    """Los dos administradores de delegación no pueden ver ni editar lo del otro en el Admin."""

    @classmethod
    def setUpTestData(cls):
        call_command('seed_data', stdout=StringIO())

    def setUp(self):
        self.client.login(username='admin_centro', password='AdminCentro#2026SGR')

    def test_admin_centro_solo_lista_actividades_de_centro(self):
        response = self.client.get('/admin/actividades/actividad/')
        self.assertEqual(response.status_code, 200)
        visibles = set(response.context['cl'].queryset.values_list('delegacion__nombre', flat=True))
        self.assertEqual(visibles, {'Delegación Centro'})

    def test_admin_centro_no_puede_abrir_actividad_de_norte(self):
        actividad_norte = Actividad.objects.filter(delegacion__nombre='Delegación Norte').first()
        response = self.client.get(f'/admin/actividades/actividad/{actividad_norte.pk}/change/')
        self.assertNotEqual(response.status_code, 200)

    def test_admin_centro_solo_lista_funcionarios_de_centro(self):
        response = self.client.get('/admin/funcionarios/funcionario/')
        visibles = set(response.context['cl'].queryset.values_list('delegacion__nombre', flat=True))
        self.assertEqual(visibles, {'Delegación Centro'})

    def test_admin_centro_solo_ve_su_delegacion_en_maestra(self):
        response = self.client.get('/admin/core/delegacion/')
        self.assertEqual(list(response.context['cl'].queryset.values_list('nombre', flat=True)), ['Delegación Centro'])

    def test_admin_centro_solo_lista_evidencias_de_centro(self):
        response = self.client.get('/admin/evidencias/evidencia/')
        visibles = set(response.context['cl'].queryset.values_list('actividad__delegacion__nombre', flat=True))
        self.assertEqual(visibles, {'Delegación Centro'})

    def test_admin_centro_no_accede_a_usuarios(self):
        response = self.client.get('/admin/auth/user/')
        self.assertEqual(response.status_code, 403)

    def test_admin_centro_no_puede_mover_funcionario_a_otra_delegacion(self):
        ana = Funcionario.objects.get(nombre='Ana Pérez (Centro)')
        response = self.client.get(f'/admin/funcionarios/funcionario/{ana.pk}/change/')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('delegacion', response.context['adminform'].form.fields)
