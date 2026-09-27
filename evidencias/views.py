from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from actividades.models import Activity
from core.admin_utils import filtrar_por_delegacion

from .forms import EvidenciaForm
from .models import Evidence


def _actividad_visible(user, pk):
    """404 si la actividad es de otra delegación: el scoping va en el QuerySet."""
    return get_object_or_404(filtrar_por_delegacion(Activity.objects.select_related('delegation'), user), pk=pk)


@login_required
@permission_required('evidencias.view_evidence', raise_exception=True)
def evidencias_actividad(request, pk):
    actividad = _actividad_visible(request.user, pk)
    form = EvidenciaForm()
    if request.method == 'POST':
        if not request.user.has_perm('evidencias.add_evidence'):
            messages.error(request, 'No tiene permiso para adjuntar evidencias.')
            return redirect('evidencias_actividad', pk=actividad.pk)
        form = EvidenciaForm(request.POST, request.FILES)
        if form.is_valid():
            evidencia = form.save(commit=False)
            evidencia.activity = actividad
            evidencia.save()
            messages.success(request, f'Evidencia {evidencia.unique_code} cargada correctamente.')
            return redirect('evidencias_actividad', pk=actividad.pk)
    evidencias = actividad.evidence_items.activos().select_related('reviewed_by')
    return render(request, 'evidencias/evidencias_actividad.html', {
        'activity': actividad, 'evidence_items': evidencias, 'form': form,
    })


@login_required
@permission_required('evidencias.delete_evidence', raise_exception=True)
@require_POST
def eliminar_evidencia(request, pk):
    qs = filtrar_por_delegacion(Evidence.objects.select_related('activity'), request.user, 'activity__delegation')
    evidencia = get_object_or_404(qs, pk=pk)
    actividad_pk, codigo = evidencia.activity_id, evidencia.unique_code
    evidencia.delete()  # borrado lógico: se marca deleted_at y el archivo se conserva
    messages.success(request, f'Evidencia {codigo} eliminada.')
    return redirect('evidencias_actividad', pk=actividad_pk)
