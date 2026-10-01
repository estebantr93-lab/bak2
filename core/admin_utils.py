from django import forms
from django.apps import apps
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.html import format_html

from .models import es_soft_delete


def get_usuario_delegacion(user):
    if not user or not user.is_authenticated:
        return None
    Employee = apps.get_model('funcionarios', 'Employee')
    try:
        funcionario = Employee.objects.select_related('delegation').get(user=user)
    except Employee.DoesNotExist:
        return None
    return funcionario.delegation


GRUPO_ADMINISTRADORES = 'Administradores'
GRUPO_FUNCIONARIOS = 'Funcionarios'
GRUPO_VERIFICADORES = 'Verificadores'

ROL_SUPERADMIN = 'superadmin'
ROL_ADMIN_DELEGACION = 'admin_delegacion'
ROL_VERIFICADOR = 'reviewer'
ROL_FUNCIONARIO = 'employee'

ROLES_ETIQUETAS = {
    ROL_SUPERADMIN: 'Administrador general',
    ROL_ADMIN_DELEGACION: 'Administrador de delegación',
    ROL_VERIFICADOR: 'Verificador',
    ROL_FUNCIONARIO: 'Funcionario',
}


def get_rol(user):
    """Rol principal del usuario, en orden de mayor a menor alcance.

    Se guarda en el propio objeto user: durante una petición los hooks del Admin y las vistas lo
    consultan varias veces y así se evita repetir la consulta de grupos.
    """
    if not user or not user.is_authenticated:
        return None
    if not hasattr(user, '_sgr_rol'):
        user._sgr_rol = _calcular_rol(user)
    return user._sgr_rol


def _calcular_rol(user):
    if user.is_superuser:
        return ROL_SUPERADMIN
    # groups.all() aprovecha prefetch_related('user__groups') en listados.
    grupos = {grupo.name for grupo in user.groups.all()}
    if GRUPO_ADMINISTRADORES in grupos:
        return ROL_ADMIN_DELEGACION
    if GRUPO_VERIFICADORES in grupos:
        return ROL_VERIFICADOR
    if GRUPO_FUNCIONARIOS in grupos:
        return ROL_FUNCIONARIO
    return None


def es_usuario_sin_restriccion(user):
    """Solo el superusuario y los verificadores ven todas las delegaciones.

    Los administradores de delegación quedan acotados a la delegación de su
    perfil de Funcionario, igual que los funcionarios.
    """
    return get_rol(user) in (ROL_SUPERADMIN, ROL_VERIFICADOR)


def perfil_desactivado(user):
    """True si el usuario tiene perfil de funcionario y está desactivado (Employee.is_active=False)."""
    Employee = apps.get_model('funcionarios', 'Employee')
    return Employee.objects.filter(user=user, is_active=False).exists()


def tiene_acceso_al_sistema(user):
    """Puede usar el sistema quien tiene rol y, salvo los roles globales, un perfil activo con delegación."""
    if get_rol(user) is None:
        return False
    if es_usuario_sin_restriccion(user):
        return True
    return get_usuario_delegacion(user) is not None and not perfil_desactivado(user)


def solo_propios(queryset, user, campo_funcionario):
    """El funcionario ve toda su delegación, pero solo modifica lo suyo.

    `campo_funcionario` es la ruta hasta el Employee dueño ('employee', 'activity__employee'...);
    '' indica que el queryset ya es de Employee. Para los demás roles no cambia el queryset.
    """
    if get_rol(user) == ROL_FUNCIONARIO:
        return queryset.filter(**{f'{campo_funcionario}__user' if campo_funcionario else 'user': user})
    return queryset


