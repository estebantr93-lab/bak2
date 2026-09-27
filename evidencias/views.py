from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from actividades.models import Actividad
from core.admin_utils import filtrar_por_delegacion

from .forms import EvidenciaForm
from .models import Evidencia


def _actividad_visible(user, pk):
    """404 si la actividad es de otra delegación: el scoping va en el QuerySet."""
    return get_object_or_404(filtrar_por_delegacion(Actividad.objects.select_related('delegacion'), user), pk=pk)


@login_required
@permission_required('evidencias.view_evidencia', raise_exception=True)
def evidencias_actividad(request, pk):
    actividad = _actividad_visible(request.user, pk)
    form = EvidenciaForm()
    if request.method == 'POST':
        if not request.user.has_perm('evidencias.add_evidencia'):
            messages.error(request, 'No tiene permiso para adjuntar evidencias.')
            return redirect('evidencias_actividad', pk=actividad.pk)
        form = EvidenciaForm(request.POST, request.FILES)
        if form.is_valid():
            evidencia = form.save(commit=False)
            evidencia.actividad = actividad
            evidencia.save()
            messages.success(request, f'Evidencia {evidencia.codigo_unico} cargada correctamente.')
            return redirect('evidencias_actividad', pk=actividad.pk)
    evidencias = actividad.evidencias.activos().select_related('revisada_por')
    return render(request, 'evidencias/evidencias_actividad.html', {
        'actividad': actividad, 'evidencias': evidencias, 'form': form,
    })


@login_required
@permission_required('evidencias.delete_evidencia', raise_exception=True)
@require_POST
def eliminar_evidencia(request, pk):
    qs = filtrar_por_delegacion(Evidencia.objects.select_related('actividad'), request.user, 'actividad__delegacion')
    evidencia = get_object_or_404(qs, pk=pk)
    actividad_pk, codigo = evidencia.actividad_id, evidencia.codigo_unico
    evidencia.delete()  # borrado lógico: se marca deleted_at y el archivo se conserva
    messages.success(request, f'Evidencia {codigo} eliminada.')
    return redirect('evidencias_actividad', pk=actividad_pk)
