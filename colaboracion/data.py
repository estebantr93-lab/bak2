from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

from actividades.models import Activity

from .models import Alert, Comment, AuditLog


def build_colaboracion():
    verificador = User.objects.get(username='verificador_leia')
    func_centro_user = User.objects.get(username='funcionario_centro')

    actividad = Activity.objects.get(number='ACT-2026-003')
    ct_actividad = ContentType.objects.get_for_model(Activity)

    Comment.objects.get_or_create(
        author=verificador, content_type=ct_actividad, object_id=actividad.pk,
        defaults={'text': 'Se solicita adjuntar evidencia fotográfica adicional para reevaluar el rechazo.'},
    )

    Alert.objects.get_or_create(
        recipient=func_centro_user,
        text='El compromiso "Instalar señalética en plaza de armas" se encuentra vencido.',
        defaults={'is_read': False},
    )

    AuditLog.objects.get_or_create(
        user=verificador, action='rechazo_evidencia', entity_type='Evidence', entity_id=None,
        defaults={'detail': 'Rechazo de evidencia EVID-CEN-003 por documentación insuficiente.'},
    )
