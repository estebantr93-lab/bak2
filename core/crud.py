"""Base reutilizable para los CRUD web (fuera del Admin).

Cada CRUD declara su modelo, columnas, formulario y permisos; esta base aporta lo común:

- Seguridad por capas: LoginRequiredMixin (autenticación) + PermissionRequiredMixin
  (autorización) + scoping por delegación en get_queryset (un objeto de otra delegación da 404).
- Solo registros activos: se parte de Model.objects, que excluye los eliminados lógicamente.
- Paginación 5 / 15 / 30 recordada en request.session; valores no permitidos se ignoran.
- Crear y editar en un modal: si el formulario tiene errores se vuelve a mostrar abierto.
- Eliminar solo por POST (con CSRF) y de forma lógica (deleted_at).
- Exportar a Excel (.xlsx, reportes/services.py) el mismo QuerySet del listado: respeta permisos,
  scoping y borrado lógico.
"""
from datetime import date, datetime

from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.paginator import Paginator
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from reportes.services import respuesta_xlsx, valor_excel

from .admin_utils import filtrar_por_delegacion

PAGE_SIZES = [5, 15, 30]
PAGE_SIZE_DEFAULT = 15
SESSION_PAGE_SIZE = 'page_size'


def page_size_from_session(request):
    """Lee ?page_size= y lo guarda en la sesión solo si es un valor permitido."""
    valor = request.GET.get('page_size')
    if valor is not None:
        try:
            numero = int(valor)
        except ValueError:
            numero = None
        if numero in PAGE_SIZES:
            request.session[SESSION_PAGE_SIZE] = numero
    numero = request.session.get(SESSION_PAGE_SIZE, PAGE_SIZE_DEFAULT)
    return numero if numero in PAGE_SIZES else PAGE_SIZE_DEFAULT


class Column:
    """Columna del listado y del Excel. `value` es una ruta de atributos ('employee.name')
    o una función que recibe el objeto. `badge` devuelve una clase CSS opcional."""

    def __init__(self, header, value, badge=None, kind='text'):
        self.header, self.value, self.badge, self.kind = header, value, badge, kind

    def resolve(self, obj):
        if callable(self.value):
            return self.value(obj)
        resultado = obj
        for parte in self.value.split('.'):
            resultado = getattr(resultado, parte, None)
            if resultado is None:
                return ''
            if callable(resultado):
                resultado = resultado()
        return resultado


def as_text(valor):
    if isinstance(valor, datetime):
        return timezone.localtime(valor).strftime('%d-%m-%Y %H:%M') if timezone.is_aware(valor) else valor.strftime('%d-%m-%Y %H:%M')
    if isinstance(valor, date):
        return valor.strftime('%d-%m-%Y')
    if isinstance(valor, bool):
        return 'Sí' if valor else 'No'
    return '' if valor is None else str(valor)


class CrudConfig:
    """Datos que declara cada CRUD."""

    model = None
    form_class = None
    scope_field = 'delegation'      # ruta hasta la delegación, para el scoping
    select_related = ()
    columns = []
    title = ''                       # plural para títulos
    singular = ''                    # para mensajes y el modal
    femenino = True                  # concordancia: «registrada» / «registrado»
    url_prefix = ''                  # nombres de URL: <prefix>_list, _create, _update, _delete, _export
    context_object_name = 'objects'
    filters = {}                     # parámetros GET permitidos → lookup (por ejemplo {'activity': 'activity_id'})
    row_links = []                   # [(texto, nombre_url, parametro_get, permiso)] enlaces extra por fila

    @property
    def fin(self):
        return 'a' if self.femenino else 'o'

    def perm(self, accion):
        meta = self.model._meta
        return f'{meta.app_label}.{accion}_{meta.model_name}'

    def url(self, accion, *args):
        return reverse(f'{self.url_prefix}_{accion}', args=args)

    def get_queryset(self):
        qs = self.model.objects.select_related(*self.select_related)  # objects = solo activos
        qs = filtrar_por_delegacion(qs, self.request.user, self.scope_field)
        for parametro, lookup in self.filters.items():
            valor = self.request.GET.get(parametro)
            if valor and valor.isdigit():
                qs = qs.filter(**{lookup: valor})
        return qs

    def active_filters(self):
        return {p: self.request.GET[p] for p in self.filters if self.request.GET.get(p, '').isdigit()}

    def form_kwargs_extra(self):
        return {'user': self.request.user}

    def build_rows(self, objetos):
        user = self.request.user
        filas = []
        for obj in objetos:
            celdas = []
            for col in self.columns:
                valor = col.resolve(obj)
                celdas.append({
                    'text': as_text(valor), 'raw': valor, 'kind': col.kind,
                    'badge': col.badge(obj) if col.badge else '',
                })
            enlaces = [
                {'text': texto, 'url': reverse(nombre) + f'?{param}={obj.pk}'}
                for texto, nombre, param, permiso in self.row_links if user.has_perm(permiso)
            ]
            filas.append({'obj': obj, 'cells': celdas, 'links': enlaces,
                          'update_url': self.url('update', obj.pk), 'delete_url': self.url('delete', obj.pk)})
        return filas

    def crud_context(self, page_obj):
        user = self.request.user
        filtros = self.active_filters()
        return {
            'title': self.title,
            'singular': self.singular,
            'headers': [c.header for c in self.columns],
            'rows': self.build_rows(page_obj.object_list),
            'page_obj': page_obj,
            self.context_object_name: page_obj.object_list,
            'page_size': page_size_from_session(self.request),
            'page_sizes': PAGE_SIZES,
            'filters': filtros,
            'filters_query': '&'.join(f'{k}={v}' for k, v in filtros.items()),
            'list_url': self.url('list'),
            'create_url': self.url('create'),
            'export_url': self.url('export'),
            'can_add': user.has_perm(self.perm('add')),
            'can_change': user.has_perm(self.perm('change')),
            'can_delete': user.has_perm(self.perm('delete')),
        }


