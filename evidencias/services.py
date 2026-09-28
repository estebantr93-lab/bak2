"""Revisión de evidencias y estado de la actividad: una sola implementación para todas las vías.

La usan el formulario web del verificador, la acción masiva del Admin, el formulario de cambio de
Evidence en el Admin y el alta de Validation en el Admin. Así ninguna vía puede aprobar "a medias"
(sin revisor, sin Validation o sin actualizar la actividad).
"""
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count, Q

from colaboracion.models import AuditLog
from core.admin_utils import motivo_no_modificable

ESTADOS_REVISION = ('approved', 'rejected')


def estado_segun_evidencias(aprobadas, rechazadas):
    """Regla de negocio: rechazada si alguna evidencia fue rechazada; aprobada si tiene al menos
    una aprobada (y ninguna rechazada); en otro caso, pendiente."""
    if rechazadas:
        return 'rejected'
    if aprobadas:
        return 'approved'
    return 'pending'


def sincronizar_estado_actividades(actividades):
    """Recalcula validation_status de un queryset de actividades con dos UPDATE por estado
    (se usa tras cargas masivas, donde bulk_create no dispara señales)."""
    activas = Q(evidence_items__deleted_at__isnull=True)
    conteos = actividades.annotate(
        aprobadas=Count('evidence_items', filter=activas & Q(evidence_items__status='approved')),
        rechazadas=Count('evidence_items', filter=activas & Q(evidence_items__status='rejected')),
    ).values_list('pk', 'aprobadas', 'rechazadas')
    por_estado = {}
    for pk, aprobadas, rechazadas in conteos:
        por_estado.setdefault(estado_segun_evidencias(aprobadas, rechazadas), []).append(pk)
    modelo = actividades.model
    for estado, pks in por_estado.items():
        modelo.all_objects.filter(pk__in=pks).exclude(validation_status=estado).update(validation_status=estado)


def sincronizar_estado_actividad(actividad):
    sincronizar_estado_actividades(type(actividad).all_objects.filter(pk=actividad.pk))


@transaction.atomic
def registrar_revision(evidencia, usuario, estado, comentario='', validacion=None, ip=None):
    """Aprueba o rechaza una evidencia: estado, revisor, Validation, traza de auditoría y, vía la
    señal post_save de Evidence, el estado de la actividad."""
    from .models import Validation

    if estado not in ESTADOS_REVISION:
        raise ValueError(f'Estado de revisión inválido: {estado}')
    motivo = motivo_no_modificable(evidencia)
    if motivo:
        raise PermissionDenied(motivo)
    evidencia.status = estado
    evidencia.reviewed_by = usuario
    if comentario:
        evidencia.result = comentario
    evidencia.save()
    validacion = validacion or Validation(evidence=evidencia)
    validacion.evidence, validacion.reviewer, validacion.status = evidencia, usuario, estado
    validacion.comment = comentario or validacion.comment
    validacion.save()
    AuditLog.objects.create(
        user=usuario, action=f'evidencia_{estado}', entity_type='Evidence', entity_id=evidencia.pk,
        detail=comentario, ip=ip,
    )
    return validacion
