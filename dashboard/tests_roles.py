"""El dashboard muestra a cada rol información pertinente y calcula el cumplimiento por tipo, ponderado."""
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from actividades.models import Activity
from core.models import Period
from core.testing import CLAVE_TEST, sembrar_datos_demo
from medicion.models import Goal
from medicion.services import calcular_cumplimiento_ponderado


class DashboardPorRolTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        sembrar_datos_demo()

    def ver(self, username, **params):
        self.client.login(username=username, password=CLAVE_TEST)
        return self.client.get(reverse('dashboard'), params)

    def test_funcionario_ve_su_avance_sin_tabla_de_equipo(self):
        html = self.ver('funcionario_centro').content.decode()
        self.assertIn('Mi gestión', html)
        self.assertIn('Evidencias rechazadas', html)
        self.assertIn('Compromisos por vencer', html)
        self.assertNotIn('de su equipo', html)
        self.assertNotIn('Resumen por funcionario', html)
        self.assertNotIn('en su delegación', html)  # el indicador "Funcionarios: 1" no le aporta

    def test_verificador_ve_su_cola_y_solo_enlaces_que_puede_abrir(self):
        response = self.ver('verificador_leia')
        html = response.content.decode()
        self.assertIn('Revisión de evidencias', html)
        self.assertIn('Estado de evidencias', html)
        self.assertIn(reverse('evidencia_list') + '?status=pending', html)
        self.assertNotIn('Compromisos vencidos', html)
        self.assertNotIn(f'href="{reverse("compromiso_list")}"', html)
        self.assertNotIn(f'href="{reverse("actividad_list")}"', html)
        self.assertNotIn('Resumen por funcionario', html)
        # El rol del verificador es global: no se le muestra una delegación propia.
        self.assertIsNone(response.context['delegacion_usuario'])

    def test_administrador_ve_su_equipo_y_compromisos_a_hoy(self):
        html = self.ver('admin_centro').content.decode()
        self.assertIn('Resumen por funcionario', html)
        self.assertIn('a hoy', html)
        self.assertIn('Delegación Centro', html)

    def test_periodo_sin_metas_lo_dice_en_vez_de_mostrar_cero(self):
        cerrado = Period.objects.get(is_closed=True)
        self.assertFalse(Goal.objects.filter(period=cerrado).exists())
        html = self.ver('admin_centro', period=cerrado.pk).content.decode()
        self.assertIn('Sin metas definidas para este período', html)

    def test_cumplimiento_por_tipo_ponderado_con_tope(self):
        response = self.ver('admin_centro')
        periodo = response.context['period']
        fila = next(f for s in response.context['secciones'] for g in s['grupos'] for f in g['filas']
                    if f['employee'].name == 'Ana Pérez (Centro)')
        empleado = fila['employee']
        metas = list(Goal.objects.filter(position=empleado.position, period=periodo))
        aprobadas = {}
        for tipo_id in Activity.objects.filter(employee=empleado, period=periodo, validation_status='approved') \
                .values_list('activity_type_id', flat=True):
            aprobadas[tipo_id] = aprobadas.get(tipo_id, 0) + 1
        esperado, _ = calcular_cumplimiento_ponderado(aprobadas, metas, periodo.max_cap)
        self.assertEqual(fila['compliance_pct'], esperado.quantize(Decimal('0.1')))
        # Solo cuentan las aprobadas de tipos con meta.
        tipos_con_meta = {m.activity_type_id for m in metas}
        self.assertEqual(fila['aprobadas_con_meta'], sum(n for t, n in aprobadas.items() if t in tipos_con_meta))


class FiltroEstadoEvidenciasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        sembrar_datos_demo()

    def test_filtra_por_estado_e_ignora_valores_no_permitidos(self):
        self.client.login(username='admin_sgr', password=CLAVE_TEST)
        pendientes = self.client.get(reverse('evidencia_list'), {'status': 'pending', 'per_page': 30})
        self.assertTrue(pendientes.context['page_obj'].object_list)
        self.assertTrue(all(e.status == 'pending' for e in pendientes.context['page_obj']))
        todas = self.client.get(reverse('evidencia_list'), {'status': 'x;drop'})
        self.assertEqual(todas.context['filters'], {})
