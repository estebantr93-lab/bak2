from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

from actividades.models import Actividad

from .models import Alerta, Comentario, TrazaAuditoria


def build_colaboracion():
    verificador = User.objects.get(username='verificador_leia')
    func_centro_user = User.objects.get(username='funcionario_centro')

    actividad = Actividad.objects.get(numero='ACT-2026-003')
    ct_actividad = ContentType.objects.get_for_model(Actividad)

    Comentario.objects.get_or_create(
        autor=verificador, content_type=ct_actividad, object_id=actividad.pk,
        defaults={'texto': 'Se solicita adjuntar evidencia fotográfica adicional para reevaluar el rechazo.'},
    )

    Alerta.objects.get_or_create(
        destinatario=func_centro_user,
        texto='El compromiso "Instalar señalética en plaza de armas" se encuentra vencido.',
        defaults={'leida': False},
    )

    TrazaAuditoria.objects.get_or_create(
        usuario=verificador, accion='rechazo_evidencia', entidad_tipo='Evidencia', entidad_id=None,
        defaults={'detalle': 'Rechazo de evidencia EVID-CEN-003 por documentación insuficiente.'},
    )