# ---------------------------------------------------------------------------------------------------
# Política única de modificación. La usan el CRUD web (core/crud.py) y el Admin (ScopedModelAdmin),
# así una regla nueva no puede quedar aplicada en un lado y olvidada en el otro.
#   - Delegación: lo decide el scoping (filtrar_por_delegacion / ScopedModelAdmin.get_queryset).
#   - Propiedad: Model.owner_field (ruta al Employee dueño) → el rol funcionario solo modifica lo suyo.
#   - Regla de negocio: Model.motivo_no_modificable() (por ejemplo, período cerrado).
# ---------------------------------------------------------------------------------------------------
#   - Bloqueo: Model.bloqueo_modificacion = ({lookup: valor}, mensaje). Una sola declaración sirve para
#     excluir en consultas (excluir_bloqueados) y para evaluar un objeto, guardado o nuevo.
def excluir_bloqueados(queryset):
    bloqueo = getattr(queryset.model, 'bloqueo_modificacion', None)
    return queryset.exclude(**bloqueo[0]) if bloqueo else queryset


def modificables(queryset, user):
    """Lo que el usuario puede modificar: sin bloqueados y, para el funcionario, solo lo propio y
    sin lo que el modelo le congela (Model.bloqueo_funcionario, p. ej. una actividad ya aprobada)."""
    queryset = excluir_bloqueados(queryset)
    campo = getattr(queryset.model, 'owner_field', None)
    if campo is None:
        return queryset
    queryset = solo_propios(queryset, user, campo)
    bloqueo = getattr(queryset.model, 'bloqueo_funcionario', None)
    if bloqueo and get_rol(user) == ROL_FUNCIONARIO:
        queryset = queryset.exclude(**bloqueo[0])
    return queryset


def _cumple_bloqueo(obj, bloqueo):
    """Mensaje del bloqueo si el objeto cumple alguno de sus lookups. Recorre rutas con '__' sobre el
    objeto (p. ej. 'activity__period__is_closed'), así sirve aunque no esté guardado."""
    if not bloqueo:
        return None
    lookups, mensaje = bloqueo
    for ruta, esperado in lookups.items():
        valor = obj
        for paso in ruta.split('__'):
            valor = getattr(valor, paso, None)
            if valor is None:
                break
        if valor == esperado:
            return mensaje
    return None


def motivo_no_modificable(obj):
    """Mensaje del bloqueo general (Model.bloqueo_modificacion), que vale para todos los roles."""
    return _cumple_bloqueo(obj, getattr(type(obj), 'bloqueo_modificacion', None))


def motivo_para_usuario(user, obj):
    """Por qué este usuario no puede modificar el objeto (bloqueo general o propio del funcionario)."""
    motivo = motivo_no_modificable(obj)
    if motivo is None and get_rol(user) == ROL_FUNCIONARIO:
        motivo = _cumple_bloqueo(obj, getattr(type(obj), 'bloqueo_funcionario', None))
    return motivo


def puede_modificar(user, obj):
    if motivo_no_modificable(obj):
        return False
    return modificables(type(obj)._default_manager.filter(pk=obj.pk), user).exists()


def filtrar_por_delegacion(queryset, user, campo='delegation'):
    """Scoping para vistas fuera del Admin: mismo criterio que ScopedModelAdmin."""
    if es_usuario_sin_restriccion(user):
        return queryset
    delegacion = get_usuario_delegacion(user)
    if delegacion is None:
        return queryset.none()
    return queryset.filter(**{campo: delegacion.pk})


def registrar_en_auditoria(user, accion, obj, detalle='', cambios=None):
    """Único punto de entrada a la traza de auditoría: quién, qué acción, sobre qué registro y, si
    corresponde, qué campos cambió ({campo: [valor anterior, valor nuevo]}). La consulta el superadmin.

    Las fechas (created_at, updated_at, deleted_at) viven en cada registro; esta traza agrega quién."""
    AuditLog = apps.get_model('colaboracion', 'AuditLog')
    AuditLog.objects.create(
        user=user if user and user.is_authenticated else None, action=accion,
        entity_type=type(obj).__name__, entity_id=obj.pk, detail=detalle or str(obj),
        changes=cambios or {},
    )


