from django.test import TestCase


class InicioViewTests(TestCase):
    def test_raiz_responde_200(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_raiz_es_publica_sin_iniciar_sesion(self):
        response = self.client.get('/')
        self.assertTemplateUsed(response, 'landing.html')

    def test_raiz_enlaza_al_admin(self):
        response = self.client.get('/')
        self.assertContains(response, 'href="/admin/"')

    def test_raiz_no_expone_los_modulos_internos(self):
        response = self.client.get('/')
        self.assertNotContains(response, 'Módulos del sistema')
        for app in ['medicion', 'colaboracion', 'admin_utils']:
            self.assertNotContains(response, app)
