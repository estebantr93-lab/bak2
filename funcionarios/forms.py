from django import forms
from django.contrib.auth.forms import AuthenticationForm

from core.admin_utils import es_usuario_sin_restriccion, perfil_desactivado, tiene_acceso_al_sistema


class LoginForm(AuthenticationForm):
    error_messages = {
        **AuthenticationForm.error_messages,
        # Genérico: no revela cuál de las dos credenciales falló.
        'invalid_login': 'Usuario o contraseña incorrectos.',
        'sin_rol': 'Su cuenta no tiene un rol asignado. Contacte al administrador del sistema.',
        'desactivado': 'Su perfil de funcionario está desactivado. Contacte al administrador de su delegación.',
    }

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)  # rechaza cuentas inactivas
        # Se evalúa con la contraseña ya verificada, así que no revela qué usuarios existen.
        if not es_usuario_sin_restriccion(user) and perfil_desactivado(user):
            raise forms.ValidationError(self.error_messages['desactivado'], code='desactivado')
        if not tiene_acceso_al_sistema(user):
            raise forms.ValidationError(self.error_messages['sin_rol'], code='sin_rol')


class SolicitarCodigoForm(forms.Form):
    email = forms.EmailField(label='Correo electrónico', widget=forms.EmailInput(attrs={'autocomplete': 'email'}))


class ValidarCodigoForm(forms.Form):
    code = forms.RegexField(
        label='Código de 6 dígitos', regex=r'^\d{6}$', max_length=6,
        error_messages={'invalid': 'El código debe tener 6 dígitos.'},
        widget=forms.TextInput(attrs={'inputmode': 'numeric', 'autocomplete': 'one-time-code'}),
    )
