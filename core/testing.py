"""Utilidades para los tests: el seed usa una clave propia de prueba, nunca la de la demo."""
import os
from io import StringIO
from unittest import mock

from django.core.management import call_command

# Solo para la base de datos temporal de los tests; la demo usa DEMO_PASSWORD del .env.
CLAVE_TEST = 'Prueba#Local-2026'


def sembrar_datos_demo(**opciones):
    entorno = {'DEMO_PASSWORD': CLAVE_TEST}
    # Se ignoran las claves por usuario que pudiera tener el .env local.
    limpio = {k: v for k, v in os.environ.items() if not k.startswith('DEMO_PASSWORD')}
    with mock.patch.dict(os.environ, {**limpio, **entorno}, clear=True):
        call_command('seed_data', stdout=StringIO(), **opciones)
