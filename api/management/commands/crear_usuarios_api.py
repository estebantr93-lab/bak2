from django.core.management.base import BaseCommand

from api.usuarios import USUARIOS_API, crear_usuarios_api


class Command(BaseCommand):
    help = 'Crea los grupos «API Administrador» y «API Operador» y los usuarios api_admin, api_operador y api_sin_rol.'

    def handle(self, *args, **options):
        generadas = crear_usuarios_api()
        self.stdout.write(self.style.MIGRATE_HEADING('Usuarios de la API:'))
        for username, _, descripcion in USUARIOS_API:
            self.stdout.write(f'  - {username} -> {descripcion}')
        if generadas:
            self.stdout.write(self.style.WARNING('Contraseñas generadas (se muestran una sola vez):'))
            for username, clave in generadas.items():
                self.stdout.write(f'  {username}: {clave}')
