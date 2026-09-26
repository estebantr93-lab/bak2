import datetime

from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase

from core.admin_utils import ScopedModelAdmin
from core.models import Cargo, Delegacion
from funcionarios.models import Funcionario

from .admin import CompromisoAdmin
from .models import Compromiso


class CompromisoModelTests(TestCase):
    def setUp(self):
        self.centro = Delegacion.objects.create(nombre='Centro', direccion='Calle 1')
        self.norte = Delegacion.objects.create(nombre='Norte', direccion='Calle 2')

    def test_compromiso_admin_usa_scoped_model_admin(self):
        self.assertTrue(issubclass(CompromisoAdmin, ScopedModelAdmin))
        self.assertEqual(CompromisoAdmin.scope_by, 'delegacion')

    def test_compromiso_vencido_se_identifica_por_fecha_y_estado(self):
        vencido = Compromiso.objects.create(
            titulo='Tarea vencida', delegacion=self.centro,
            fecha_vencimiento=datetime.date(2020, 1, 1), estado='pendiente',
        )
        vigente = Compromiso.objects.create(
            titulo='Tarea vigente', delegacion=self.centro,
            fecha_vencimiento=datetime.date(2099, 1, 1), estado='pendiente',
        )
        hoy = datetime.date.today()
        vencidos = Compromiso.objects.filter(fecha_vencimiento__lt=hoy).exclude(estado='realizado')
        self.assertIn(vencido, vencidos)
        self.assertNotIn(vigente, vencidos)


class CompromisoScopingTests(TestCase):
    def setUp(self):
        centro = Delegacion.objects.create(nombre='Centro', direccion='Calle 1')
        norte = Delegacion.objects.create(nombre='Norte', direccion='Calle 2')
        cargo = Cargo.objects.create(nombre='Encargado')
        user_centro = User.objects.create_user(username='func_centro', password='x', is_staff=True)
        Funcionario.objects.create(user=user_centro, delegacion=centro, cargo=cargo, nombre='Func Centro')

        self.compromiso_centro = Compromiso.objects.create(
            titulo='Centro', delegacion=centro, fecha_vencimiento=datetime.date(2026, 1, 1), estado='ingresado',
        )
        self.compromiso_norte = Compromiso.objects.create(
            titulo='Norte', delegacion=norte, fecha_vencimiento=datetime.date(2026, 1, 1), estado='ingresado',
        )
        self.user_centro = user_centro
        self.factory = RequestFactory()

    def test_funcionario_solo_ve_compromisos_de_su_delegacion(self):
        request = self.factory.get('/admin/agenda/compromiso/')
        request.user = self.user_centro
        admin_instance = CompromisoAdmin(Compromiso, None)

        queryset = admin_instance.get_queryset(request)

        self.assertIn(self.compromiso_centro, queryset)
        self.assertNotIn(self.compromiso_norte, queryset)
