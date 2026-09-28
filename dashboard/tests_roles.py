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
        self.assertIn('Actividades rechazadas', html)
        self.assertIn('Compromisos por vencer', html)
        self.assertNotIn('de su equipo', html)
        self.assertNotIn('Resumen por funcionario', html)
        self.assertNotIn('en su delegación', html)  # el indicador "Funcionarios: 1" no le aporta

    def test_verificador_ve_su_cola_y_solo_enlaces_que_puede_abrir(self):
        response = self.ver('verificador_leia')
        html = response.content.decode()
        self.assertIn('Revisión de evidencias', html)
        self.assertIn('Estado de evidencias', html)
        self.assertIn(reverse('evidencia_list') + f'?period={response.context["period"].pk}&amp;status=pending', html)
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


class IndicadoresCoincidenConSuListaTests(TestCase):
    """Cada indicador con enlace lleva los mismos filtros que su conteo: la lista muestra ese número."""

    @classmethod
    def setUpTestData(cls):
        sembrar_datos_demo()

    def test_valor_del_indicador_igual_a_las_filas_de_la_lista(self):
        for username in ('admin_sgr', 'admin_centro', 'funcionario_centro', 'verificador_leia'):
            self.client.login(username=username, password=CLAVE_TEST)
            for k in self.client.get(reverse('dashboard')).context['indicadores']:
                if k.get('url'):
                    filas = self.client.get(k['url']).context['page_obj'].paginator.count
                    self.assertEqual(filas, k['valor'], f'{username} · {k["etiqueta"]} → {k["url"]}')

    def test_la_lista_dice_que_filtro_aplica(self):
        self.client.login(username='funcionario_centro', password=CLAVE_TEST)
        periodo = Period.objects.get(is_closed=False)
        html = self.client.get(reverse('actividad_list'), {'period': periodo.pk, 'mias': 1, 'status': 'rejected'}).content.decode()
        self.assertIn(f'período {periodo}', html)
        self.assertIn('solo las mías', html)
        self.assertIn('rechazada', html)


class GestionesDeActividadAprobadaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        sembrar_datos_demo()

    def test_funcionario_no_edita_gestiones_de_una_actividad_aprobada(self):
        from actividades.models import SocialCase

        gestion = SocialCase.objects.filter(activity__employee__user__username='funcionario_centro').first()
        Activity.objects.filter(pk=gestion.activity_id).update(validation_status='approved')
        self.client.login(username='funcionario_centro', password=CLAVE_TEST)
        self.assertEqual(self.client.get(reverse('atencion_update', args=[gestion.pk])).status_code, 403)
        self.client.login(username='admin_centro', password=CLAVE_TEST)
        self.assertEqual(self.client.get(reverse('atencion_update', args=[gestion.pk])).status_code, 200)


class PeriodosRelativosTests(TestCase):
    """La carga arma los períodos alrededor de la fecha del día: la demo funciona cuando se presente."""

    def test_hoy_queda_dentro_del_periodo_abierto_y_el_cerrado_es_anterior(self):
        import datetime

        from core.data import rangos_de_periodos

        for hoy in (datetime.date(2026, 9, 30), datetime.date(2026, 10, 1), datetime.date(2027, 1, 15)):
            (ini_c, fin_c), (ini_a, fin_a) = rangos_de_periodos(hoy)
            self.assertTrue(ini_a <= hoy <= fin_a, hoy)
            self.assertEqual(fin_c + datetime.timedelta(days=1), ini_a)
            self.assertLess(ini_c, fin_c)

    def test_la_semilla_no_deja_pendientes_en_el_periodo_cerrado_ni_fechas_futuras(self):
        from django.utils import timezone

        from evidencias.models import Evidence

        import shutil
        import tempfile

        from django.test import override_settings

        media = tempfile.mkdtemp()  # la carga de volumen genera archivos: nunca en el media/ real
        self.addCleanup(shutil.rmtree, media, ignore_errors=True)
        with override_settings(MEDIA_ROOT=media):
            sembrar_datos_demo(volumen=300)
        self.assertFalse(Evidence.objects.filter(activity__period__is_closed=True, status='pending').exists())
        self.assertFalse(Activity.objects.filter(date__gt=timezone.localdate()).exists())
        abierto = Period.objects.get(is_closed=False)
        self.assertTrue(abierto.start_date <= timezone.localdate() <= abierto.end_date)


class ActividadesSinEvidenciaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        sembrar_datos_demo()

    def test_cuenta_por_funcionario_las_actividades_sin_evidencia(self):
        # Con un conteo agregado filtrado y luego agrupado por funcionario, el resultado era 0.
        from django.db.models import Count, Q

        periodo = Period.objects.get(is_closed=False)
        propias = Activity.objects.filter(employee__user__username='funcionario_centro', period=periodo)
        base = propias.first()
        Activity.objects.create(
            number='SIN-EVI-1', employee=base.employee, delegation=base.delegation, period=periodo,
            activity_type=base.activity_type, date=base.date, description='Sin respaldo', evidence_code='EV-SIN-1',
        )
        esperado = propias.annotate(
            n=Count('evidence_items', filter=Q(evidence_items__deleted_at__isnull=True))).filter(n=0).count()
        self.assertGreater(esperado, 0)
        self.client.login(username='funcionario_centro', password=CLAVE_TEST)
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.context['totales']['act_sin_evidencia'], esperado)
        lista = self.client.get(reverse('actividad_list'), {'period': periodo.pk, 'mias': 1, 'sin_evidencia': 1})
        self.assertEqual(lista.context['page_obj'].paginator.count, esperado)
