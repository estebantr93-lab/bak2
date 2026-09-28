"""El admin comparte la barra, el menú, el tema y el pie de la app, y queda en español."""
from django.test import TestCase
from django.urls import reverse

from core.testing import CLAVE_TEST, sembrar_datos_demo


class AdminMismoSistemaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        sembrar_datos_demo()

    def test_admin_usa_la_barra_y_el_menu_del_sistema(self):
        self.client.login(username='admin_centro', password=CLAVE_TEST)
        html = self.client.get(reverse('admin:index')).content.decode()
        self.assertIn('SGR · La Serena', html)
        self.assertIn('class="sgr-menu-boton"', html)
        self.assertIn('data-tema="dark"', html)
        self.assertIn(reverse('dashboard'), html)
        self.assertIn(f'action="{reverse("logout")}"', html)
        self.assertIn('class="sgr-pie"', html)
        # "Administración" aparece activa y los enlaces respetan permisos (admin_centro no gestiona usuarios).
        self.assertIn('class="sgr-menu-item active" href="/admin/"', html)
        self.assertNotIn('/admin/auth/user/', html)

    def test_listado_del_admin_en_espanol(self):
        self.client.login(username='admin_centro', password=CLAVE_TEST)
        html = self.client.get(reverse('admin:actividades_activity_changelist')).content.decode()
        self.assertIn('- Seleccione una opción -', html)
        self.assertIn('Ejecutar', html)
        self.assertNotIn('Select an option', html)

    def test_app_y_admin_guardan_el_tema_en_la_misma_clave(self):
        self.client.login(username='admin_centro', password=CLAVE_TEST)
        for url in (reverse('dashboard'), reverse('admin:index')):
            html = self.client.get(url).content.decode()
            self.assertIn("localStorage.getItem('theme')", html, url)
            self.assertIn('js/tema.js', html, url)
