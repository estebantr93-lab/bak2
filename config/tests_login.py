from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse


class LoginTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_data', stdout=StringIO())

    def test_pagina_de_login_responde(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/login.html')

    def test_login_correcto_redirige_al_dashboard(self):
        response = self.client.post(reverse('login'), {
            'username': 'admin_centro', 'password': 'AdminCentro#2026SGR',
        })
        self.assertRedirects(response, reverse('dashboard'))

    def test_login_incorrecto_muestra_error(self):
        response = self.client.post(reverse('login'), {
            'username': 'admin_centro', 'password': 'incorrecta',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Usuario o contraseña incorrectos.')

    def test_login_respeta_next(self):
        response = self.client.post(reverse('login'), {
            'username': 'admin_sgr', 'password': 'Admin#2026SGR', 'next': '/admin/',
        })
        self.assertRedirects(response, '/admin/')

    def test_login_del_admin_redirige_al_login_propio(self):
        response = self.client.get('/admin/login/?next=/admin/')
        self.assertRedirects(response, reverse('login') + '?next=/admin/')

    def test_admin_sin_sesion_termina_en_login_propio(self):
        response = self.client.get('/admin/', follow=True)
        self.assertTemplateUsed(response, 'registration/login.html')

    def test_logout_por_post_redirige_al_login(self):
        self.client.login(username='admin_centro', password='AdminCentro#2026SGR')
        response = self.client.post(reverse('logout'))
        self.assertRedirects(response, reverse('login'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_login_muestra_mensaje_de_bienvenida(self):
        response = self.client.post(reverse('login'), {
            'username': 'admin_centro', 'password': 'AdminCentro#2026SGR',
        }, follow=True)
        self.assertContains(response, 'Bienvenido/a')

    def test_logout_muestra_mensaje_y_limpia_la_sesion(self):
        self.client.login(username='admin_centro', password='AdminCentro#2026SGR')
        self.client.get(reverse('dashboard'), {'periodo': 1})
        response = self.client.post(reverse('logout'), follow=True)
        self.assertContains(response, 'Sesión cerrada correctamente.')
        self.assertNotIn('dashboard_periodo_id', self.client.session)

    def test_logout_por_get_no_esta_permitido(self):
        self.client.login(username='admin_centro', password='AdminCentro#2026SGR')
        response = self.client.get(reverse('logout'))
        self.assertEqual(response.status_code, 405)

    def test_rutas_de_django_auth_disponibles(self):
        self.assertEqual(reverse('login'), '/accounts/login/')
        self.assertEqual(reverse('logout'), '/accounts/logout/')
        self.assertEqual(reverse('password_change'), '/accounts/password_change/')


class ConfiguracionSesionTests(TestCase):
    def test_cookies_de_sesion_seguras(self):
        from django.conf import settings

        self.assertEqual(settings.SESSION_COOKIE_AGE, 7200)
        self.assertTrue(settings.SESSION_COOKIE_HTTPONLY)
        self.assertEqual(settings.SESSION_COOKIE_SAMESITE, 'Lax')
        self.assertEqual(settings.LOGIN_REDIRECT_URL, 'dashboard')

