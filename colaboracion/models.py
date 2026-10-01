from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class Comment(models.Model):
    author = models.ForeignKey(User, verbose_name='autor', on_delete=models.CASCADE, related_name='comments')
    text = models.TextField('texto')
    date = models.DateTimeField('fecha', auto_now_add=True)
    content_type = models.ForeignKey(ContentType, verbose_name='tipo de contenido', on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField('id del objeto')
    content_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        db_table = 'comment'
        ordering = ['-date']
        verbose_name = 'Comentario'
        verbose_name_plural = 'Comentarios'

    def __str__(self):
        return f'{self.author} - {self.date:%Y-%m-%d %H:%M}'


class Alert(models.Model):
    recipient = models.ForeignKey(User, verbose_name='destinatario', on_delete=models.CASCADE, related_name='alerts')
    text = models.CharField('texto', max_length=250)
    date = models.DateTimeField('fecha', auto_now_add=True)
    is_read = models.BooleanField('leída', default=False)

    class Meta:
        db_table = 'alert'
        ordering = ['-date']
        verbose_name = 'Alerta'
        verbose_name_plural = 'Alertas'

    def __str__(self):
        return self.text


class AuditLog(models.Model):
    user = models.ForeignKey(User, verbose_name='usuario', on_delete=models.SET_NULL, null=True, related_name='audit_logs')
    action = models.CharField('acción', max_length=100)
    entity_type = models.CharField('tipo de entidad', max_length=100)
    entity_id = models.PositiveIntegerField('id de entidad', null=True, blank=True)
    detail = models.TextField('detalle', blank=True)
    # Campos modificados: {campo: [valor anterior, valor nuevo]} (RNF-008 y CA-09 de la guía).
    changes = models.JSONField('cambios', default=dict, blank=True)
    date = models.DateTimeField('fecha', auto_now_add=True)
    ip = models.GenericIPAddressField('IP', null=True, blank=True)

    class Meta:
        db_table = 'audit_log'
        ordering = ['-date']
        verbose_name = 'Traza de auditoría'
        verbose_name_plural = 'Trazas de auditoría'

    def __str__(self):
        return f'{self.action} - {self.entity_type}#{self.entity_id}'
