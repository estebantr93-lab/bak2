import datetime

from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase

from core.admin_utils import ScopedModelAdmin
from core.models import Position, Delegation
from funcionarios.models import Employee

from .admin import CompromisoAdmin
from .models import Commitment


class CompromisoModelTests(TestCase):
    def setUp(self):
        self.centro = Delegation.objects.create(name='Centro', address='Calle 1')
        self.norte = Delegation.objects.create(name='Norte', address='Calle 2')

    def test_compromiso_admin_usa_scoped_model_admin(self):
        self.assertTrue(issubclass(CompromisoAdmin, ScopedModelAdmin))
        self.assertEqual(CompromisoAdmin.scope_by, 'delegation')

    def test_compromiso_vencido_se_identifica_por_fecha_y_estado(self):
        vencido = Commitment.objects.create(
            title='Tarea vencida', delegation=self.centro,
            due_date=datetime.date(2020, 1, 1), status='pending',
        )
        vigente = Commitment.objects.create(
            title='Tarea vigente', delegation=self.centro,
            due_date=datetime.date(2099, 1, 1), status='pending',
        )
        hoy = datetime.date.today()
        vencidos = Commitment.objects.filter(due_date__lt=hoy).exclude(status='done')
        self.assertIn(vencido, vencidos)
        self.assertNotIn(vigente, vencidos)


class CompromisoScopingTests(TestCase):
    def setUp(self):
        centro = Delegation.objects.create(name='Centro', address='Calle 1')
        norte = Delegation.objects.create(name='Norte', address='Calle 2')
        cargo = Position.objects.create(name='Encargado')
        user_centro = User.objects.create_user(username='func_centro', password='x', is_staff=True)
        Employee.objects.create(user=user_centro, delegation=centro, position=cargo, name='Func Centro')

        self.compromiso_centro = Commitment.objects.create(
            title='Centro', delegation=centro, due_date=datetime.date(2026, 1, 1), status='registered',
        )
        self.compromiso_norte = Commitment.objects.create(
            title='Norte', delegation=norte, due_date=datetime.date(2026, 1, 1), status='registered',
        )
        self.user_centro = user_centro
        self.factory = RequestFactory()

    def test_funcionario_solo_ve_compromisos_de_su_delegacion(self):
        request = self.factory.get('/admin/agenda/commitment/')
        request.user = self.user_centro
        admin_instance = CompromisoAdmin(Commitment, None)

        queryset = admin_instance.get_queryset(request)

        self.assertIn(self.compromiso_centro, queryset)
        self.assertNotIn(self.compromiso_norte, queryset)
