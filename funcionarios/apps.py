from django.apps import AppConfig


class FuncionariosConfig(AppConfig):
    name = 'funcionarios'

    def ready(self):
        from . import signals  # noqa: F401
