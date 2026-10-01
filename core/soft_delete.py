"""QuerySet y managers del borrado lógico (deleted_at). El modelo base está en core/models.py (BaseModel).

- `objects` devuelve solo registros activos: es el que usan vistas, listados y exportaciones.
- `all_objects` (manager por defecto) ve todo. Django lo usa para validar campos únicos,
  así un valor ocupado por un registro eliminado no provoca un IntegrityError.
- `delete()` marca `deleted_at` en vez de borrar la fila; `hard_delete()` borra de verdad.
"""
from django.db import models


class SoftDeleteQuerySet(models.QuerySet):
    def delete(self):
        # Uno a uno para que cada objeto propague el borrado lógico a sus hijos.
        total = 0
        for obj in self.filter(deleted_at__isnull=True):
            obj.soft_delete()
            total += 1
        return total, {self.model._meta.label: total}

    def hard_delete(self):
        return super().delete()


class ActivosManager(models.Manager.from_queryset(SoftDeleteQuerySet)):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)
