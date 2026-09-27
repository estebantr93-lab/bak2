import re

from django.core.exceptions import ValidationError


class ComplexPasswordValidator:
    """Exige mayúscula, minúscula, número y carácter especial.

    Se registra en AUTH_PASSWORD_VALIDATORS, así Django lo aplica en todos los formularios
    que cambian contraseñas (recuperación, Admin, changepassword). El largo mínimo lo
    controla MinimumLengthValidator (10).
    """

    REGLAS = [
        (r'[A-ZÁÉÍÓÚÑ]', 'una letra mayúscula'),
        (r'[a-záéíóúñ]', 'una letra minúscula'),
        (r'\d', 'un número'),
        (r'[^\w\s]|_', 'un carácter especial (por ejemplo # $ % & * -)'),
    ]

    def validate(self, password, user=None):
        faltan = [texto for patron, texto in self.REGLAS if not re.search(patron, password)]
        if faltan:
            raise ValidationError(
                'La contraseña debe contener al menos ' + ', '.join(faltan) + '.',
                code='password_too_simple',
            )

    def get_help_text(self):
        return 'Debe contener mayúscula, minúscula, número y carácter especial.'
