from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver

from .models import Evidencia


@receiver(post_delete, sender=Evidencia)
def borrar_archivo_al_eliminar(sender, instance, **kwargs):
    """Política de huérfanos: al eliminar la evidencia se elimina su archivo físico."""
    if instance.archivo:
        instance.archivo.delete(save=False)


@receiver(pre_save, sender=Evidencia)
def borrar_archivo_reemplazado(sender, instance, **kwargs):
    """Al reemplazar el archivo, el anterior se elimina para no dejarlo huérfano."""
    if not instance.pk:
        return
    anterior = Evidencia.objects.filter(pk=instance.pk).values_list('archivo', flat=True).first()
    if anterior and anterior != instance.archivo.name:
        instance.archivo.storage.delete(anterior)
