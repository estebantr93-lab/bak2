"""Obtención del token JWT con el mismo límite de intentos que el login de la web (OWASP A07).

Sin esto, /api/token/ sería una segunda puerta para probar contraseñas sin bloqueo. Los intentos
fallidos quedan en la traza por la señal user_login_failed (funcionarios/accesos.py) y cuentan para el
bloqueo igual que los de la web. La respuesta de un usuario bloqueado es la misma que la de una clave
incorrecta: no revela si la clave era correcta.
"""
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

from funcionarios.accesos import LOGIN_BLOQUEADO, LOGIN_EXITOSO, esta_bloqueado, normalizar, registrar_acceso


class TokenConLimiteSerializer(TokenObtainPairSerializer):
    default_error_messages = {'no_active_account': 'Usuario o contraseña incorrectos.'}

    def validate(self, attrs):
        request = self.context.get('request')
        username = attrs.get(self.username_field)
        if username and esta_bloqueado(request, username):
            registrar_acceso(request, LOGIN_BLOQUEADO, normalizar(username), motivo='token JWT')
            raise AuthenticationFailed(self.error_messages['no_active_account'], 'no_active_account')
        datos = super().validate(attrs)
        registrar_acceso(request, LOGIN_EXITOSO, normalizar(username), user=self.user, motivo='token JWT')
        return datos


class ObtenerTokenView(TokenObtainPairView):
    serializer_class = TokenConLimiteSerializer
