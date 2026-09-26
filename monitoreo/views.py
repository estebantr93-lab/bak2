from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from core.admin_utils import ROLES_ETIQUETAS, get_rol, get_usuario_delegacion
from core.models import Periodo

from .services import construir_dashboard, periodo_por_defecto


@login_required
def dashboard(request):
    periodos = Periodo.objects.all()
    periodo = None
    periodo_id = request.GET.get('periodo')
    if periodo_id and periodo_id.isdigit():
        periodo = periodos.filter(pk=periodo_id).first()
    periodo = periodo or periodo_por_defecto()

    rol = get_rol(request.user)
    contexto = {
        'rol': rol,
        'rol_etiqueta': ROLES_ETIQUETAS.get(rol, 'Sin rol asignado'),
        'delegacion_usuario': get_usuario_delegacion(request.user),
        'periodos': periodos,
        'periodo': periodo,
        **construir_dashboard(request.user, periodo),
    }
    return render(request, 'monitoreo/dashboard.html', contexto)
