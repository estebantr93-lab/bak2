from django.contrib.auth.models import User

from core.models import Cargo, Delegacion

from .models import Funcionario
from .security import configurar_grupos_y_permisos

CREDENCIALES_DEMO = {
    'admin_sgr': 'Admin#2026SGR',
    'funcionario_centro': 'Centro#2026SGR',
    'funcionario_norte': 'Norte#2026SGR',
    'verificador_leia': 'Verifica#2026SGR',
}


def build_funcionarios():
    administradores, grupo_funcionarios, verificadores = configurar_grupos_y_permisos()

    admin_user, creado = User.objects.get_or_create(
        username='admin_sgr', defaults={'is_staff': True, 'is_superuser': True, 'email': 'admin_sgr@demo.sgr.local'},
    )
    if creado:
        admin_user.set_password(CREDENCIALES_DEMO['admin_sgr'])
        admin_user.save()

    centro = Delegacion.objects.get(nombre='Delegación Centro')
    norte = Delegacion.objects.get(nombre='Delegación Norte')
    cargo_atencion = Cargo.objects.get(nombre='Encargado de Atención Ciudadana')
    cargo_social = Cargo.objects.get(nombre='Encargado Social')

    func_centro_user, creado = User.objects.get_or_create(
        username='funcionario_centro',
        defaults={'is_staff': True, 'email': 'funcionario_centro@demo.sgr.local'},
    )
    if creado:
        func_centro_user.set_password(CREDENCIALES_DEMO['funcionario_centro'])
        func_centro_user.save()
    func_centro_user.groups.add(grupo_funcionarios)
    Funcionario.objects.get_or_create(
        user=func_centro_user,
        defaults={'delegacion': centro, 'cargo': cargo_atencion, 'nombre': 'Ana Pérez (Centro)'},
    )

    func_norte_user, creado = User.objects.get_or_create(
        username='funcionario_norte',
        defaults={'is_staff': True, 'email': 'funcionario_norte@demo.sgr.local'},
    )
    if creado:
        func_norte_user.set_password(CREDENCIALES_DEMO['funcionario_norte'])
        func_norte_user.save()
    func_norte_user.groups.add(grupo_funcionarios)
    Funcionario.objects.get_or_create(
        user=func_norte_user,
        defaults={'delegacion': norte, 'cargo': cargo_social, 'nombre': 'Carlos Rojas (Norte)'},
    )

    verificador_user, creado = User.objects.get_or_create(
        username='verificador_leia',
        defaults={'is_staff': True, 'email': 'verificador_leia@demo.sgr.local'},
    )
    if creado:
        verificador_user.set_password(CREDENCIALES_DEMO['verificador_leia'])
        verificador_user.save()
    verificador_user.groups.add(verificadores)

    return {
        'admin_sgr': admin_user,
        'funcionario_centro': func_centro_user,
        'funcionario_norte': func_norte_user,
        'verificador_leia': verificador_user,
    }