class ScopedCrudMixin(LoginRequiredMixin, PermissionRequiredMixin):
    """Anónimo → login. Autenticado sin permiso → 403. Objeto fuera de su alcance → 404."""


class CrudListView(ScopedCrudMixin, CrudConfig, ListView):
    template_name = 'crud/list.html'

    def get_permission_required(self):
        return (self.perm('view'),)

    def get_paginate_by(self, queryset):
        return page_size_from_session(self.request)

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto.update(self.crud_context(contexto['page_obj']))
        contexto.update({
            'form': self.form_class(**self.form_kwargs_extra()),
            'form_action': self.url('create'),
            'modal_titulo': f'Nuev{self.fin} {self.singular}',
            'modal_abierto': False,
        })
        return contexto


class CrudFormView(ScopedCrudMixin, CrudConfig, SuccessMessageMixin):
    template_name = 'crud/list.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(self.form_kwargs_extra())
        return kwargs

    def get_success_url(self):
        return self.url('list')

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        pagina = Paginator(self.get_queryset(), page_size_from_session(self.request))
        contexto.update(self.crud_context(pagina.get_page(self.request.GET.get('page'))))
        # Crear/editar se muestran en el modal de la misma página; con errores queda abierto.
        contexto['modal_abierto'] = True
        contexto['form_action'] = self.request.path
        return contexto


class CrudCreateView(CrudFormView, CreateView):
    def get_permission_required(self):
        return (self.perm('add'),)

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['modal_titulo'] = f'Nuev{self.fin} {self.singular}'
        return contexto

    def get_success_message(self, cleaned_data):
        return f'{self.singular.capitalize()} «{self.object}» registrad{self.fin} correctamente.'


class CrudUpdateView(CrudFormView, UpdateView):
    def get_permission_required(self):
        return (self.perm('change'),)

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['modal_titulo'] = f'Editar {self.singular}'
        return contexto

    def get_success_message(self, cleaned_data):
        return f'{self.singular.capitalize()} «{self.object}» actualizad{self.fin} correctamente.'


class CrudDeleteView(ScopedCrudMixin, CrudConfig, DeleteView):
    http_method_names = ['post']  # nunca por GET; el formulario lleva CSRF

    def get_permission_required(self):
        return (self.perm('delete'),)

    def get_form_class(self):
        # DeleteView valida un formulario vacío (solo CSRF), no el ModelForm de la entidad.
        return forms.Form

    def get_form_kwargs(self):
        return {'data': self.request.POST} if self.request.method == 'POST' else {}

    def get_success_url(self):
        return self.url('list')

    def form_valid(self, form):
        nombre = str(self.object)
        respuesta = super().form_valid(form)  # llama a object.delete(): borrado lógico (SoftDeleteModel)
        messages.success(self.request, f'{self.singular.capitalize()} «{nombre}» eliminad{self.fin}.')
        return respuesta


class CrudExportView(ScopedCrudMixin, CrudConfig, View):
    """Descarga .xlsx con openpyxl: encabezados + filas del mismo QuerySet del listado."""

    def get_permission_required(self):
        return (self.perm('view'),)

    def get(self, request, *args, **kwargs):
        filas = (
            [valor_excel(col.resolve(obj), as_text) for col in self.columns]
            for obj in self.get_queryset().iterator()  # mismo QuerySet del listado
        )
        nombre = f'{self.url_prefix}_{timezone.localdate():%Y%m%d}.xlsx'
        return respuesta_xlsx(self.title, [c.header for c in self.columns], filas, nombre)
