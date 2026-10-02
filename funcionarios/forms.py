from django import forms
from django.contrib.auth.forms import AuthenticationForm

from core.admin_utils import ROLES_ETIQUETAS, es_usuario_sin_restriccion, get_rol, perfil_desactivado, tiene_acceso_al_sistema

from .accesos import LOGIN_BLOQUEADO, LOGIN_RECHAZADO, esta_bloqueado, normalizar, registrar_acceso


class LoginForm(AuthenticationForm):
    """Ingreso con un único mensaje de error para todo rechazo (clave incorrecta, cuenta inactiva, sin rol,
    sin perfil, perfil desactivado o bloqueo por intentos). Así la respuesta no revela si la cuenta
    existe, si la clave era correcta ni en qué estado está. El motivo real queda en la traza de
    auditoría (`login_rechazado`) y lo explica `python manage.py diagnosticar_acceso <usuario>`."""

    error_messages = {
        **AuthenticationForm.error_messages,
        'invalid_login': 'Usuario o contraseña incorrectos.',
        'inactive': 'Usuario o contraseña incorrectos.',
    }

    def _rechazar(self, motivo, username):
        registrar_acceso(self.request, LOGIN_RECHAZADO, normalizar(username), motivo=motivo)
        raise forms.ValidationError(self.error_messages['invalid_login'], code='invalid_login',
                                    params={'username': self.username_field.verbose_name})

    def clean(self):
        # OWASP A07: se revisa antes de comprobar la contraseña, así el bloqueo responde lo mismo
        # con la clave correcta o incorrecta y no sirve para adivinarla.
        username = self.cleaned_data.get('username')
        if username and esta_bloqueado(self.request, username):
            registrar_acceso(self.request, LOGIN_BLOQUEADO, normalizar(username))
            raise forms.ValidationError(self.error_messages['invalid_login'], code='invalid_login',
                                        params={'username': self.username_field.verbose_name})
        return super().clean()

    def confirm_login_allowed(self, user):
        # La clave ya es correcta: cualquier rechazo desde aquí responde igual que una clave incorrecta.
        if not user.is_active:
            self._rechazar('cuenta inactiva', user.get_username())
        if not es_usuario_sin_restriccion(user) and perfil_desactivado(user):
            self._rechazar('perfil de funcionario desactivado', user.get_username())
        if not tiene_acceso_al_sistema(user):
            rol = get_rol(user)
            if rol is None:
                self._rechazar('sin rol asignado', user.get_username())
            self._rechazar(f'rol {ROLES_ETIQUETAS[rol].lower()} sin perfil de funcionario con delegación', user.get_username())


class SolicitarCodigoForm(forms.Form):
    email = forms.EmailField(label='Correo electrónico', widget=forms.EmailInput(attrs={'autocomplete': 'email'}))


class ValidarCodigoForm(forms.Form):
    code = forms.RegexField(
        label='Código de 6 dígitos', regex=r'^\d{6}$', max_length=6,
        error_messages={'invalid': 'El código debe tener 6 dígitos.'},
        widget=forms.TextInput(attrs={'inputmode': 'numeric', 'autocomplete': 'one-time-code'}),
    )
