"""Pruebas de seguridad de la Evaluación 3 (OWASP Top 10).

Cada clase corresponde a una deficiencia del registro en docs/evaluacion-3/README.md:
- A07 Fallas de identificación y autenticación: el login no limitaba los intentos fallidos.
- A09 Fallas de registro y monitoreo: los ingresos fallidos y los accesos denegados no quedaban registrados.
- A05 Configuración de seguridad incorrecta: las respuestas no traían política de seguridad de contenido (CSP).
"""
import re
from pathlib import Path
from datetime import timedelta

from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from colaboracion.models import AuditLog
from core.testing import CLAVE_TEST, SesionTestMixin, sembrar_datos_demo

CLAVE_MALA = 'Incorrecta#2026'
# Valores por defecto para que la prueba muestre la falla real incluso antes de existir los ajustes.
MAX_INTENTOS = getattr(settings, 'LOGIN_MAX_INTENTOS', 5)
MAX_INTENTOS_IP = getattr(settings, 'LOGIN_MAX_INTENTOS_IP', 20)
VENTANA_MINUTOS = getattr(settings, 'LOGIN_VENTANA_MINUTOS', 15)


class IntentoMixin:
    def intentar(self, username, password, ip='10.0.0.1'):
        return self.client.post(reverse('login'), {'username': username, 'password': password}, REMOTE_ADDR=ip)

    def sesion_iniciada(self):
        return '_auth_user_id' in self.client.session


