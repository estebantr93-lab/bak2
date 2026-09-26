from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.paginator import Paginator
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from core.admin_utils import filtrar_por_delegacion

from .forms import ActividadWebForm
from .models import Actividad

# Preferencia de interfaz guardada en la sesión (no es un permiso ni un dato sensible).
SESION_PAGE_SIZE = 'actividades_page_size'
PAGE_SIZES = [10, 15, 30]
PAGE_SIZE_POR_DEFECTO = 15


def page_size_de_sesion(request):
    valor = request.GET.get('page_size')
    if valor and valor.isdigit() and int(valor) in PAGE_SIZES:
        request.session[SESION_PAGE_SIZE] = int(valor)
    return request.session.get(SESION_PAGE_SIZE, PAGE_SIZE_POR_DEFECTO)


class ActividadScopeMixin(LoginRequiredMixin, PermissionRequiredMixin):
    """Autenticación + autorización + scoping por delegación en cada vista.

    Anónimo → redirige al login. Autenticado sin permiso → 403.
    Objeto de otra delegación → 404, porque no existe en su QuerySet.
    """

    def get_queryset(self):
        qs = Actividad.objects.select_related('funcionario', 'delegacion', 'tipo_actividad', 'periodo')
        return filtrar_por_delegacion(qs, self.request.user)


class ActividadPaginaMixin:
    """Contexto del listado para Create/Update: el modal vive en la misma página que el listado."""

    template_name = 'actividades/actividad_list.html'

    def contexto_listado(self):
        page_size = page_size_de_sesion(self.request)
        pagina = Paginator(self.get_queryset(), page_size).get_page(self.request.GET.get('page'))
        return {
            'page_obj': pagina,
            'actividades': pagina.object_list,
            'page_size': page_size,
            'page_sizes': PAGE_SIZES,
        }


class ActividadListView(ActividadScopeMixin, ListView):
    permission_required = 'actividades.view_actividad'
    template_name = 'actividades/actividad_list.html'
    context_object_name = 'actividades'

    def get_paginate_by(self, queryset):
        return page_size_de_sesion(self.request)

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto.update({
            'page_size': self.get_paginate_by(None),
            'page_sizes': PAGE_SIZES,
            'form': ActividadWebForm(user=self.request.user),
            'form_action': reverse('actividad_create'),
            'modal_titulo': 'Nueva actividad',
            'modal_abierto': False,
        })
        return contexto


class ActividadFormMixin(ActividadPaginaMixin, SuccessMessageMixin):
    form_class = ActividadWebForm
    success_url = reverse_lazy('actividad_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto.update(self.contexto_listado())
        # Si hay errores, la misma plantilla se vuelve a mostrar con el modal abierto.
        contexto['modal_abierto'] = True
        contexto['form_action'] = self.request.path
        return contexto


class ActividadCreateView(ActividadScopeMixin, ActividadFormMixin, CreateView):
    permission_required = 'actividades.add_actividad'
    success_message = 'Actividad %(numero)s registrada correctamente.'
    extra_context = {'modal_titulo': 'Nueva actividad'}


class ActividadUpdateView(ActividadScopeMixin, ActividadFormMixin, UpdateView):
    permission_required = 'actividades.change_actividad'
    success_message = 'Actividad %(numero)s actualizada correctamente.'
    extra_context = {'modal_titulo': 'Editar actividad'}


class ActividadDeleteView(ActividadScopeMixin, DeleteView):
    permission_required = 'actividades.delete_actividad'
    http_method_names = ['post']  # eliminar solo por POST (con CSRF)
    success_url = reverse_lazy('actividad_list')

    def form_valid(self, form):
        numero = self.object.numero
        respuesta = super().form_valid(form)
        messages.success(self.request, f'Actividad {numero} eliminada.')
        return respuesta
