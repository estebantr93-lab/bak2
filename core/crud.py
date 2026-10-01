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
from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.contrib.messages.views import SuccessMessageMixin
from django.core.paginator import Paginator
from django.db.models import Q
from django.urls import reverse
from django.utils.http import urlencode
from django.utils.text import slugify
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from reportes.services import as_text, respuesta_xlsx, valor_excel

from .admin_utils import cambios_del_formulario, filtrar_por_delegacion, registrar_en_auditoria, modificables, motivo_no_modificable, motivo_para_usuario, puede_modificar

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
    o una función que recibe el objeto. `badge` devuelve una clase CSS opcional.
    `sort` es la ruta del ORM para ordenar por esa columna (None = no ordenable).
    `kind`: 'text', 'badge', 'file' o 'person' (nombre con iniciales)."""

    def __init__(self, header, value, badge=None, kind='text', sort=None):
        self.header, self.value, self.badge, self.kind, self.sort = header, value, badge, kind, sort
        self.key = slugify(header) or 'col'

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
    filters = {}                     # parámetros GET permitidos → lookup (por ejemplo {'activity': 'activity_id'})
    choice_filters = {}              # parámetro GET → (lookup, valores permitidos), p. ej. {'status': ('status', {...})}
    # Filtros que se activan con ?param=1: param → (texto para el usuario, nombre del método que filtra).
    # Todo CRUD con dueño (Model.owner_field) acepta además ?mias=1 («solo los míos»).
    flag_filters = {}
    row_links = []                   # [(texto, nombre_url, parametro_get, permiso)] enlaces extra por fila
    search_fields = ()               # rutas del ORM donde busca ?q= (icontains)
    # Pestañas del listado: (clave, etiqueta, parámetros). La primera es «todas» ({}). Usan los
    # mismos filtros permitidos (choice_filters / flag_filters), así que no abren datos nuevos.
    tabs = []
    # Tarjetas de resumen: (clave de pestaña, tono). El número es el conteo de esa pestaña.
    kpis = []

    @property
    def fin(self):
        return 'a' if self.femenino else 'o'

    def perm(self, accion):
        meta = self.model._meta
        return f'{meta.app_label}.{accion}_{meta.model_name}'

    def url(self, accion, *args):
        return reverse(f'{self.url_prefix}_{accion}', args=args)

    def get_queryset(self):
        qs = self.queryset_para(self.request.GET)
        orden = self.orden_activo()
        return qs.order_by(orden, 'pk') if orden else qs

    def queryset_para(self, params):
        """Mismo alcance (delegación y solo activos) con los filtros de `params`. Lo usan el listado,
        el Excel y el conteo de cada pestaña."""
        qs = self.model.objects.select_related(*self.select_related)  # objects = solo activos
        qs = filtrar_por_delegacion(qs, self.request.user, self.scope_field)
        for lookup, valor in self._filtros_validos(params).values():
            qs = qs.filter(**{lookup: valor})
        for _, metodo in self._banderas_activas(params).values():
            qs = getattr(self, metodo)(qs)
        busqueda = self._busqueda(params)
        if busqueda:
            condicion = Q()
            for campo in self.search_fields:
                condicion |= Q(**{f'{campo}__icontains': busqueda})
            qs = qs.filter(condicion)
        return qs

    def _busqueda(self, params):
        return (params.get('q') or '').strip()[:100] if self.search_fields else ''

    def orden_activo(self):
        """?orden=<ruta> o ?orden=-<ruta>, solo entre las columnas ordenables (lista blanca)."""
        orden = self.request.GET.get('orden', '')
        permitidos = {c.sort for c in self.columns if c.sort}
        return orden if orden.lstrip('-') in permitidos else ''

    def _banderas(self):
        banderas = dict(self.flag_filters)
        if getattr(self.model, 'owner_field', None) is not None:
            banderas['mias'] = ('solo los míos' if not self.femenino else 'solo las mías', '_filtrar_mias')
        return banderas

    def _banderas_activas(self, params=None):
        params = self.request.GET if params is None else params
        return {p: v for p, v in self._banderas().items() if params.get(p) == '1'}

    def _filtrar_mias(self, qs):
        campo = self.model.owner_field
        return qs.filter(**{f'{campo}__user' if campo else 'user': self.request.user})

    def descripcion_filtros(self):
        """Textos de los filtros aplicados, para que la lista diga qué está mostrando."""
        textos = []
        for parametro, (lookup, valor) in self._filtros_validos().items():
            if parametro == 'period':
                from core.models import Period
                textos.append(f'período {Period.objects.filter(pk=valor).first() or valor}')
            elif parametro in self.choice_filters:
                campo = self.model._meta.get_field(lookup)
                textos.append(str(dict(campo.choices or {}).get(valor, f'{campo.verbose_name} {valor}')).lower())
            elif parametro == 'activity':
                textos.append(f'actividad {self.model._meta.get_field("activity").related_model.all_objects.filter(pk=valor).first() or valor}')
        textos += [texto for texto, _ in self._banderas_activas().values()]
        busqueda = self._busqueda(self.request.GET)
        if busqueda:
            textos.append(f'búsqueda «{busqueda}»')
        return textos

    def _filtros_validos(self, params=None):
        """{parámetro: (lookup, valor)} de los filtros GET válidos; los demás se ignoran."""
        params = self.request.GET if params is None else params
        validos = {}
        for parametro, lookup in self.filters.items():
            valor = params.get(parametro, '')
            if valor.isdigit():
                validos[parametro] = (lookup, valor)
        for parametro, (lookup, permitidos) in self.choice_filters.items():
            valor = params.get(parametro, '')
            if valor in permitidos:
                validos[parametro] = (lookup, valor)
        return validos

    def get_editable_queryset(self):
        """Registros que el usuario puede editar o eliminar: política única de core/admin_utils."""
        return modificables(self.get_queryset(), self.request.user)

    def check_modificable(self, obj):
        if not puede_modificar(self.request.user, obj):
            raise PermissionDenied(motivo_para_usuario(self.request.user, obj) or 'Solo puede modificar sus propios registros.')

    def active_filters(self):
        activos = {parametro: valor for parametro, (_, valor) in self._filtros_validos().items()}
        activos.update({parametro: '1' for parametro in self._banderas_activas()})
        busqueda = self._busqueda(self.request.GET)
        if busqueda:
            activos['q'] = busqueda
        return activos

    def pestanas(self, filtros):
        """Pestañas con su conteo y su URL; conservan los demás filtros (período, búsqueda, «mías»)."""
        claves = {clave for _, _, params in self.tabs for clave in params}
        base = {k: v for k, v in filtros.items() if k not in claves}
        actuales = {k: v for k, v in filtros.items() if k in claves}
        orden = self.orden_activo()
        resultado = []
        for clave, etiqueta, params in self.tabs:
            consulta = {**base, **params, **({'orden': orden} if orden else {})}
            resultado.append({
                'clave': clave, 'etiqueta': etiqueta, 'activa': params == actuales,
                'total': self.queryset_para({**base, **params}).count(),
                'url': self.url('list') + (f'?{urlencode(consulta)}' if consulta else ''),
            })
        return resultado

    def tarjetas(self, pestanas):
        por_clave = {p['clave']: p for p in pestanas}
        return [{**por_clave[clave], 'tono': tono} for clave, tono in self.kpis if clave in por_clave]

    def encabezados(self, filtros):
        """Encabezados con su enlace de orden (ascendente → descendente)."""
        orden = self.orden_activo()
        resultado = []
        for col in self.columns:
            item = {'texto': col.header, 'clave': col.key, 'url': '', 'dir': ''}
            if col.sort:
                if orden == col.sort:
                    siguiente, item['dir'] = f'-{col.sort}', 'asc'
                elif orden == f'-{col.sort}':
                    siguiente, item['dir'] = col.sort, 'desc'
                else:
                    siguiente = col.sort
                item['url'] = self.url('list') + '?' + urlencode({**filtros, 'orden': siguiente})
            resultado.append(item)
        return resultado

    def form_kwargs_extra(self):
        return {'user': self.request.user}

    def build_rows(self, objetos):
        user = self.request.user
        editables = set(self.get_editable_queryset().filter(pk__in=[o.pk for o in objetos]).values_list('pk', flat=True))
        filas = []
        for obj in objetos:
            celdas = []
            for col in self.columns:
                valor = col.resolve(obj)
                texto = as_text(valor)
                celdas.append({
                    'header': col.header, 'key': col.key, 'text': texto, 'raw': valor, 'kind': col.kind,
                    'iniciales': ''.join(p[0] for p in texto.replace('(', '').split()[:2]).upper() if col.kind == 'person' else '',
                    # Una línea por fila (como una tabla de datos); solo los textos largos se parten.
                    'nowrap': len(texto) <= 30,
                    'badge': col.badge(obj) if col.badge else '',
                })
            enlaces = [
                {'text': texto, 'url': reverse(nombre) + f'?{param}={obj.pk}'}
                for texto, nombre, param, permiso in self.row_links if user.has_perm(permiso)
            ]
            filas.append({'obj': obj, 'cells': celdas, 'links': enlaces,
                          'editable': obj.pk in editables and not motivo_no_modificable(obj),
                          'update_url': self.url('update', obj.pk), 'delete_url': self.url('delete', obj.pk)})
        return filas

    def crud_context(self, page_obj):
        user = self.request.user
        filtros = self.active_filters()
        orden = self.orden_activo()
        estado = {**filtros, **({'orden': orden} if orden else {})}
        pestanas = self.pestanas(filtros) if self.tabs else []
        return {
            'title': self.title,
            'singular': self.singular,
            'fin': self.fin,
            'headers': [c.header for c in self.columns],
            'columnas': self.encabezados(filtros),
            'pestanas': pestanas,
            'tarjetas': self.tarjetas(pestanas),
            'busqueda': filtros.get('q', ''),
            'buscable': bool(self.search_fields),
            'orden': orden,
            'page_range': page_obj.paginator.get_elided_page_range(page_obj.number, on_each_side=1, on_ends=1),
            'tabla_id': self.url_prefix,
            'rows': self.build_rows(page_obj.object_list),
            'page_obj': page_obj,
            'page_size': page_size_from_session(self.request),
            'page_sizes': PAGE_SIZES,
            'filters': filtros,
            'filters_desc': self.descripcion_filtros(),
            # Estado de la lista (filtros, búsqueda y orden) para paginación, modal y Excel.
            'filters_query': urlencode(estado),
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

    def form_valid(self, form):
        # Traza: quién creó o modificó el registro y qué valores cambió (las fechas las pone BaseModel).
        es_nuevo = form.instance._state.adding
        cambios = cambios_del_formulario(form)
        respuesta = super().form_valid(form)
        if es_nuevo or cambios:
            registrar_en_auditoria(self.request.user, 'crear' if es_nuevo else 'modificar', self.object, cambios=cambios)
        return respuesta

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

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)  # fuera de su delegación → 404
        self.check_modificable(obj)         # de otro funcionario o bloqueado por regla → 403
        return obj

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

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        self.check_modificable(obj)
        return obj

    def get_form_class(self):
        # DeleteView valida un formulario vacío (solo CSRF), no el ModelForm de la entidad.
        return forms.Form

    def get_form_kwargs(self):
        return {'data': self.request.POST} if self.request.method == 'POST' else {}

    def get_success_url(self):
        return self.url('list')

    def form_valid(self, form):
        nombre = str(self.object)
        respuesta = super().form_valid(form)  # llama a object.delete(): borrado lógico (BaseModel)
        registrar_en_auditoria(self.request.user, 'eliminar', self.object)  # el superadmin ve quién lo eliminó
        messages.success(self.request, f'{self.singular.capitalize()} «{nombre}» eliminad{self.fin}.')
        return respuesta


class CrudExportView(ScopedCrudMixin, CrudConfig, View):
    """Descarga .xlsx con openpyxl: encabezados + filas del mismo QuerySet del listado."""

    def get_permission_required(self):
        return (self.perm('view'),)

    def get(self, request, *args, **kwargs):
        qs = self.get_queryset()  # mismo QuerySet del listado
        # ?ids=1,2,3: solo los seleccionados, siempre dentro del alcance del usuario.
        if 'ids' in request.GET:  # con ?ids= sin ningún id válido no se exporta nada, nunca todo
            ids = [i for i in request.GET['ids'].split(',') if i.isdigit()][:1000]
            qs = qs.filter(pk__in=ids)
        filas = (
            [valor_excel(col.resolve(obj)) for col in self.columns]
            for obj in qs.iterator()
        )
        nombre = f'{self.url_prefix}_{timezone.localdate():%Y%m%d}.xlsx'
        return respuesta_xlsx(self.title, [c.header for c in self.columns], filas, nombre)
