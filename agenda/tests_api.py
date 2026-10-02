"""API REST de compromisos (Unidad 3 · Clase 1): CRUD JSON con estados HTTP comprobables y las mismas
reglas de seguridad del CRUD web (sesión, permisos por rol, alcance por delegación, borrado lógico)."""
import datetime

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from colaboracion.models import AuditLog
from core.testing import SesionTestMixin, sembrar_datos_demo
from funcionarios.models import Employee

from .models import Commitment

LISTA = reverse('compromiso-list')


def detalle(pk):
    return reverse('compromiso-detail', args=[pk])


class ApiCompromisosTests(SesionTestMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        sembrar_datos_demo()

    def setUp(self):
        self.ingresar('admin_centro')
        self.vence = (timezone.localdate() + datetime.timedelta(days=10)).isoformat()

    def crear(self, **extra):
        return self.client.post(LISTA, {'title': 'Reunión con junta de vecinos', 'due_date': self.vence, **extra},
                                content_type='application/json')

    # --- Secuencia de la clase: lista, creación, detalle, edición, error 400, eliminación y 404 ---
    def test_get_lista_200_en_json_y_solo_de_su_delegacion(self):
        respuesta = self.client.get(LISTA)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta['Content-Type'], 'application/json')
        ids = {c['id'] for c in respuesta.json()}
        self.assertEqual(ids, set(Commitment.objects.filter(delegation__name='Delegación Centro').values_list('pk', flat=True)))

    def test_post_valido_201_y_la_delegacion_es_la_del_usuario(self):
        respuesta = self.crear()
        self.assertEqual(respuesta.status_code, 201)
        compromiso = Commitment.objects.get(pk=respuesta.json()['id'])
        self.assertEqual(compromiso.delegation.name, 'Delegación Centro')
        self.assertEqual(respuesta.json()['status'], 'registered')

    def test_get_detalle_y_patch_parcial_200(self):
        pk = self.crear().json()['id']
        self.assertEqual(self.client.get(detalle(pk)).status_code, 200)
        respuesta = self.client.patch(detalle(pk), {'status': 'in_progress'}, content_type='application/json')
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()['status_display'], 'En proceso')
        self.assertEqual(Commitment.objects.get(pk=pk).title, 'Reunión con junta de vecinos')  # PATCH no toca lo demás

    def test_post_invalido_400_con_las_reglas_de_la_web(self):
        respuesta = self.client.post(LISTA, {'title': 'Ab', 'due_date': '2020-01-01'}, content_type='application/json')
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn('al menos 5 caracteres', respuesta.json()['title'][0])
        self.assertIn('pasado', respuesta.json()['due_date'][0])

    def test_reglas_del_modelo_tambien_en_patch(self):
        pk = self.crear().json()['id']
        respuesta = self.client.patch(detalle(pk), {'status': 'done'}, content_type='application/json')
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn('observaciones', respuesta.json()['notes'][0])
        norte = Employee.objects.filter(delegation__name='Delegación Norte').first()
        respuesta = self.client.patch(detalle(pk), {'responsible': norte.pk}, content_type='application/json')
        self.assertEqual(respuesta.status_code, 400)  # un responsable de otra delegación no es una opción válida

    def test_delete_204_es_logico_y_despues_404(self):
        pk = self.crear().json()['id']
        self.assertEqual(self.client.delete(detalle(pk)).status_code, 204)
        self.assertIsNotNone(Commitment.all_objects.get(pk=pk).deleted_at)  # el registro sigue en la base
        respuesta = self.client.get(detalle(pk))
        self.assertEqual(respuesta.status_code, 404)
        self.assertEqual(respuesta.json(), {'detail': 'Compromiso no encontrado.'})

    def test_cada_operacion_queda_en_la_traza_con_quien_y_que_cambio(self):
        pk = self.crear().json()['id']
        self.client.patch(detalle(pk), {'status': 'in_progress'}, content_type='application/json')
        self.client.delete(detalle(pk))
        acciones = list(AuditLog.objects.filter(entity_type='Commitment', entity_id=pk).order_by('date')
                        .values_list('action', 'user__username'))
        self.assertEqual(acciones, [('crear', 'admin_centro'), ('modificar', 'admin_centro'), ('eliminar', 'admin_centro')])
        cambio = AuditLog.objects.get(entity_id=pk, action='modificar')
        self.assertEqual(cambio.changes['status'], ['registered', 'in_progress'])

    # --- Seguridad: la API no es una puerta trasera ---
    def test_sin_sesion_no_hay_acceso(self):
        self.client.logout()
        self.assertEqual(self.client.get(LISTA).status_code, 403)
        self.assertEqual(self.crear().status_code, 403)

    def test_compromiso_de_otra_delegacion_404(self):
        ajeno = Commitment.objects.filter(delegation__name='Delegación Norte').first()
        self.assertEqual(self.client.get(detalle(ajeno.pk)).status_code, 404)
        self.assertEqual(self.client.patch(detalle(ajeno.pk), {'status': 'done'}, content_type='application/json').status_code, 404)
        self.assertEqual(self.client.delete(detalle(ajeno.pk)).status_code, 404)

    def test_usuario_acotado_no_puede_elegir_otra_delegacion(self):
        from core.models import Delegation
        norte = Delegation.objects.get(name='Delegación Norte')
        self.assertEqual(self.crear(delegation=norte.pk).status_code, 400)

    def test_superadmin_ve_todas_y_debe_indicar_la_delegacion(self):
        self.ingresar('admin_sgr')
        self.assertEqual(len(self.client.get(LISTA).json()), Commitment.objects.count())
        self.assertEqual(self.crear().status_code, 400)
        from core.models import Delegation
        self.assertEqual(self.crear(delegation=Delegation.objects.get(name='Delegación Norte').pk).status_code, 201)

    def test_funcionario_solo_consulta(self):
        # El rol Funcionario tiene solo el permiso de ver compromisos: lista sí, crear o modificar no.
        self.ingresar('funcionario_centro')
        self.assertEqual(self.client.get(LISTA).status_code, 200)
        self.assertEqual(self.crear().status_code, 403)
        propio = Commitment.objects.filter(responsible__user__username='funcionario_centro').first()
        respuesta = self.client.patch(detalle(propio.pk), {'notes': 'cambio'}, content_type='application/json')
        self.assertEqual(respuesta.status_code, 403)
        self.assertNotEqual(Commitment.objects.get(pk=propio.pk).notes, 'cambio')

    def test_rol_sin_permiso_sobre_compromisos_recibe_403(self):
        self.ingresar('verificador_leia')  # el verificador no tiene permisos sobre compromisos
        self.assertEqual(self.client.get(LISTA).status_code, 403)

    def test_las_paginas_web_siguen_funcionando(self):
        self.assertEqual(self.client.get(reverse('compromiso_list')).status_code, 200)
        self.assertEqual(self.client.get(reverse('dashboard')).status_code, 200)
