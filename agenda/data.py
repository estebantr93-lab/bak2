import datetime

from core.models import Delegacion
from funcionarios.models import Funcionario

from .models import Compromiso, SeguimientoCompromiso


def build_agenda():
    centro = Delegacion.objects.get(nombre='Delegación Centro')
    norte = Delegacion.objects.get(nombre='Delegación Norte')
    func_centro = Funcionario.objects.get(nombre='Ana Pérez (Centro)')
    func_norte = Funcionario.objects.get(nombre='Carlos Rojas (Norte)')

    compromisos_data = [
        ('Instalar señalética en plaza de armas', centro, func_centro, datetime.date(2026, 8, 1), 'pendiente'),
        ('Coordinar operativo de verano', centro, func_centro, datetime.date(2026, 10, 15), 'en_proceso'),
        ('Reparación de luminarias sector norte', norte, func_norte, datetime.date(2026, 7, 20), 'ingresado'),
        ('Catastro de organizaciones sociales', norte, func_norte, datetime.date(2026, 11, 1), 'realizado'),
    ]

    compromisos = {}
    for titulo, delegacion, responsable, fecha_venc, estado in compromisos_data:
        compromiso, _ = Compromiso.objects.get_or_create(
            titulo=titulo,
            defaults={
                'delegacion': delegacion, 'responsable': responsable,
                'fecha_vencimiento': fecha_venc, 'estado': estado,
            },
        )
        compromisos[titulo] = compromiso

    SeguimientoCompromiso.objects.get_or_create(
        compromiso=compromisos['Instalar señalética en plaza de armas'],
        responsable=func_centro, estado_nuevo='pendiente',
        defaults={'descripcion': 'Compromiso vencido: pendiente de coordinación con proveedor.'},
    )
    SeguimientoCompromiso.objects.get_or_create(
        compromiso=compromisos['Reparación de luminarias sector norte'],
        responsable=func_norte, estado_nuevo='ingresado',
        defaults={'descripcion': 'Compromiso vencido: a la espera de asignación de cuadrilla técnica.'},
    )

    return compromisos