def _valor_legible(campo, valor):
    """Texto de un valor de formulario tal como lo reconoce una persona (nombre en vez de id, Sí/No…)."""
    if isinstance(campo, forms.FileField):
        return getattr(valor, 'name', '') or ''
    if valor is None or valor == '':
        return ''
    if isinstance(campo, forms.ModelMultipleChoiceField):
        return ', '.join(_valor_legible(forms.ModelChoiceField(campo.queryset), v) for v in valor)
    if isinstance(campo, forms.ModelChoiceField):
        if hasattr(valor, 'pk'):
            return str(valor)
        # Valor inicial = id: se busca con el manager por defecto (incluye eliminados lógicamente).
        obj = campo.queryset.model._default_manager.filter(pk=valor).first()
        return str(obj) if obj is not None else str(valor)
    if isinstance(valor, bool):
        return 'Sí' if valor else 'No'
    if isinstance(campo, forms.ChoiceField):
        etiquetas = {str(k): str(v) for k, v in campo.choices if not isinstance(v, (list, tuple))}
        return etiquetas.get(str(valor), str(valor))
    return str(valor)


def cambios_del_formulario(form):
    """Campos que el formulario modificó, con su valor anterior y el nuevo. Usa form.changed_data,
    que Django ya calcula comparando lo enviado con form.initial."""
    cambios = {}
    for nombre in form.changed_data:
        campo = form.fields[nombre]
        if 'password' in nombre:
            cambios[nombre] = ['***', '***']  # nunca se guarda una contraseña, ni siquiera cifrada
            continue
        antes = _valor_legible(campo, form.initial.get(nombre, campo.initial))
        despues = _valor_legible(campo, form.cleaned_data.get(nombre))
        if antes != despues:
            cambios[nombre] = [antes, despues]
    return cambios


def ve_eliminados(user):
    """Regla de negocio: lo que eliminan los administradores de delegación (borrado lógico) lo sigue
    viendo el administrador general, que además puede restaurarlo."""
    return get_rol(user) == ROL_SUPERADMIN


class EstadoRegistroFilter(admin.SimpleListFilter):
    """Filtro del superadmin: registros activos, eliminados o todos (por defecto, todos)."""
    title = 'estado del registro'
    parameter_name = 'registro'

    def lookups(self, request, model_admin):
        return [('activos', 'Activos'), ('eliminados', 'Eliminados')]

    def queryset(self, request, queryset):
        if self.value() == 'activos':
            return queryset.filter(deleted_at__isnull=True)
        if self.value() == 'eliminados':
            return queryset.filter(deleted_at__isnull=False)
        return queryset


FECHAS_DE_AUDITORIA = ('created_at', 'updated_at')


def con_fechas_de_auditoria(model, obj, campos):
    """Las fechas de auditoría se ven en la ficha de un registro existente, pero no se editan."""
    if obj is None:
        return campos
    propios = {campo.name for campo in model._meta.fields}
    return [*campos, *(c for c in FECHAS_DE_AUDITORIA if c in propios and c not in campos)]


class AuditarCambiosAdmin:
    """Traza de los cambios de configuración hechos en el Admin (RF-036): quién creó, modificó o
    eliminó un período, una meta, un parámetro o un catálogo, y qué campos cambió. Cerrar o reabrir
    un período queda con su propia acción (RN-013: la reapertura debe quedar auditada)."""

    def get_readonly_fields(self, request, obj=None):
        return con_fechas_de_auditoria(self.model, obj, list(super().get_readonly_fields(request, obj)))

    def save_model(self, request, obj, form, change):
        cambios = cambios_del_formulario(form)
        super().save_model(request, obj, form, change)
        campos = [campo for campo in form.changed_data]
        if change and 'is_closed' in campos:
            accion = 'cerrar_periodo' if obj.is_closed else 'reabrir_periodo'
        else:
            accion = 'modificar_configuracion' if change else 'crear_configuracion'
        detalle = f'{obj}' + (f' · campos: {", ".join(campos)}' if campos else '')
        registrar_en_auditoria(request.user, accion, obj, detalle, cambios=cambios)

    def delete_model(self, request, obj):
        registrar_en_auditoria(request.user, 'eliminar_configuracion', obj)
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            registrar_en_auditoria(request.user, 'eliminar_configuracion', obj)
        super().delete_queryset(request, queryset)


