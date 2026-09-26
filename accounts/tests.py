from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse


class LoginTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_data', stdout=StringIO())

    def test_pagina_de_login_responde(self):
        response = self.client.get(reverse('accounts:login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/login.html')

    def test_login_correcto_redirige_al_dashboard(self):
        response = self.client.post(reverse('accounts:login'), {
            'username': 'admin_centro', 'password': 'AdminCentro#2026SGR',
        })
        self.assertRedirects(response, reverse('monitoreo:dashboard'))

    def test_login_incorrecto_muestra_error(self):
        response = self.client.post(reverse('accounts:login'), {
            'username': 'admin_centro', 'password': 'incorrecta',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Usuario o contraseña incorrectos.')

    def test_login_respeta_next(self):
        response = self.client.post(reverse('accounts:login'), {
            'username': 'admin_sgr', 'password': 'Admin#2026SGR', 'next': '/admin/',
        })
        self.assertRedirects(response, '/admin/')

    def test_login_del_admin_redirige_al_login_propio(self):
        response = self.client.get('/admin/login/?next=/admin/')
        self.assertRedirects(response, reverse('accounts:login') + '?next=/admin/')

    def test_admin_sin_sesion_termina_en_login_propio(self):
        response = self.client.get('/admin/', follow=True)
        self.assertTemplateUsed(response, 'registration/login.html')

    def test_logout_por_post_redirige_al_login(self):
        self.client.login(username='admin_centro', password='AdminCentro#2026SGR')
        response = self.client.post(reverse('accounts:logout'))
        self.assertRedirects(response, reverse('accounts:login'))
        self.assertNotIn('_auth_user_id', self.client.session)