class A07LimiteDeIntentosTests(IntentoMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        sembrar_datos_demo()

    def test_bloquea_la_cuenta_tras_el_maximo_de_intentos_fallidos(self):
        for _ in range(MAX_INTENTOS):
            self.intentar('admin_centro', CLAVE_MALA)
        # Con la clave correcta tampoco entra mientras dure el bloqueo.
        respuesta = self.intentar('admin_centro', CLAVE_TEST)
        self.assertFalse(self.sesion_iniciada())
        # El bloqueo responde con el mismo mensaje genérico; queda registrado como login_bloqueado.
        self.assertContains(respuesta, 'Usuario o contraseña incorrectos.')
        self.assertNotContains(respuesta, 'intentos')
        self.assertTrue(AuditLog.objects.filter(action='login_bloqueado', detail='admin_centro').exists())

    def test_el_bloqueo_no_revela_si_la_clave_era_correcta(self):
        for _ in range(MAX_INTENTOS):
            self.intentar('admin_centro', CLAVE_MALA)
        con_clave_buena = self.intentar('admin_centro', CLAVE_TEST).content.decode()
        con_clave_mala = self.intentar('admin_centro', CLAVE_MALA).content.decode()
        # El token CSRF y el nonce de la CSP cambian en cada respuesta; el resto debe ser idéntico.
        limpiar = lambda html: re.sub(r'(value|nonce)="[A-Za-z0-9_-]{16,}"', '', html)
        self.assertEqual(limpiar(con_clave_buena), limpiar(con_clave_mala))

    def test_bloquea_tambien_usuarios_que_no_existen(self):
        # Mismo trato para cualquier nombre: el bloqueo no sirve para averiguar qué cuentas existen.
        for _ in range(MAX_INTENTOS):
            self.intentar('no_existe', CLAVE_MALA)
        self.assertContains(self.intentar('no_existe', CLAVE_MALA), 'Usuario o contraseña incorrectos.')
        self.assertTrue(AuditLog.objects.filter(action='login_bloqueado', detail='no_existe').exists())

    def test_el_bloqueo_termina_al_pasar_la_ventana(self):
        for _ in range(MAX_INTENTOS):
            self.intentar('admin_centro', CLAVE_MALA)
        antes = timezone.now() - timedelta(minutes=VENTANA_MINUTOS + 1)
        AuditLog.objects.filter(action='login_fallido').update(date=antes)
        self.intentar('admin_centro', CLAVE_TEST)
        self.assertTrue(self.sesion_iniciada())

    def test_un_ingreso_correcto_reinicia_el_contador(self):
        for _ in range(MAX_INTENTOS - 1):
            self.intentar('admin_centro', CLAVE_MALA)
        self.intentar('admin_centro', CLAVE_TEST)
        self.assertTrue(self.sesion_iniciada())
        self.client.post(reverse('logout'))
        for _ in range(MAX_INTENTOS - 1):
            self.intentar('admin_centro', CLAVE_MALA)
        self.intentar('admin_centro', CLAVE_TEST)
        self.assertTrue(self.sesion_iniciada())

    def test_bloquea_una_ip_que_prueba_muchas_cuentas(self):
        # Probar una clave común contra muchas cuentas (password spraying) desde la misma IP.
        for n in range(MAX_INTENTOS_IP):
            self.intentar(f'usuario{n}', CLAVE_MALA, ip='10.9.9.9')
        self.assertContains(self.intentar('admin_norte', CLAVE_TEST, ip='10.9.9.9'), 'Usuario o contraseña incorrectos.')
        self.assertFalse(self.sesion_iniciada())
        # Otra IP no queda afectada.
        self.intentar('admin_norte', CLAVE_TEST, ip='10.1.1.1')
        self.assertTrue(self.sesion_iniciada())


class A09RegistroDeEventosTests(IntentoMixin, SesionTestMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        sembrar_datos_demo()

    def test_registra_el_ingreso_fallido_con_usuario_e_ip_sin_la_clave(self):
        self.intentar('admin_centro', CLAVE_MALA, ip='10.2.3.4')
        evento = AuditLog.objects.get(action='login_fallido')
        self.assertEqual(evento.detail, 'admin_centro')
        self.assertEqual(evento.ip, '10.2.3.4')
        self.assertNotIn(CLAVE_MALA, evento.detail)

    def test_registra_el_ingreso_correcto_y_el_cierre_de_sesion(self):
        self.intentar('admin_centro', CLAVE_TEST, ip='10.2.3.4')
        self.client.post(reverse('logout'), REMOTE_ADDR='10.2.3.4')
        acciones = list(AuditLog.objects.filter(user__username='admin_centro').values_list('action', 'ip'))
        self.assertIn(('login_exitoso', '10.2.3.4'), acciones)
        self.assertIn(('logout', '10.2.3.4'), acciones)

    def test_registra_el_bloqueo(self):
        for _ in range(MAX_INTENTOS + 1):
            self.intentar('admin_centro', CLAVE_MALA)
        self.assertTrue(AuditLog.objects.filter(action='login_bloqueado', detail='admin_centro').exists())

    def test_registra_el_acceso_denegado(self):
        self.ingresar('verificador_leia')
        respuesta = self.client.get(reverse('compromiso_list'), REMOTE_ADDR='10.2.3.4')
        self.assertEqual(respuesta.status_code, 403)
        evento = AuditLog.objects.get(action='acceso_denegado')
        self.assertEqual(evento.user.username, 'verificador_leia')
        self.assertEqual(evento.detail, reverse('compromiso_list'))
        self.assertEqual(evento.ip, '10.2.3.4')


class A05PoliticaDeContenidoTests(SesionTestMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        sembrar_datos_demo()

    def politica(self, respuesta):
        cabecera = respuesta.headers.get('Content-Security-Policy', '')
        return dict((d.split()[0], d.split()[1:]) for d in cabecera.split(';') if d.strip())

    def test_las_respuestas_traen_una_politica_de_contenido_estricta(self):
        politica = self.politica(self.client.get(reverse('login')))
        self.assertEqual(politica.get('default-src'), ["'self'"])
        self.assertEqual(politica.get('object-src'), ["'none'"])
        self.assertEqual(politica.get('frame-ancestors'), ["'none'"])
        self.assertEqual(politica.get('base-uri'), ["'self'"])
        self.assertEqual(politica.get('form-action'), ["'self'"])
        # Un script inyectado no se ejecuta: no se permite JavaScript en línea sin nonce.
        self.assertNotIn("'unsafe-inline'", politica.get('script-src', []))
        self.assertNotIn("'unsafe-eval'", politica.get('script-src', []))

    def test_los_scripts_en_linea_propios_llevan_el_nonce_de_la_respuesta(self):
        self.ingresar('admin_sgr')
        # El login va al final: abrirlo con la sesión iniciada la cierra (vuelta atrás tras ingresar).
        for url in (reverse('dashboard'), reverse('actividad_list'), '/admin/', '/admin/actividades/activity/', reverse('login')):
            with self.subTest(url=url):
                respuesta = self.client.get(url)
                fuentes = self.politica(respuesta).get('script-src', [])
                nonce = next((v[7:-1] for v in fuentes if v.startswith("'nonce-")), None)
                self.assertIsNotNone(nonce, 'la respuesta no declara un nonce para scripts')
                html = respuesta.content.decode()
                for etiqueta in re.findall(r'<script(?![^>]*\bsrc=)[^>]*>', html):
                    self.assertIn(f'nonce="{nonce}"', etiqueta)

    def test_ninguna_plantilla_usa_javascript_en_atributos(self):
        # La CSP bloquea onclick=, onchange=, etc.: la interfaz dejaría de responder sin aviso.
        raiz = Path(settings.BASE_DIR)
        for plantilla in raiz.glob('**/templates/**/*.html'):
            if '.venv' in plantilla.parts or 'site-packages' in plantilla.parts:
                continue
            with self.subTest(plantilla=str(plantilla.relative_to(raiz))):
                self.assertNotRegex(plantilla.read_text(encoding='utf-8'), r'\son[a-z]+\s*=\s*"')


class A03InyeccionCsrfYSesionTests(SesionTestMixin, TestCase):
    """Controles que ya existían y el plan de pruebas verifica: inyección SQL, XSS, CSRF y sesión."""

    @classmethod
    def setUpTestData(cls):
        sembrar_datos_demo()

    def test_sql_en_filtros_y_busquedas_no_altera_la_consulta(self):
        from actividades.models import Activity

        self.ingresar('admin_sgr')
        # Los filtros solo aceptan números: el texto inyectado se ignora y la lista es la misma.
        normal = self.client.get(reverse('actividad_list')).context['page_obj'].paginator.count
        inyectado = self.client.get(reverse('actividad_list'), {'period': "1 OR 1=1", 'status': "' OR '1'='1"})
        self.assertEqual(inyectado.status_code, 200)
        self.assertEqual(inyectado.context['page_obj'].paginator.count, normal)
        # La búsqueda del Admin va por el ORM (consulta parametrizada): el texto se busca literal.
        busqueda = self.client.get('/admin/actividades/activity/', {'q': "' OR '1'='1' -- "})
        self.assertEqual(busqueda.status_code, 200)
        self.assertEqual(busqueda.context['cl'].result_count, 0)
        self.assertGreater(Activity.objects.count(), 0)

    def test_xss_guardado_se_muestra_escapado(self):
        from actividades.models import SocialCase

        gestion = SocialCase.objects.filter(activity__delegation__name='Delegación Centro').first()
        gestion.description = '<script>alert("xss")</script>'
        gestion.save(update_fields=['description'])
        self.ingresar('admin_centro')
        html = self.client.get(reverse('atencion_list'), {'activity': gestion.activity_id}).content.decode()
        self.assertIn('&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;', html)
        self.assertNotIn('<script>alert("xss")</script>', html)

    def test_textos_de_ayuda_se_escapan_salvo_el_html_marcado_como_seguro(self):
        # D-07: form_campos.html ya no usa |safe. Un help_text con HTML se muestra como texto; la lista
        # de reglas de contraseña de Django sigue como lista porque Django la marca como HTML seguro.
        from django import forms
        from django.contrib.auth.forms import SetPasswordForm
        from django.contrib.auth.models import User
        from django.template.loader import render_to_string

        class FormularioConAyudaMaliciosa(forms.Form):
            campo = forms.CharField(help_text='<img src=x onerror=alert(1)>')

        html = render_to_string('includes/form_campos.html', {'form': FormularioConAyudaMaliciosa()})
        self.assertIn('&lt;img src=x onerror=alert(1)&gt;', html)
        self.assertNotIn('<img src=x', html)
        html = render_to_string('includes/form_campos.html', {'form': SetPasswordForm(User.objects.first())})
        self.assertIn('<ul><li>', html)
        plantillas = Path(settings.BASE_DIR, 'templates')
        for plantilla in plantillas.rglob('*.html'):
            self.assertNotRegex(plantilla.read_text(encoding='utf-8'), r'help_text\s*\|\s*safe', str(plantilla))

    def test_post_sin_token_csrf_es_rechazado(self):
        from django.test import Client

        from agenda.models import Commitment

        cliente = Client(enforce_csrf_checks=True)
        cliente.login(username='admin_centro', password=CLAVE_TEST)
        compromiso = Commitment.objects.filter(delegation__name='Delegación Centro').first()
        respuesta = cliente.post(reverse('compromiso_delete', args=[compromiso.pk]))
        self.assertEqual(respuesta.status_code, 403)
        self.assertTrue(Commitment.objects.filter(pk=compromiso.pk).exists())

    def test_la_sesion_cambia_de_identificador_al_ingresar(self):
        # Evita la fijación de sesión: un identificador conocido antes del login deja de servir.
        sesion = self.client.session
        sesion['marca'] = 1
        sesion.save()
        antes = sesion.session_key
        self.client.post(reverse('login'), {'username': 'admin_centro', 'password': CLAVE_TEST})
        self.assertIn('_auth_user_id', self.client.session)
        self.assertNotEqual(self.client.session.session_key, antes)

    def test_la_cookie_de_sesion_no_es_accesible_desde_javascript(self):
        respuesta = self.client.post(reverse('login'), {'username': 'admin_centro', 'password': CLAVE_TEST})
        self.assertTrue(respuesta.cookies[settings.SESSION_COOKIE_NAME]['httponly'])
        self.assertEqual(respuesta.cookies[settings.SESSION_COOKIE_NAME]['samesite'], 'Lax')
