"""Borrado lógico (deleted_at) para las entidades de negocio.

- `objects` devuelve solo registros activos: es el que usan vistas, listados y exportaciones.
- `all_objects` (manager por defecto) ve todo. Django lo usa para validar campos únicos,
  así un valor ocupado por un registro eliminado no provoca un IntegrityError.
- `delete()` marca `deleted_at` en vez de borrar la fila; `hard_delete()` borra de verdad.
"""
from django.db import models
from django.utils import timezone


class SoftDeleteQuerySet(models.QuerySet):
    def activos(self):
        return self.filter(deleted_at__isnull=True)

    def eliminados(self):
        return self.filter(deleted_at__isnull=False)

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


class SoftDeleteModel(models.Model):
    deleted_at = models.DateTimeField('eliminado el', null=True, blank=True, editable=False, db_index=True)

    # El primer manager declarado es el manager por defecto.
    all_objects = models.Manager.from_queryset(SoftDeleteQuerySet)()
    objects = ActivosManager()

    # related_name de los hijos que se eliminan lógicamente junto con este registro.
    soft_delete_cascade = ()

    class Meta:
        abstract = True

    @property
    def eliminado(self):
        return self.deleted_at is not None

    def soft_delete(self, momento=None):
        if self.deleted_at is not None:
            return
        # Toda la cascada usa el mismo instante: así restore() sabe qué hijos cayeron con el padre.
        self.deleted_at = momento or timezone.now()
        self.save(update_fields=['deleted_at'])
        for relacion in self.soft_delete_cascade:
            for hijo in getattr(self, relacion).filter(deleted_at__isnull=True):
                hijo.soft_delete(self.deleted_at)

    def restore(self):
        """Recupera el registro y los hijos que se eliminaron junto con él (no los que ya estaban eliminados)."""
        momento = self.deleted_at
        self.deleted_at = None
        self.save(update_fields=['deleted_at'])
        if momento is None:
            return
        for relacion in self.soft_delete_cascade:
            for hijo in getattr(self, relacion).filter(deleted_at=momento):
                hijo.restore()

    def delete(self, using=None, keep_parents=False):
        self.soft_delete()
        return 1, {self._meta.label: 1}

    def hard_delete(self, using=None, keep_parents=False):
        return super().delete(using=using, keep_parents=keep_parents)


def es_soft_delete(model):
    return issubclass(model, SoftDeleteModel)