# Campos de estado que el listado del Admin muestra como etiqueta de color (misma clase que en las vistas).
CAMPOS_DE_ESTADO = ('status', 'validation_status', 'new_status')


def etiqueta_de_estado(clase, texto):
    return format_html('<span class="estado estado-{}">{}</span>', clase, texto)


def columna_de_estado(modelo, campo):
    """Columna del changelist que muestra el estado como etiqueta y sigue ordenando por el campo."""
    @admin.display(description=modelo._meta.get_field(campo).verbose_name, ordering=campo)
    def columna(obj):
        return etiqueta_de_estado(getattr(obj, campo), getattr(obj, f'get_{campo}_display')())
    columna.__name__ = f'{campo}_etiqueta'
    return columna


class ScopedModelAdmin:
    scope_by = 'delegation'

    def _muestra_eliminados(self, request):
        return es_soft_delete(self.model) and ve_eliminados(request.user)

    def get_list_filter(self, request):
        filtros = super().get_list_filter(request)
        if self._muestra_eliminados(request):
            return [*filtros, EstadoRegistroFilter]
        if es_usuario_sin_restriccion(request.user):
            return filtros
        # Un usuario acotado ya ve una sola delegación: filtrar por ella no aporta y listaría las demás.
        return [f for f in filtros if f != self.scope_by]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if es_soft_delete(self.model) and not ve_eliminados(request.user):
            qs = qs.filter(deleted_at__isnull=True)  # los eliminados solo los ve el administrador general
        return filtrar_por_delegacion(qs, request.user, self.scope_by)

    def get_list_display(self, request):
        columnas = [
            columna_de_estado(self.model, c) if c in CAMPOS_DE_ESTADO and self.model._meta.get_field(c).choices else c
            for c in super().get_list_display(request)
        ]
        return [*columnas, 'estado_registro'] if self._muestra_eliminados(request) else columnas

    @admin.display(description='Registro')
    def estado_registro(self, obj):
        if obj.deleted_at is None:
            return etiqueta_de_estado('activo', 'Activo')
        return etiqueta_de_estado('eliminado', f'Eliminado el {timezone.localtime(obj.deleted_at):%d-%m-%Y %H:%M}')

    def get_actions(self, request):
        acciones = super().get_actions(request)
        if self._muestra_eliminados(request):
            acciones['restaurar_registros'] = (
                type(self).restaurar_registros, 'restaurar_registros', 'Restaurar los registros eliminados seleccionados',
            )
        return acciones

    def restaurar_registros(self, request, queryset):
        restaurados = 0
        for obj in queryset.filter(deleted_at__isnull=False):
            try:
                obj.restore()  # también recupera los registros que se eliminaron junto con él
            except ValidationError as error:
                # Su padre sigue eliminado: se omite y se dice qué restaurar antes.
                self.message_user(request, f'No se restauró «{obj}»: {" ".join(error.messages)}', level=messages.WARNING)
                continue
            registrar_en_auditoria(request.user, 'restaurar', obj)
            restaurados += 1
        if restaurados:
            self.message_user(request, f'{restaurados} registro(s) restaurado(s).', level=messages.SUCCESS)

    def delete_model(self, request, obj):
        super().delete_model(request, obj)
        if es_soft_delete(self.model):
            registrar_en_auditoria(request.user, 'eliminar', obj)

    def delete_queryset(self, request, queryset):
        objetos = list(queryset.filter(deleted_at__isnull=True)) if es_soft_delete(self.model) else []
        super().delete_queryset(request, queryset)
        for obj in objetos:
            registrar_en_auditoria(request.user, 'eliminar', obj)

    def get_readonly_fields(self, request, obj=None):
        return con_fechas_de_auditoria(self.model, obj, list(super().get_readonly_fields(request, obj)))

    def save_model(self, request, obj, form, change):
        cambios = cambios_del_formulario(form)
        super().save_model(request, obj, form, change)
        if cambios or not change:
            registrar_en_auditoria(request.user, 'modificar' if change else 'crear', obj, cambios=cambios)

    def save_formset(self, request, form, formset, change):
        # Inlines (p. ej. evidencias dentro de una actividad): cada fila creada o modificada queda en la traza.
        filas = [
            (fila, fila.instance._state.adding, cambios_del_formulario(fila))
            for fila in formset.forms
            if fila.has_changed() and not (formset.can_delete and formset._should_delete_form(fila))
        ]
        super().save_formset(request, form, formset, change)
        for fila, es_nueva, cambios in filas:
            if fila.instance.pk is not None:
                registrar_en_auditoria(request.user, 'crear' if es_nueva else 'modificar', fila.instance, cambios=cambios)
        for obj in formset.deleted_objects:
            registrar_en_auditoria(request.user, 'eliminar', obj)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not es_usuario_sin_restriccion(request.user):
            kwargs['queryset'] = self._opciones_relacionadas(db_field.related_model, request)
        elif getattr(db_field.related_model, 'bloqueo_modificacion', None):
            kwargs['queryset'] = excluir_bloqueados(db_field.related_model._default_manager.all())
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def _opciones_relacionadas(self, relacionado, request):
        """Opciones de una llave foránea para un usuario acotado.

        Se toman del Admin del modelo relacionado cuando es un ScopedModelAdmin: ese Admin ya sabe
        llegar a la delegación (directa o indirecta, p. ej. evidence__activity__delegation) y excluir
        eliminados. Encima se aplica la regla de dueño. Los usuarios se limitan a los de su delegación.
        """
        from django.contrib.auth.models import User

        delegacion = get_usuario_delegacion(request.user)
        admin_relacionado = self.admin_site._registry.get(relacionado)
        if isinstance(admin_relacionado, ScopedModelAdmin):
            base = admin_relacionado.get_queryset(request)
        elif relacionado is User:
            base = User.objects.filter(employee__delegation=delegacion) if delegacion else User.objects.none()
        elif any(campo.name == 'delegation' for campo in relacionado._meta.fields):
            base = relacionado._default_manager.filter(delegation=delegacion)
        else:
            base = relacionado._default_manager.all()  # datos maestros compartidos (cargo, tipo, período)
        return modificables(base, request.user)

    def has_add_permission(self, request):
        if not super().has_add_permission(request):
            return False
        if es_usuario_sin_restriccion(request.user):
            return True
        return get_usuario_delegacion(request.user) is not None

    def _objeto_en_alcance(self, request, obj):
        return self.get_queryset(request).filter(pk=obj.pk).exists()  # mismo alcance que el listado

    def _puede_modificar(self, request, obj):
        if obj is not None and getattr(obj, 'deleted_at', None) is not None:
            return False  # un registro eliminado se consulta (solo lectura) o se restaura, no se edita
        return obj is None or (self._objeto_en_alcance(request, obj) and puede_modificar(request.user, obj))

    def has_change_permission(self, request, obj=None):
        # Sin permiso de cambio sobre un registro visible, el Admin lo muestra en solo lectura.
        return super().has_change_permission(request, obj) and self._puede_modificar(request, obj)

    def has_delete_permission(self, request, obj=None):
        return super().has_delete_permission(request, obj) and self._puede_modificar(request, obj)

    def get_search_results(self, request, queryset, search_term):
        # Autocompletado de un campo relacionado (p. ej. la actividad de una evidencia): mismas opciones
        # que el formulario, es decir, solo lo que el usuario puede modificar.
        queryset, duplicados = super().get_search_results(request, queryset, search_term)
        if request.GET.get('field_name'):
            queryset = modificables(queryset, request.user)
            if es_soft_delete(queryset.model):
                queryset = queryset.filter(deleted_at__isnull=True)  # nada nuevo cuelga de algo eliminado
        return queryset, duplicados
