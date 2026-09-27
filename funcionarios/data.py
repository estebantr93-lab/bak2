import os
import secrets
import string

from django.contrib.auth.models import User

from core.models import Position, Delegation

from .models import Employee
from .security import configurar_grupos_y_permisos

USUARIOS_DEMO = [
    'admin_sgr', 'admin_centro', 'admin_norte', 'funcionario_centro', 'funcionario_norte', 'verificador_leia',
]

# Contraseñas generadas en esta ejecución (solo para imprimirlas una vez al final del seed).
CLAVES_GENERADAS = {}


def _generar_clave():
    """Clave aleatoria que cumple la política: mayúscula, minúscula, número y símbolo."""
    alfabeto = string.ascii_letters + string.digits + '#$%&*+-_'
    while True:
        clave = ''.join(secrets.choice(alfabeto) for _ in range(14))
        if (any(c.islower() for c in clave) and any(c.isupper() for c in clave)
                and any(c.isdigit() for c in clave) and any(c in '#$%&*+-_' for c in clave)):
            return clave


def clave_demo(username):
    """Las contraseñas de demo NO se versionan: vienen del .env o se generan al azar.

    DEMO_PASSWORD_<USUARIO> tiene prioridad sobre DEMO_PASSWORD (común a todas las cuentas).
    """
    clave = os.getenv(f'DEMO_PASSWORD_{username.upper()}') or os.getenv('DEMO_PASSWORD')
    if not clave:
        clave = _generar_clave()
        CLAVES_GENERADAS[username] = clave
    return clave


def _fijar_clave_si_es_nuevo(user, creado):
    # Idempotente: solo se asigna contraseña al crear la cuenta; re-ejecutar el seed no la cambia.
    if creado:
        user.set_password(clave_demo(user.username))
        user.save()


def _crear_usuario_con_perfil(username, grupo, delegacion, cargo, nombre):
    user, creado = User.objects.get_or_create(
        username=username, defaults={'is_staff': True, 'email': f'{username}@demo.sgr.local'},
    )
    _fijar_clave_si_es_nuevo(user, creado)
    user.groups.add(grupo)
    Employee.objects.get_or_create(
        user=user, defaults={'delegation': delegacion, 'position': cargo, 'name': nombre},
    )
    return user


def build_funcionarios():
    administradores, grupo_funcionarios, verificadores = configurar_grupos_y_permisos()

    admin_user, creado = User.objects.get_or_create(
        username='admin_sgr', defaults={'is_staff': True, 'is_superuser': True, 'email': 'admin_sgr@demo.sgr.local'},
    )
    _fijar_clave_si_es_nuevo(admin_user, creado)

    centro = Delegation.objects.get(name='Delegación Centro')
    norte = Delegation.objects.get(name='Delegación Norte')
    cargo_atencion = Position.objects.get(name='Encargado de Atención Ciudadana')
    cargo_social = Position.objects.get(name='Encargado Social')
    cargo_coordinador = Position.objects.get(name='Coordinador de Delegación')

    # Un administrador por delegación: cada uno solo ve los datos de la suya.
    admin_centro_user = _crear_usuario_con_perfil(
        'admin_centro', administradores, centro, cargo_coordinador, 'María Soto (Admin Centro)',
    )
    admin_norte_user = _crear_usuario_con_perfil(
        'admin_norte', administradores, norte, cargo_coordinador, 'Jorge Díaz (Admin Norte)',
    )

    func_centro_user, creado = User.objects.get_or_create(
        username='funcionario_centro',
        defaults={'is_staff': True, 'email': 'funcionario_centro@demo.sgr.local'},
    )
    _fijar_clave_si_es_nuevo(func_centro_user, creado)
    func_centro_user.groups.add(grupo_funcionarios)
    Employee.objects.get_or_create(
        user=func_centro_user,
        defaults={'delegation': centro, 'position': cargo_atencion, 'name': 'Ana Pérez (Centro)'},
    )

    func_norte_user, creado = User.objects.get_or_create(
        username='funcionario_norte',
        defaults={'is_staff': True, 'email': 'funcionario_norte@demo.sgr.local'},
    )
    _fijar_clave_si_es_nuevo(func_norte_user, creado)
    func_norte_user.groups.add(grupo_funcionarios)
    Employee.objects.get_or_create(
        user=func_norte_user,
        defaults={'delegation': norte, 'position': cargo_social, 'name': 'Carlos Rojas (Norte)'},
    )

    verificador_user, creado = User.objects.get_or_create(
        username='verificador_leia',
        defaults={'is_staff': True, 'email': 'verificador_leia@demo.sgr.local'},
    )
    _fijar_clave_si_es_nuevo(verificador_user, creado)
    verificador_user.groups.add(verificadores)

    return {
        'admin_sgr': admin_user,
        'admin_centro': admin_centro_user,
        'admin_norte': admin_norte_user,
        'funcionario_centro': func_centro_user,
        'funcionario_norte': func_norte_user,
        'verificador_leia': verificador_user,
    }
