
from django.test import TestCase
from django.urls import reverse

from core.testing import CLAVE_TEST, sembrar_datos_demo


class LoginTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        sembrar_datos_demo()

    def test_pagina_de_login_responde(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/login.html')

    def test_login_correcto_redirige_al_dashboard(self):
        response = self.client.post(reverse('login'), {
            'username': 'admin_centro', 'password': CLAVE_TEST,
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
            'username': 'admin_sgr', 'password': CLAVE_TEST, 'next': '/admin/',
        })
        self.assertRedirects(response, '/admin/')

    def test_login_del_admin_redirige_al_login_propio(self):
        response = self.client.get('/admin/login/?next=/admin/')
        self.assertRedirects(response, reverse('login') + '?next=/admin/')

    def test_admin_sin_sesion_termina_en_login_propio(self):
        response = self.client.get('/admin/', follow=True)
        self.assertTemplateUsed(response, 'registration/login.html')

    def test_logout_por_post_redirige_al_login(self):
        self.client.login(username='admin_centro', password=CLAVE_TEST)
        response = self.client.post(reverse('logout'))
        self.assertRedirects(response, reverse('login'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_login_muestra_mensaje_de_bienvenida(self):
        response = self.client.post(reverse('login'), {
            'username': 'admin_centro', 'password': CLAVE_TEST,
        }, follow=True)
        self.assertContains(response, 'Bienvenido/a')

    def test_logout_muestra_mensaje_y_limpia_la_sesion(self):
        self.client.login(username='admin_centro', password=CLAVE_TEST)
        self.client.get(reverse('dashboard'), {'period': 1})
        response = self.client.post(reverse('logout'), follow=True)
        self.assertContains(response, 'Sesión cerrada correctamente.')
        self.assertNotIn('dashboard_periodo_id', self.client.session)

    def test_logout_por_get_no_esta_permitido(self):
        self.client.login(username='admin_centro', password=CLAVE_TEST)
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



class AccesoPorRolEnLoginTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        sembrar_datos_demo()

    def _ingresar(self, username, password):
        return self.client.post(reverse('login'), {'username': username, 'password': password}, follow=True)

    def test_usuario_sin_rol_no_puede_iniciar_sesion(self):
        from django.contrib.auth.models import User

        User.objects.create_user(username='sin_rol', password='Clave#Segura2026')
        response = self._ingresar('sin_rol', 'Clave#Segura2026')
        self.assertContains(response, 'Usuario o contraseña incorrectos.')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_funcionario_sin_perfil_no_puede_iniciar_sesion(self):
        from django.contrib.auth.models import Group, User

        user = User.objects.create_user(username='sin_perfil', password='Clave#Segura2026')
        user.groups.add(Group.objects.get(name='Funcionarios'))
        response = self._ingresar('sin_perfil', 'Clave#Segura2026')
        self.assertContains(response, 'Usuario o contraseña incorrectos.')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_verificador_sin_perfil_si_puede_iniciar_sesion(self):
        # El verificador es un rol global: no necesita perfil de delegación.
        response = self._ingresar('verificador_leia', CLAVE_TEST)
        self.assertRedirects(response, reverse('dashboard'))

    def test_contrasena_incorrecta_muestra_un_solo_mensaje_generico(self):
        response = self._ingresar('admin_centro', 'incorrecta')
        self.assertContains(response, 'Usuario o contraseña incorrectos.', count=1)
        self.assertNotContains(response, 'rol asignado')


class MensajesYPagina403Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        sembrar_datos_demo()

    def test_mensaje_de_error_usa_la_clase_danger_de_bootstrap(self):
        response = self.client.get(reverse('recuperar_nueva'), follow=True)
        self.assertContains(response, 'La validación expiró')
        self.assertContains(response, 'alert-danger')
        self.assertNotContains(response, 'alert-error')

    def test_403_usa_la_plantilla_del_sitio(self):
        self.client.login(username='verificador_leia', password=CLAVE_TEST)
        response = self.client.get(reverse('actividad_list'))
        self.assertEqual(response.status_code, 403)
        self.assertTemplateUsed(response, '403.html')
        self.assertContains(response, 'Acceso denegado', status_code=403)
        self.assertContains(response, reverse('dashboard'), status_code=403)


class SesionAlVolverAtrasTests(TestCase):
    """Volver al login con la sesión abierta (botón atrás tras ingresar) la cierra, y las páginas con
    sesión no quedan en la caché del navegador."""

    @classmethod
    def setUpTestData(cls):
        sembrar_datos_demo()

    def setUp(self):
        self.assertTrue(self.client.login(username='admin_centro', password=CLAVE_TEST))

    def test_abrir_el_login_con_sesion_la_cierra(self):
        response = self.client.get(reverse('login'), follow=True)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertContains(response, 'Por seguridad, se cerró su sesión.')
        # «Adelante» vuelve a pedir el dashboard: ya no hay sesión, así que pide ingresar.
        self.assertRedirects(self.client.get(reverse('dashboard')), f"{reverse('login')}?next={reverse('dashboard')}")

    def test_el_cierre_queda_en_la_traza(self):
        from colaboracion.models import AuditLog

        self.client.get(reverse('login'))
        self.assertTrue(AuditLog.objects.filter(action='logout', user__username='admin_centro').exists())

    def test_paginas_con_sesion_no_se_guardan_en_cache(self):
        for url in (reverse('dashboard'), reverse('actividad_list'), reverse('compromiso_list'), '/admin/'):
            with self.subTest(url=url):
                cabecera = self.client.get(url)['Cache-Control']
                self.assertIn('no-store', cabecera)
                self.assertIn('private', cabecera)

    def test_el_login_tampoco_se_guarda_en_cache(self):
        self.client.logout()
        self.assertIn('no-store', self.client.get(reverse('login'))['Cache-Control'])

    def test_todas_las_paginas_recargan_si_el_navegador_las_restaura_de_memoria(self):
        for url in (reverse('login'), reverse('dashboard'), '/admin/'):
            self.client.login(username='admin_centro', password=CLAVE_TEST)
            with self.subTest(url=url):
                self.assertContains(self.client.get(url, follow=True), 'js/sesion.js')
