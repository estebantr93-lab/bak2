"""Estado de la actividad según sus evidencias y conteos de la acción masiva del Admin."""
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory, TestCase

from actividades.models import Activity
from core.testing import sembrar_datos_demo

from .admin import EvidenciaAdmin
from .models import Evidence
from .services import estado_segun_evidencias, registrar_revision


class ReglaEstadoActividadTests(TestCase):
    def test_regla(self):
        self.assertEqual(estado_segun_evidencias(aprobadas=0, rechazadas=0, pendientes=0), 'pending')
        self.assertEqual(estado_segun_evidencias(aprobadas=0, rechazadas=1, pendientes=0), 'rejected')
        # Una evidencia corregida por revisar deja la actividad pendiente, no rechazada.
        self.assertEqual(estado_segun_evidencias(aprobadas=0, rechazadas=1, pendientes=1), 'pending')
        # Basta una evidencia aprobada, aunque otra haya sido rechazada.
        self.assertEqual(estado_segun_evidencias(aprobadas=1, rechazadas=1, pendientes=0), 'approved')


class ActividadRechazadaSeRecuperaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        sembrar_datos_demo()

    def test_rechazo_correccion_y_aprobacion(self):
        verificador = User.objects.get(username='verificador_leia')
        actividad = Activity.objects.filter(period__is_closed=False).first()
        actividad.evidence_items.all().delete()

        borrosa = Evidence.objects.create(activity=actividad, description='Foto borrosa')
        registrar_revision(borrosa, verificador, 'rejected', 'No se lee')
        actividad.refresh_from_db()
        self.assertEqual(actividad.validation_status, 'rejected')

        corregida = Evidence.objects.create(activity=actividad, description='Foto corregida')
        actividad.refresh_from_db()
        self.assertEqual(actividad.validation_status, 'pending')

        registrar_revision(corregida, verificador, 'approved', 'Correcta')
        actividad.refresh_from_db()
        self.assertEqual(actividad.validation_status, 'approved')


class AccionMasivaConteosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        sembrar_datos_demo()

    def test_informa_aprobadas_y_omitidas_correctamente(self):
        from core.models import Period

        abierta = Activity.objects.filter(period__is_closed=False).first()
        # Actividad heredada de un período ya cerrado (create() no pasa por clean()).
        cerrada = Activity.objects.create(
            number='ACT-CERRADA', employee=abierta.employee, delegation=abierta.delegation,
            activity_type=abierta.activity_type, period=Period.objects.get(is_closed=True),
            date=abierta.date, description='Del trimestre cerrado', evidence_code='EV-CERRADA',
        )
        abiertas = [Evidence.objects.create(activity=abierta, description=f'e{i}') for i in range(3)]
        de_cerrado = Evidence.objects.create(activity=cerrada, description='cerrado')  # sin clean(): dato heredado
        seleccion = Evidence.objects.filter(pk__in=[e.pk for e in abiertas] + [de_cerrado.pk])

        request = RequestFactory().post('/admin/evidencias/evidence/')
        request.user = User.objects.get(username='admin_sgr')
        request.session = {}
        request._messages = FallbackStorage(request)
        EvidenciaAdmin(Evidence, None).aprobar_evidencias(request, seleccion)

        mensajes = [str(m) for m in get_messages(request)]
        self.assertIn('3 evidencia(s) aprobada(s) correctamente.', mensajes)
        self.assertIn('1 evidencia(s) omitida(s) por pertenecer a un período cerrado.', mensajes)
        de_cerrado.refresh_from_db()
        self.assertEqual(de_cerrado.status, 'pending')
