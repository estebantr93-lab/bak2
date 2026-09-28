import datetime

from core.models import Delegation
from funcionarios.models import Employee

from .models import Commitment, CommitmentFollowUp


def build_agenda():
    centro = Delegation.objects.get(name='Delegación Centro')
    norte = Delegation.objects.get(name='Delegación Norte')
    func_centro = Employee.objects.get(name='Ana Pérez (Centro)')
    func_norte = Employee.objects.get(name='Carlos Rojas (Norte)')

    compromisos_data = [
        ('Instalar señalética en plaza de armas', centro, func_centro, datetime.date(2026, 8, 1), 'pending'),
        ('Coordinar operativo de verano', centro, func_centro, datetime.date(2026, 10, 15), 'in_progress'),
        ('Reparación de luminarias sector norte', norte, func_norte, datetime.date(2026, 7, 20), 'registered'),
        ('Catastro de organizaciones sociales', norte, func_norte, datetime.date(2026, 11, 1), 'done'),
    ]

    compromisos = {}
    for titulo, delegacion, responsable, fecha_venc, estado in compromisos_data:
        compromiso, _ = Commitment.all_objects.get_or_create(
            title=titulo,
            defaults={
                'delegation': delegacion, 'responsible': responsable,
                'due_date': fecha_venc, 'status': estado,
                # Regla del modelo: un compromiso realizado lleva observaciones.
                'notes': 'Catastro entregado a la dirección.' if estado == 'done' else '',
            },
        )
        compromisos[titulo] = compromiso

    CommitmentFollowUp.all_objects.get_or_create(
        commitment=compromisos['Instalar señalética en plaza de armas'],
        responsible=func_centro, new_status='pending',
        defaults={'description': 'Compromiso vencido: pendiente de coordinación con proveedor.'},
    )
    CommitmentFollowUp.all_objects.get_or_create(
        commitment=compromisos['Reparación de luminarias sector norte'],
        responsible=func_norte, new_status='registered',
        defaults={'description': 'Compromiso vencido: a la espera de asignación de cuadrilla técnica.'},
    )

    return compromisos
