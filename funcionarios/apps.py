from django.apps import AppConfig


class FuncionariosConfig(AppConfig):
    name = 'funcionarios'

    def ready(self):
        from . import accesos, signals  # noqa: F401  (registran sus receptores de señales)
