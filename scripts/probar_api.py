"""Matriz de pruebas de la API REST con JWT contra el servidor local (las mismas filas de Apidog).

Con el servidor levantado (python manage.py runserver) y los datos cargados (seed_data), desde la raíz:

    SGR_CLAVE_API='<clave de los usuarios api_*>' python scripts/probar_api.py

Opcional: SGR_URL (por defecto http://127.0.0.1:8000) y --markdown para imprimir la matriz como tabla.
Recorre: token y renovación, 401 sin token, operador (200/403), usuario sin rol (403), CRUD completo de
los cuatro recursos principales (201/200/200/204 y 404 después del borrado lógico), lista y detalle de
los dos operacionales, errores (400/400/404) y paginación (dos páginas distintas). Imprime método, URL,
identidad, estado esperado y observado. Nunca imprime tokens ni contraseñas. Termina con código 1 si
algún estado no es el esperado. Los registros de prueba quedan eliminados (borrado lógico).
"""
import datetime
import io
import json
import os
import sys
import urllib.error
import urllib.request
import uuid

URL = os.environ.get('SGR_URL', 'http://127.0.0.1:8000').rstrip('/')
CLAVE = os.environ.get('SGR_CLAVE_API')
if not CLAVE:
    sys.exit('Falta SGR_CLAVE_API (contraseña de api_admin, api_operador y api_sin_rol).')
MARKDOWN = '--markdown' in sys.argv

filas = []
fallas = 0


def pedir(metodo, ruta, cuerpo=None, token=None, multipart=None):
    cabeceras = {'Accept': 'application/json'}
    datos = None
    if token:
        cabeceras['Authorization'] = f'Bearer {token}'
    if multipart is not None:
        limite = uuid.uuid4().hex
        partes = []
        for nombre, valor in multipart.items():
            if isinstance(valor, tuple):  # (nombre de archivo, bytes, tipo)
                partes.append(f'--{limite}\r\nContent-Disposition: form-data; name="{nombre}"; filename="{valor[0]}"\r\n'
                              f'Content-Type: {valor[2]}\r\n\r\n'.encode() + valor[1] + b'\r\n')
            else:
                partes.append(f'--{limite}\r\nContent-Disposition: form-data; name="{nombre}"\r\n\r\n{valor}\r\n'.encode())
        datos = b''.join(partes) + f'--{limite}--\r\n'.encode()
        cabeceras['Content-Type'] = f'multipart/form-data; boundary={limite}'
    elif cuerpo is not None:
        datos = json.dumps(cuerpo).encode()
        cabeceras['Content-Type'] = 'application/json'
    solicitud = urllib.request.Request(URL + ruta, data=datos, method=metodo, headers=cabeceras)
    try:
        with urllib.request.urlopen(solicitud) as respuesta:
            texto = respuesta.read().decode()
            return respuesta.status, json.loads(texto) if texto else None
    except urllib.error.HTTPError as error:
        texto = error.read().decode()
        try:
            return error.code, json.loads(texto) if texto else None
        except ValueError:
            return error.code, texto[:120]


def probar(caso, metodo, ruta, identidad, esperado, **opciones):
    global fallas
    estado, cuerpo = pedir(metodo, ruta, **opciones)
    ok = estado == esperado
    fallas += not ok
    resumen = json.dumps(cuerpo, ensure_ascii=False)[:110] if cuerpo is not None else '(sin cuerpo)'
    for secreto in ('access', 'refresh'):
        if isinstance(cuerpo, dict) and secreto in cuerpo:
            resumen = resumen.replace(cuerpo[secreto], '***')
    filas.append((caso, metodo, ruta, identidad, esperado, estado, 'OK' if ok else 'FALLA', resumen))
    if not MARKDOWN:
        print(f"{'OK   ' if ok else 'FALLA'} {caso:<38} {metodo:<6} {ruta:<38} {identidad:<13} esperado {esperado} · obtenido {estado}")
    return estado, cuerpo


def token(usuario):
    estado, cuerpo = pedir('POST', '/api/token/', {'username': usuario, 'password': CLAVE})
    if estado != 200:
        sys.exit(f'No se pudo obtener el token de {usuario} ({estado}). ¿Cargó los datos con seed_data y la clave es la correcta?')
    return cuerpo


def png():
    from PIL import Image  # pillow ya está en requirements.txt

    buffer = io.BytesIO()
    Image.new('RGB', (12, 12), (0, 110, 70)).save(buffer, format='PNG')
    return buffer.getvalue()


# --- JWT ------------------------------------------------------------------------------------------
_, tokens = probar('JWT: obtener token', 'POST', '/api/token/', 'api_admin', 200,
                   cuerpo={'username': 'api_admin', 'password': CLAVE})
probar('JWT: renovar access', 'POST', '/api/token/refresh/', 'api_admin', 200, cuerpo={'refresh': tokens['refresh']})
admin = tokens['access']
operador = token('api_operador')['access']
sin_rol = token('api_sin_rol')['access']

# --- Sin autenticación, operador y sin rol --------------------------------------------------------
recursos = ['actividades', 'atenciones', 'compromisos', 'evidencias', 'validaciones', 'seguimientos']
for recurso in recursos:
    probar('Sin token', 'GET', f'/api/{recurso}/', 'sin token', 401)
for recurso in recursos:
    probar('Operador: lectura', 'GET', f'/api/{recurso}/', 'api_operador', 200, token=operador)
probar('Operador: escritura denegada', 'POST', '/api/compromisos/', 'api_operador', 403, token=operador,
       cuerpo={'title': 'Intento del operador'})
