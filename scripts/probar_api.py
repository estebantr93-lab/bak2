"""Secuencia de pruebas de la API REST de compromisos (Unidad 3 · Clase 1, diapositiva 14).

Con el servidor levantado (python manage.py runserver), desde la raíz del proyecto:

    SGR_URL=http://127.0.0.1:8000 SGR_USUARIO=admin_centro SGR_CLAVE='<clave>' python scripts/probar_api.py

Inicia sesión como en el navegador (la API usa la sesión del sitio hasta agregar JWT en la Clase 2) y
ejecuta: GET lista → POST válido (201) → GET detalle → PATCH parcial → POST inválido (400) →
DELETE (204) → GET del eliminado (404). Imprime método, URL, cuerpo enviado, estado y un extracto
del JSON. Solo usa la biblioteca estándar de Python. Termina con código 1 si algún estado no es el
esperado. El compromiso de prueba queda eliminado (borrado lógico).
"""
import datetime
import http.cookiejar
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

URL = os.environ.get('SGR_URL', 'http://127.0.0.1:8000').rstrip('/')
USUARIO = os.environ.get('SGR_USUARIO', 'admin_centro')
CLAVE = os.environ.get('SGR_CLAVE')
if not CLAVE:
    sys.exit('Falta SGR_CLAVE (contraseña de la cuenta de prueba).')

cookies = http.cookiejar.CookieJar()
navegador = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookies))


def csrf():
    return next((c.value for c in cookies if c.name == 'csrftoken'), '')


def pedir(metodo, ruta, cuerpo=None, tipo='application/json'):
    datos = None
    if cuerpo is not None:
        datos = json.dumps(cuerpo).encode() if tipo == 'application/json' else urllib.parse.urlencode(cuerpo).encode()
    solicitud = urllib.request.Request(URL + ruta, data=datos, method=metodo, headers={
        'Content-Type': tipo, 'Accept': 'application/json', 'X-CSRFToken': csrf(), 'Referer': URL + ruta,
    })
    try:
        with navegador.open(solicitud) as respuesta:
            return respuesta.status, respuesta.read().decode(), respuesta.geturl()
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode(), error.geturl()


# Ingreso con la sesión del sitio (mismo formulario que el navegador, con su token CSRF).
_, html, _ = pedir('GET', '/accounts/login/')
token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', html).group(1)
_, _, destino = pedir('POST', '/accounts/login/', {'csrfmiddlewaretoken': token, 'username': USUARIO, 'password': CLAVE},
                      tipo='application/x-www-form-urlencoded')
if '/accounts/login/' in destino:
    sys.exit(f'No se pudo iniciar sesión como {USUARIO}: «Usuario o contraseña incorrectos.»')

fallas = 0


def paso(numero, metodo, ruta, esperado, cuerpo=None):
    global fallas
    estado, texto, _ = pedir(metodo, ruta, cuerpo)
    ok = estado == esperado
    fallas += not ok
    print(f'{numero}. {metodo:<6} {ruta}')
    if cuerpo is not None:
        print(f'   cuerpo:  {json.dumps(cuerpo, ensure_ascii=False)}')
    print(f'   estado:  {estado} (esperado {esperado}) {"OK" if ok else "FALLA"}')
    print(f'   JSON:    {(texto[:180] + "…") if len(texto) > 180 else (texto or "(sin cuerpo)")}\n')
    try:
        return json.loads(texto) if texto else None
    except ValueError:
        return None


vence = (datetime.date.today() + datetime.timedelta(days=10)).isoformat()
lista = paso(1, 'GET', '/api/compromisos/', 200)
print(f'   ({len(lista or [])} compromisos visibles para {USUARIO})\n')
creado = paso(2, 'POST', '/api/compromisos/', 201, {'title': 'Reunión con junta de vecinos (API)', 'due_date': vence})
pk = (creado or {}).get('id')
paso(3, 'GET', f'/api/compromisos/{pk}/', 200)
paso(4, 'PATCH', f'/api/compromisos/{pk}/', 200, {'status': 'in_progress'})
paso(5, 'POST', '/api/compromisos/', 400, {'title': 'Ab', 'due_date': '2020-01-01'})
paso(6, 'DELETE', f'/api/compromisos/{pk}/', 204)
paso(7, 'GET', f'/api/compromisos/{pk}/', 404)
print('Todas las respuestas con el estado esperado.' if not fallas else f'{fallas} respuesta(s) con un estado distinto al esperado.')
sys.exit(1 if fallas else 0)
