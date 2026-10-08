"""Grupos y usuarios de prueba de la API: tres usuarios normales (ninguno es superusuario).

| Usuario      | Grupo               | Puede                                  |
| ------------ | ------------------- | -------------------------------------- |
| api_admin    | API Administrador   | GET, POST, PUT, PATCH y DELETE         |
| api_operador | API Operador        | Solo GET                               |
| api_sin_rol  | (ninguno)           | Obtiene token, pero cada recurso da 403 |

Las contraseñas no se versionan: API_PASSWORD (o DEMO_PASSWORD) del .env, o se generan al azar y se
muestran una sola vez. Es idempotente: volver a ejecutarlo no cambia contraseñas ya asignadas.
"""
import os

from django.contrib.auth.models import Group, User

from funcionarios.data import _generar_clave

from .permisos import GRUPO_API_ADMINISTRADOR, GRUPO_API_OPERADOR

USUARIOS_API = [
    ('api_admin', GRUPO_API_ADMINISTRADOR, 'Administrador API: lectura y escritura'),
    ('api_operador', GRUPO_API_OPERADOR, 'Operador API: solo lectura'),
    ('api_sin_rol', None, 'Usuario autenticado sin rol API: 403 en los recursos'),
]


def crear_usuarios_api():
    """Devuelve {usuario: clave generada} solo para las cuentas nuevas sin clave en el .env."""
    generadas = {}
    for username, grupo, _ in USUARIOS_API:
        user, creado = User.objects.get_or_create(username=username, defaults={'email': f'{username}@demo.sgr.local'})
        if creado:
            clave = os.getenv('API_PASSWORD') or os.getenv('DEMO_PASSWORD')
            if not clave:
                clave = generadas[username] = _generar_clave()
            user.set_password(clave)
            user.save()
        if grupo:
            user.groups.add(Group.objects.get_or_create(name=grupo)[0])
    return generadas