for recurso in recursos:
    probar('Sin rol API', 'GET', f'/api/{recurso}/', 'api_sin_rol', 403, token=sin_rol)

# --- Datos de referencia (ids reales de la base cargada) ----------------------------------------
hoy = datetime.date.today()
referencia = None
pagina = 1
while referencia is None:
    _, lista = pedir('GET', f'/api/actividades/?page={pagina}&page_size=100', token=admin)
    referencia = next((a for a in lista['results'] if a['period_is_closed'] is False), None)
    if referencia is None and not lista['next']:
        sys.exit('No hay actividades en un período abierto para tomar como referencia.')
    pagina += 1
_, atenciones = pedir('GET', '/api/atenciones/?page_size=1', token=admin)
_, actividad_social = pedir('GET', f"/api/actividades/{atenciones['results'][0]['activity']}/", token=admin)
_, compromisos = pedir('GET', '/api/compromisos/?page_size=1', token=admin)
sufijo = uuid.uuid4().hex[:6].upper()


def crud(nombre, recurso, datos, cambio, multipart=False):
    opciones = {'multipart': datos} if multipart else {'cuerpo': datos}
    estado, creado = probar(f'CRUD {nombre}: crear', 'POST', f'/api/{recurso}/', 'api_admin', 201, token=admin, **opciones)
    if estado != 201:
        return None
    ruta = f"/api/{recurso}/{creado['id']}/"
    probar(f'CRUD {nombre}: detalle', 'GET', ruta, 'api_admin', 200, token=admin)
    probar(f'CRUD {nombre}: modificar (PATCH)', 'PATCH', ruta, 'api_admin', 200, token=admin, cuerpo=cambio)
    probar(f'CRUD {nombre}: eliminar', 'DELETE', ruta, 'api_admin', 204, token=admin)
    probar(f'CRUD {nombre}: ya no figura', 'GET', ruta, 'api_admin', 404, token=admin)
    return creado


actividad = {'employee': referencia['employee'], 'period': referencia['period'], 'activity_type': referencia['activity_type'],
             'date': str(hoy), 'description': 'Atención registrada desde la matriz de pruebas'}
crud('actividad', 'actividades', {**actividad, 'number': f'API-{sufijo}'}, {'description': 'Descripción corregida'})

# Atención social: sobre una actividad nueva del tipo social, para tener libre la gestión n.º 1.
_, social = pedir('POST', '/api/actividades/', {**actividad, 'number': f'API-SOC-{sufijo}',
                                                'activity_type': actividad_social['activity_type']}, token=admin)
crud('atención social', 'atenciones', {'activity': social['id'], 'step_number': 1, 'date': str(hoy),
                                       'description': 'Primera gestión de prueba'}, {'result': 'Derivado a beneficio'})

compromiso = {'title': f'Compromiso de prueba {sufijo}', 'delegation': compromisos['results'][0]['delegation'],
              'due_date': str(hoy + datetime.timedelta(days=15))}
crud('compromiso', 'compromisos', compromiso, {'status': 'in_progress'})
crud('evidencia', 'evidencias', {'activity': social['id'], 'description': 'Respaldo fotográfico de prueba',
                                 'file': ('respaldo.png', png(), 'image/png')},
     {'description': 'Respaldo corregido'}, multipart=True)
pedir('DELETE', f"/api/actividades/{social['id']}/", token=admin)  # limpieza (borrado lógico)

for recurso in ('validaciones', 'seguimientos'):
    _, lista = pedir('GET', f'/api/{recurso}/', token=operador)
    probar(f'Operacional {recurso}: detalle', 'GET', f"/api/{recurso}/{lista['results'][0]['id']}/", 'api_operador', 200,
           token=operador)

# --- Errores --------------------------------------------------------------------------------------
probar('Error: validación de campo (título corto)', 'POST', '/api/compromisos/', 'api_admin', 400, token=admin,
       cuerpo={**compromiso, 'title': 'abc'})
# Regla de negocio: el responsable debe ser de la misma delegación del compromiso.
_, con_responsable = pedir('GET', '/api/compromisos/?page_size=100', token=admin)
uno = next(c for c in con_responsable['results'] if c['responsible'])
otro = next(c for c in con_responsable['results'] if c['delegation'] != uno['delegation'])
probar('Error: regla de negocio (responsable ajeno)', 'POST', '/api/compromisos/', 'api_admin', 400, token=admin,
       cuerpo={**compromiso, 'delegation': otro['delegation'], 'responsible': uno['responsible']})
probar('Error: id inexistente', 'GET', '/api/actividades/999999/', 'api_admin', 404, token=admin)

# --- Paginación -----------------------------------------------------------------------------------
_, p1 = probar('Paginación: página 1', 'GET', '/api/actividades/', 'api_operador', 200, token=operador)
_, p2 = probar('Paginación: página 2', 'GET', '/api/actividades/?page=2', 'api_operador', 200, token=operador)
distintas = {a['id'] for a in p1['results']}.isdisjoint({a['id'] for a in p2['results']})
fallas += not distintas

if MARKDOWN:
    print('| Caso | Método | URL | Identidad | Esperado | Obtenido | Resultado | Respuesta (extracto) |')
    print('| --- | --- | --- | --- | --- | --- | --- | --- |')
    for fila in filas:
        print('| ' + ' | '.join(str(c).replace('|', '\\|') for c in fila) + ' |')
print()
print(f"Total de actividades: {p1['count']} · por página: {len(p1['results'])} · páginas distintas: {'sí' if distintas else 'NO'}")
print(f"{sum(fila[6] == 'OK' for fila in filas)}/{len(filas)} casos con el estado esperado.")
sys.exit(1 if fallas else 0)
