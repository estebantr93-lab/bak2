"""Roles de la API (Evaluación 3 · Programación Back End).

La API tiene su propia matriz de roles, independiente de los roles de la web:
- «API Administrador»: lectura y escritura (GET, POST, PUT, PATCH, DELETE).
- «API Operador»: solo lectura (GET, HEAD, OPTIONS).
- Cualquier otro usuario autenticado, aunque tenga un token válido: 403.
Sin token (o con un token inválido o vencido) la respuesta es 401, porque JWT es el primer autenticador.
"""
from rest_framework.permissions import SAFE_METHODS, BasePermission

GRUPO_API_ADMINISTRADOR = 'API Administrador'
GRUPO_API_OPERADOR = 'API Operador'


def rol_api(user):
    """'administrador', 'operador' o None (sin rol API). Un superusuario no tiene rol por serlo."""
    if not user or not user.is_authenticated:
        return None
    grupos = {grupo.name for grupo in user.groups.all()}
    if GRUPO_API_ADMINISTRADOR in grupos:
        return 'administrador'
    if GRUPO_API_OPERADOR in grupos:
        return 'operador'
    return None


class PermisoPorRolAPI(BasePermission):
    message = 'Su usuario no tiene un rol de la API que permita esta operación.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False  # DRF responde 401 (NotAuthenticated) porque hay un autenticador con cabecera
        rol = rol_api(request.user)
        if rol == 'administrador':
            return True
        return rol == 'operador' and request.method in SAFE_METHODS
