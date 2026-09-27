from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver

from .models import Evidencia


@receiver(post_delete, sender=Evidencia)
def borrar_archivo_al_eliminar(sender, instance, **kwargs):
    """Política de huérfanos: al borrar físicamente (hard_delete) se borra también el archivo.

    El borrado lógico (delete()) no dispara esta señal: el archivo se conserva por si se restaura.
    """
    if instance.archivo:
        instance.archivo.delete(save=False)


@receiver(pre_save, sender=Evidencia)
def borrar_archivo_reemplazado(sender, instance, **kwargs):
    """Al reemplazar el archivo, el anterior se elimina para no dejarlo huérfano."""
    if not instance.pk:
        return
    anterior = Evidencia.all_objects.filter(pk=instance.pk).values_list('archivo', flat=True).first()
    if anterior and anterior != instance.archivo.name:
        instance.archivo.storage.delete(anterior)
