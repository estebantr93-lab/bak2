from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class Comentario(models.Model):
    autor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comentarios')
    texto = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        ordering = ['-fecha']
        verbose_name = 'Comentario'
        verbose_name_plural = 'Comentarios'

    def __str__(self):
        return f'{self.autor} - {self.fecha:%Y-%m-%d %H:%M}'


class Alerta(models.Model):
    destinatario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='alertas')
    texto = models.CharField(max_length=250)
    fecha = models.DateTimeField(auto_now_add=True)
    leida = models.BooleanField(default=False)

    class Meta:
        ordering = ['-fecha']
        verbose_name = 'Alerta'
        verbose_name_plural = 'Alertas'

    def __str__(self):
        return self.texto


class TrazaAuditoria(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='trazas')
    accion = models.CharField(max_length=100)
    entidad_tipo = models.CharField(max_length=100)
    entidad_id = models.PositiveIntegerField(null=True, blank=True)
    detalle = models.TextField(blank=True)
    fecha = models.DateTimeField(auto_now_add=True)
    ip = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ['-fecha']
        verbose_name = 'Traza de auditoría'
        verbose_name_plural = 'Trazas de auditoría'

    def __str__(self):
        return f'{self.accion} - {self.entidad_tipo}#{self.entidad_id}'
