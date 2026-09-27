import re
from datetime import timedelta

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from core.testing import sembrar_datos_demo

from .models import CodigoRecuperacion

EMAIL = 'admin_centro@demo.sgr.local'
NUEVA = 'NuevaClave#2026sgr'


@override_settings(MAILERS={'default': {'BACKEND': 'django.core.mail.backends.locmem.EmailBackend'}})
class RecuperacionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        sembrar_datos_demo()

    def _solicitar(self, email=EMAIL):
        return self.client.post(reverse('recuperar_solicitar'), {'email': email}, follow=True)

    def _codigo_enviado(self):
        return re.search(r'\b(\d{6})\b', mail.outbox[-1].body).group(1)

    def _flujo_hasta_codigo(self):
        self._solicitar()
        return self._codigo_enviado()

    def test_envia_codigo_de_6_digitos_y_guarda_solo_el_hash(self):
        codigo = self._flujo_hasta_codigo()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [EMAIL])
        registro = CodigoRecuperacion.objects.get()
        self.assertNotEqual(registro.codigo_hash, codigo)
        self.assertNotIn(codigo, registro.codigo_hash)
        vigencia = (registro.expira - registro.creado).total_seconds()
        self.assertAlmostEqual(vigencia, 120, delta=2)

    def test_respuesta_generica_si_el_correo_no_existe(self):
        existe = self._solicitar()
        no_existe = self.client.post(reverse('recuperar_solicitar'), {'email': 'nadie@x.cl'}, follow=True)
        self.assertEqual(len(mail.outbox), 1)
        self.assertContains(existe, 'Si el correo corresponde')
        self.assertContains(no_existe, 'Si el correo corresponde')
        self.assertEqual(existe.redirect_chain, no_existe.redirect_chain)

    def test_flujo_completo_cambia_contrasena_con_set_password(self):
        codigo = self._flujo_hasta_codigo()
        response = self.client.post(reverse('recuperar_codigo'), {'codigo': codigo})
        self.assertRedirects(response, reverse('recuperar_nueva'))
        response = self.client.post(reverse('recuperar_nueva'), {'new_password1': NUEVA, 'new_password2': NUEVA})
        self.assertRedirects(response, reverse('login'))
        self.assertTrue(User.objects.get(email=EMAIL).check_password(NUEVA))
        self.assertTrue(self.client.login(username='admin_centro', password=NUEVA))

    def test_codigo_es_de_uso_unico(self):
        codigo = self._flujo_hasta_codigo()
        self.client.post(reverse('recuperar_codigo'), {'codigo': codigo})
        session = self.client.session
        session['recuperacion_email'] = EMAIL
        session.save()
        response = self.client.post(reverse('recuperar_codigo'), {'codigo': codigo})
        self.assertContains(response, 'Código incorrecto o vencido.')

    def test_codigo_vencido_no_se_acepta(self):
        codigo = self._flujo_hasta_codigo()
        CodigoRecuperacion.objects.update(expira=timezone.now() - timedelta(seconds=1))
        response = self.client.post(reverse('recuperar_codigo'), {'codigo': codigo})
        self.assertContains(response, 'Código incorrecto o vencido.')

    def test_nuevo_codigo_invalida_el_anterior(self):
        primero = self._flujo_hasta_codigo()
        segundo = self._flujo_hasta_codigo()
        self.assertEqual(CodigoRecuperacion.objects.filter(usado=False).count(), 1)
        if primero != segundo:
            response = self.client.post(reverse('recuperar_codigo'), {'codigo': primero})
            self.assertContains(response, 'Código incorrecto o vencido.')
        response = self.client.post(reverse('recuperar_codigo'), {'codigo': segundo})
        self.assertRedirects(response, reverse('recuperar_nueva'))

    def test_maximo_5_intentos(self):
        codigo = self._flujo_hasta_codigo()
        incorrecto = f'{(int(codigo) + 1) % 1000000:06d}'
        for _ in range(4):
            response = self.client.post(reverse('recuperar_codigo'), {'codigo': incorrecto})
            self.assertContains(response, 'Código incorrecto o vencido.')
        response = self.client.post(reverse('recuperar_codigo'), {'codigo': incorrecto})
        self.assertRedirects(response, reverse('recuperar_solicitar'))
        self.assertTrue(CodigoRecuperacion.objects.get().usado)
        # Ni siquiera el código correcto sirve después del bloqueo.
        session = self.client.session
        session['recuperacion_email'] = EMAIL
        session.save()
        response = self.client.post(reverse('recuperar_codigo'), {'codigo': codigo})
        self.assertContains(response, 'Código incorrecto o vencido.')

    def test_no_se_puede_saltar_a_nueva_contrasena(self):
        response = self.client.get(reverse('recuperar_nueva'))
        self.assertRedirects(response, reverse('recuperar_solicitar'))

    def test_login_enlaza_a_recuperacion(self):
        response = self.client.get(reverse('login'))
        self.assertContains(response, reverse('recuperar_solicitar'))
