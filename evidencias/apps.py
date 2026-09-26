from django.apps import AppConfig


class EvidenciasConfig(AppConfig):
    name = 'evidencias'

    def ready(self):
        from . import signals  # noqa: F401
