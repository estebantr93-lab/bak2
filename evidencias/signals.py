from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver

from .models import Evidence


@receiver(post_delete, sender=Evidence)
def borrar_archivo_al_eliminar(sender, instance, **kwargs):
    """Política de huérfanos: al borrar físicamente (hard_delete) se borra también el archivo.

    El borrado lógico (delete()) no dispara esta señal: el archivo se conserva por si se restaura.
    """
    if instance.file:
        instance.file.delete(save=False)


@receiver(pre_save, sender=Evidence)
def borrar_archivo_reemplazado(sender, instance, **kwargs):
    """Al reemplazar el archivo, el anterior se elimina para no dejarlo huérfano."""
    if not instance.pk:
        return
    anterior = Evidence.all_objects.filter(pk=instance.pk).values_list('file', flat=True).first()
    if anterior and anterior != instance.file.name:
        instance.file.storage.delete(anterior)
