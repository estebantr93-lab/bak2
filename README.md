# Sistema de Gestión de Resultados (SGR)

Proyecto integrado académico (INACAP) correspondiente al caso de las delegaciones municipales de la Ilustre Municipalidad de La Serena.

## Descripción

El **Sistema de Gestión de Resultados (SGR)** es una aplicación web que centraliza el registro, seguimiento, verificación y medición de la gestión de funcionarios y delegaciones, generando indicadores individuales y colectivos que apoyan el control operativo y la toma de decisiones.

Esta entrega corresponde a la **Evaluación Formativa – Unidad II (Programación Back End, TI3V41)**: integración Django de autenticación, recuperación de contraseña, permisos y scoping, CRUD con ModelForm, archivos, sesiones y paginación, borrado lógico, exportación a Excel y despliegue en AWS Academy, sobre MySQL/MariaDB.

> **Importante:** el proyecto se usa únicamente con **datos ficticios**. Está prohibido cargar información real de ciudadanos o funcionarios.

## Stack y dependencias

- **Backend:** Python 3 + Django 6.1.1
- **Base de datos:** MySQL 8.4+ o MariaDB 10.11+ (local en desarrollo, Amazon RDS en AWS), configurada por variables de entorno. Son las versiones mínimas que acepta Django 6.1.
- **Variables de entorno:** `python-dotenv`

| Paquete | Versión |
| --- | --- |
| asgiref | 3.12.1 |
| Django | 6.1.1 |
| python-dotenv | 1.2.3 |
| sqlparse | 0.6.0 |
| tzdata | 2026.3 |
| pillow | 12.3.0 |
| mysqlclient | 2.3.0 |

## Requisitos previos

- **Git** instalado.
- **Python 3.12+** instalado (Django 6.1 no funciona con versiones anteriores).
- **MySQL 8.4+ o MariaDB 10.11+** en ejecución (local, en Docker o Amazon RDS).
- Para compilar `mysqlclient` en Linux: `sudo apt install pkg-config libmariadb-dev` (Debian/Ubuntu) o `sudo dnf install python3.12 python3.12-devel gcc pkgconf mariadb1011-devel` (Amazon Linux 2023; si `mariadb1011-devel` no existe en su versión, use `mariadb-connector-c-devel`). En Amazon Linux 2023 `python3` es la 3.9: cree el entorno con `python3.12 -m venv .venv`. En Windows y macOS `pip` descarga una rueda precompilada.
- Se documentan comandos para **Linux/macOS (bash/zsh)**; para Windows se usan los equivalentes de `venv`/`activate`.

## Arquitectura modular (apps Django)

Cada módulo del dominio SGR es una app Django independiente:

```
Proyecto_Integrado_SGR/
├── config/          # Proyecto Django (settings, urls con django.contrib.auth.urls, wsgi, asgi) + portada
├── core/            # Delegation, Position, ActivityType, Period, Parameter + scoping, soft delete y seed_data
├── funcionarios/    # Employee (perfil), PasswordResetCode, grupos/permisos (security.py), login y recuperación
├── actividades/     # Activity, SocialCase + CRUD web protegido (ListView/CreateView/UpdateView/DeleteView + modal)
├── evidencias/      # Evidence, Validation + acción "Aprobar evidencias seleccionadas" + carga de archivos validada
├── agenda/          # Commitment, CommitmentFollowUp
├── medicion/        # Goal, Weighting, Indicator + fórmulas de cálculo (services.py)
├── monitoreo/       # DashboardPanel
├── dashboard/       # Dashboard de resumen por funcionario y rol (services.py)
├── reportes/        # Exportación a Excel (.xlsx) con openpyxl (services.py)
├── colaboracion/    # Comment, Alert, AuditLog
├── templates/       # landing, base, 403/404/500, registration/ (login y recuperación), dashboard/, crud/list.html (los 4 CRUD)
├── static/          # static/css/style.css y static/js/confirmar.js (SweetAlert2)
├── .env.example
├── .gitignore
├── manage.py
├── README.md
└── requirements.txt
```

### Nomenclatura

Los nombres técnicos de **modelos, campos, tablas y valores internos de choices** están en inglés, en `snake_case` para campos y tablas (`db_table`: `activity`, `evidence`, `commitment_follow_up`…) y `PascalCase` para modelos. Las etiquetas que ve el usuario siguen en español mediante `verbose_name` y las etiquetas de choices. Las carpetas de las apps conservan su nombre original (`actividades`, `evidencias`…) para no cambiar rutas ni permisos.

`core` no depende de ninguna otra app. Todas las demás dependen de `core` y/o `funcionarios`, sin imports circulares.

## Cómo levantar el proyecto

### 1. Clonar el repositorio

```bash
git clone https://github.com/estebantr93-lab/bak2.git
cd bak2
```

### 2. Crear y activar el entorno virtual

```bash
python3 -m venv .venv
source .venv/bin/activate
```

En Windows: `.venv\Scripts\activate`.

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

```bash
cp .env.example .env
```

Valores documentados en `.env.example`:

```
SECRET_KEY=<generar una propia, ver .env.example>
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DB_ENGINE=django.db.backends.mysql
DB_NAME=sgr
DB_USER=sgr_app
DB_PASSWORD=cambiar-esta-clave
DB_HOST=127.0.0.1
DB_PORT=3306
DB_SSL_CA=
```

### 4.1 Crear la base de datos y su usuario (una sola vez)

Hay que usar un usuario propio de la aplicación, no `root`. Como administrador de MySQL/MariaDB:

```sql
CREATE DATABASE sgr CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'sgr_app'@'%' IDENTIFIED BY 'cambiar-esta-clave';
GRANT ALL PRIVILEGES ON sgr.* TO 'sgr_app'@'%';
-- Solo si se ejecutan los tests: Django crea y borra la base test_sgr.
GRANT ALL PRIVILEGES ON test_sgr.* TO 'sgr_app'@'%';
FLUSH PRIVILEGES;
```

> El archivo `.env` no se versiona (ver `.gitignore`). Cada equipo/computador genera el suyo a partir de la plantilla.

### 5. Aplicar migraciones

```bash
python manage.py check
python manage.py migrate
```

### 6. Cargar datos de demostración (reproducible)

```bash
python manage.py seed_data
```

El comando `seed_data` (definido en `core/management/commands/seed_data.py`) ejecuta, en orden de dependencias, los seeders de `core → funcionarios → medicion → actividades → evidencias → agenda → colaboracion`, creando de forma **idempotente**: 2 delegaciones, 4 cargos, 5 tipos de actividad, 2 períodos relativos a la fecha de la carga (ver abajo), parámetros, metas/ponderaciones/indicadores, 8 actividades (con evidencias y validaciones) repartidas entre ambas delegaciones, 4 compromisos de agenda (con seguimientos) y los usuarios/grupos de prueba. Al finalizar recalcula el estado de cada actividad según sus evidencias e imprime un resumen de conteos y las cuentas de prueba. Las contraseñas solo se muestran si se generaron al azar.

#### Fechas relativas al día de la carga

Para que la demo funcione el día que se presente, los datos se arman alrededor de la fecha en que se ejecuta `seed_data`:

- **Período actual:** desde el primer día de hace 3 meses hasta el último día de dentro de 2 meses (por ejemplo, «jun–nov 2026 (actual)»). Hoy siempre queda dentro, así se pueden registrar actividades.
- **Período cerrado:** los 6 meses anteriores (por ejemplo, «dic 2025–may 2026 (cerrado)»). Llega completamente revisado: no deja evidencias pendientes que nadie podría revisar.
- **Actividades:** entre el inicio del período y hoy (nunca futuras). **Compromisos:** vencen entre 60 días atrás y 120 días adelante, así siempre hay vencidos y por vencer.
- **Metas:** acordes al volumen generado, así el semáforo muestra verdes, ámbar y rojos. Con el tope de 100 %, pocos funcionarios llegan al 100 % y la mayoría queda repartida entre 30 % y 90 %.
- **Evidencias pendientes:** subidas en las últimas 3 semanas, así ninguna aparece esperando meses.
- Si ya existen períodos, `seed_data` los conserva (no crea otros que se solapen), y las metas existentes tampoco se cambian. **Una base cargada antes de estos cambios (la local o la de AWS) conserva el período antiguo, que vence el 30-09, con tope 150 % y metas altas: desde octubre no se podrán registrar actividades.** Antes de la demo, vuelva a armar todo con la fecha de hoy:

```bash
git pull
python manage.py migrate                  # aplica las migraciones nuevas
python manage.py flush --noinput          # vacía la base (usuarios incluidos)
python manage.py seed_data --volumen      # recrea demo y volumen con las fechas de hoy
python manage.py revisar_archivos --borrar-huerfanos   # borra los archivos de la carga anterior
```

#### Datos de volumen (1.000+ registros)

```bash
python manage.py seed_data --volumen
```

Además de la demo, agrega de forma **reproducible** (semilla fija) e **idempotente**, sin duplicar si se vuelve a ejecutar, **más de 1.600 registros de negocio** repartidos **en partes iguales entre ambas delegaciones** (tres de cada cuatro actividades en el período actual):

| Por delegación (aprox.) | Centro | Norte |
| --- | --- | --- |
| Actividades | 254 | 254 |
| Evidencias (con archivo PNG/PDF real) | 206 (54) | 210 (48) |
| Atenciones sociales | 105 | 87 |
| Compromisos | 64 | 65 |
| Funcionarios | 10 | 10 |

- Las cuentas de demostración tienen datos propios. `funcionario_centro` y `funcionario_norte` tienen entre 50 y 60 actividades cada uno, con evidencias y compromisos. Los admins tienen un bloque menor.
- Los funcionarios generados tienen cargos operativos (Atención Ciudadana y Social) y no tienen contraseña utilizable: son datos, no cuentas de acceso.
- Las evidencias aprobadas o rechazadas incluyen su `Validation` hecha por el verificador.
- Para regenerar desde cero solo el volumen (por ejemplo en AWS): `python manage.py seed_data --rehacer-volumen`.
- El código está en `core/volume_data.py`.

> Para reconstruir desde cero: `DROP DATABASE sgr; CREATE DATABASE sgr CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;` y repetir los pasos 5 y 6.

### 7. Levantar el servidor

```bash
python manage.py runserver
```

El proyecto expone estas rutas:

| URL | Contenido |
| --- | --- |
| **http://127.0.0.1:8000/** | Portada pública. El botón **Ingresar al sistema** lleva al login. |
| **http://127.0.0.1:8000/accounts/login/** | Login (`django.contrib.auth.urls`). Tras ingresar redirige al dashboard (o a `?next=`). |
| **http://127.0.0.1:8000/accounts/logout/** | Cierre de sesión (solo `POST`, botón en la barra superior). |
| **http://127.0.0.1:8000/accounts/recuperar/** | Recuperación de contraseña con código temporal de 6 dígitos. |
| **http://127.0.0.1:8000/actividades/**, **/actividades/atenciones/**, **/evidencias/**, **/compromisos/** | CRUD protegidos con exportación a Excel. |
| **http://127.0.0.1:8000/dashboard/** | Dashboard: resumen por funcionario agrupado por rol, acotado a lo que el usuario puede ver. |
| **http://127.0.0.1:8000/admin/** | Django Admin. `/admin/login/` redirige al login propio. |

### Dashboard por rol

Cada rol ve lo que le sirve (banderas `es_funcionario`, `es_verificador` y `es_gestor` en `dashboard/views.py`, con las constantes de rol de `core/admin_utils.py`):

| Rol | Alcance | Qué muestra |
| --- | --- | --- |
| Administrador general (superusuario) | Ambas delegaciones | Avance del equipo: funcionarios, actividades, evidencias por revisar y compromisos vencidos (a hoy); estado de actividades; cumplimiento promedio; resumen por funcionario (con **Ver detalle**) y destacados. |
| Administrador de delegación (grupo `Administradores`) | Solo **su** delegación | Lo mismo que el administrador general, acotado a su delegación. |
| Verificador (grupo `Verificadores`) | Ambas delegaciones | Su cola de trabajo: evidencias por revisar (con enlace a la lista filtrada), espera más larga, revisadas y rechazadas; estado de evidencias; pendientes por delegación; evidencias recibidas por mes. No se le ofrecen enlaces a listas que no puede abrir. |
| Funcionario (grupo `Funcionarios`) | Solo sus datos | Su avance: actividades, actividades sin evidencia, evidencias rechazadas por corregir y compromisos por vencer; su cumplimiento y el **avance por tipo de actividad** que lo explica. |

**Cumplimiento.** Las metas (`Goal`) son por cargo, período y tipo de actividad, con ponderador. Para cada tipo con meta se calcula `aprobadas del tipo / meta`, con el tope del período (`Period.max_cap`, 100 %): nadie supera el 100 % y sobrecumplir un tipo no tapa el incumplimiento de otro, y luego el promedio ponderado (`medicion.services.calcular_cumplimiento_ponderado`). Las actividades de tipos sin meta no cuentan. El cumplimiento de un grupo es el promedio del de sus funcionarios con meta. El semáforo compara con el % esperado a la fecha. Si el período no tiene metas, el dashboard lo dice en vez de mostrar 0 %.

**Cada indicador coincide con su lista.** Los indicadores con enlace abren la lista con los mismos filtros que su conteo (período, «solo los míos», estado, sin evidencia, vencidos o por vencer), y la lista dice qué filtro aplica, por ejemplo «Filtrado: período jun–nov 2026 (actual) · rechazada · solo las mías (3)». Los filtros también sirven escritos a mano: `?period=`, `?status=`, `?mias=1`, `?sin_evidencia=1` (Actividades), `?vencidos=1` y `?por_vencer=1` (Compromisos).

**Qué depende del período.** Actividades, evidencias y cumplimiento son del período elegido. Los compromisos se muestran **a hoy** (vencidos y por vencer en los próximos 7 días), porque no pertenecen a un período.

Diseño (paleta institucional roja/vinotinto/terracota de `static/css/style.css`, clases `.dash-*`): banner con período y rol, 4 indicadores (enlazan a la lista correspondiente cuando el usuario puede verla), dona de estados, anillo con el % de evidencias del período ya revisadas y barras por mes. Parciales: `templates/dashboard/_kpi.html`, `_dona.html` y `_por_mes.html`.

Todo se calcula en `dashboard/services.py` (sin librerías de gráficos). Los números que van en CSS/SVG usan `|unlocalize`, porque en `es-cl` los decimales llevan coma.

**Menú y tema.** La navegación, el selector de tema y **Cerrar sesión** están en el menú hamburguesa de la barra superior (en todos los tamaños de pantalla), con texto oscuro sobre fondo claro para mejor contraste. El tema puede ser **Claro**, **Oscuro** o **Por defecto** (sigue al sistema operativo); usa los modos de color de Bootstrap 5.3 (`data-bs-theme`) y la preferencia se guarda en el navegador (`static/js/tema.js`). Los colores de estado del dashboard tienen una versión propia para el modo oscuro, validada para daltonismo.

**Admin integrado al sistema.** `/admin/` usa la misma barra roja, el mismo menú hamburguesa (enlaces de `templates/includes/menu_navegacion.html`, compartidos con la app), el mismo pie y la misma paleta en tarjetas (`templates/admin/base_site.html` y `core/static/admin/css/custom_admin.css`, sin librerías externas). El tema es uno solo: la app y el admin guardan la preferencia en la misma clave del navegador (`theme`), así que elegir «Oscuro» en uno se respeta en el otro. Los textos nuevos de Django 6.1 que aún no traía traducidos («- Select an option -», «Run», avisos de zona horaria, algunos errores de formulario) están traducidos en `locale/es/` (`LOCALE_PATHS`). Si se editan los `.po`, recompilar con `python manage.py compilemessages` (requiere `sudo apt install gettext`); los `.mo` ya compilados vienen en el repositorio.

**Archivos de evidencias.** La carga de volumen genera imágenes PNG y PDF de una página válidos (`evidencias/archivos.py`). Para revisar la carpeta de archivos:

```bash
python manage.py revisar_archivos                              # informa faltantes, dañados y huérfanos
python manage.py revisar_archivos --reparar --borrar-huerfanos # regenera los de ejemplo y borra los huérfanos
```

`--reparar` solo regenera archivos de ejemplo (código `EVI-VOL-…`); un archivo subido por un usuario nunca se reemplaza, se informa para volver a subirlo. En los listados, una evidencia cuyo archivo ya no está en el servidor muestra «Archivo no disponible» en vez de un enlace roto. Los huérfanos aparecen, por ejemplo, al recrear la base de datos sin vaciar `media/`.

### Autenticación y sesiones (Clase 6)

- Rutas de `django.contrib.auth.urls` en `config/urls.py`; `LOGIN_URL = 'login'`, `LOGIN_REDIRECT_URL = 'dashboard'`, `LOGOUT_REDIRECT_URL = 'login'`.
- Seguridad por capas: `login_required` / `LoginRequiredMixin` (autenticación), `permission_required` / `PermissionRequiredMixin` (autorización) y `filtrar_por_delegacion` en cada QuerySet (scoping). Una cuenta sin rol o sin perfil de delegación recibe **403**.
- `request.session` guarda solo preferencias: el período elegido en el dashboard y la cantidad de filas por página (5/15/30), que aplica a todos los listados.
- Mensajes (`django.contrib.messages`) al ingresar, al cerrar sesión y en cada operación del CRUD.
- El login (`LoginView` con `funcionarios.forms.LoginForm`) rechaza las cuentas sin rol, o sin perfil de delegación, con el mensaje «Su cuenta no tiene un rol asignado». La misma regla (`tiene_acceso_al_sistema`) protege el dashboard. Si la contraseña es incorrecta, el mensaje es genérico: «Usuario o contraseña incorrectos.».
- `MESSAGE_TAGS` asigna la clase `danger` de Bootstrap a `messages.error()`, y `templates/403.html` muestra «Acceso denegado» con el estilo del sitio.
- Cookies: `SESSION_COOKIE_AGE` de 2 horas, `HTTPONLY`, `SAMESITE='Lax'` y `SESSION/CSRF_COOKIE_SECURE` desde `COOKIE_SECURE` en `.env`.

### Recuperación de contraseña (guía autónoma)

Enlace **¿Olvidó su contraseña?** en el login → correo → código de 6 dígitos (`secrets`) → nueva contraseña (`SetPasswordForm`, que usa `set_password()`).
Solo se guarda el **hash** del código (`PasswordResetCode`). El código vence en **120 s**, es de **uso único**, admite **5 intentos** y pedir uno nuevo invalida los anteriores. La respuesta es siempre genérica («Si el correo corresponde…»).
En desarrollo el correo se imprime en la terminal de `runserver`. Django 6.1 reemplaza `EMAIL_BACKEND`/`EMAIL_HOST`/... por `MAILERS`, y definir ambos es un error; por eso `settings.py` lee las mismas variables de `.env` (`EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`) dentro de `MAILERS`. Para usar Mailtrap basta con cambiar esas variables.

Cada usuario puede pedir como máximo `RECUPERACION_MAX_SOLICITUDES_HORA` (5) códigos por hora: cada código trae sus propios intentos, así que sin tope se podría adivinar pidiendo códigos sin fin. Pasado el tope, la respuesta es la misma genérica y no se envía correo.

### Política de contraseñas

`AUTH_PASSWORD_VALIDATORS` exige **mínimo 10 caracteres** (`MinimumLengthValidator`) y **mayúscula, minúscula, número y carácter especial** (`core/validators.py`), además de los validadores de similitud con el usuario y de contraseñas comunes. Se aplica en la recuperación de contraseña, que pide la clave dos veces con `SetPasswordForm`, y en el Admin. Django guarda solo el hash (PBKDF2), nunca el texto plano.

### CRUD protegidos, paginación y Excel (Clase 7 + investigación)

Hay cuatro CRUD completos (crear, listar, editar y eliminar lógicamente) construidos sobre una base común, `core/crud.py`. Cada entidad solo declara su modelo, columnas, formulario (ModelForm) y permisos:

| CRUD | URL | Validaciones de servidor destacadas |
| --- | --- | --- |
| Actividades | `/actividades/` | número único (también contra eliminadas), período cerrado, funcionario de la misma delegación |
| Atenciones sociales | `/actividades/atenciones/` | gestión 1 a 3 (validadores de rango), máximo 3 por actividad, sin duplicados, solo actividades de tipo social |
| Evidencias (con archivo) | `/evidencias/` | archivo obligatorio al crear, 2 MB, extensión y contenido real; solo el verificador cambia el estado |
| Compromisos | `/compromisos/` | título mínimo, vencimiento no pasado, responsable de la misma delegación, "realizado" exige observaciones |

- **Propiedad (rol funcionario):** ve toda su delegación, pero solo modifica lo propio. La regla se declara en el modelo (`owner_field`, `bloqueo_modificacion`) y la aplica una política única (`core/admin_utils.py`) en el CRUD web y en el Django Admin: cambio, borrado, opciones de formularios y autocompletado. Una actividad de un **período cerrado** no se edita ni se elimina (403), y el período es obligatorio en el formulario.
- **Seguridad por capas en cada vista:** `LoginRequiredMixin` (anónimo → login), `PermissionRequiredMixin` (sin permiso → 403) y scoping por delegación en `get_queryset` (un objeto de otra delegación → 404). Ocultar un botón no protege nada; cada vista vuelve a verificar.
- **Modal:** crear y editar usan el mismo ModelForm en un modal de Bootstrap. Si hay errores, la misma plantilla se vuelve a mostrar con el modal abierto. Cada operación conserva su URL (`nueva/`, `<id>/editar/`, `<id>/eliminar/`).
- **Eliminar:** solo por POST con CSRF, previa confirmación con SweetAlert2 (`static/js/confirmar.js`). El resultado es un **borrado lógico**.
- **Paginación:** 5, 15 o 30 registros por página. La elección se guarda en `request.session['page_size']` y aplica a todos los listados. Los valores no permitidos se ignoran.
- **Exportar a Excel:** el botón "Exportar Excel" descarga un `.xlsx` generado con **openpyxl** (`CrudExportView`), con encabezados y los datos del **mismo QuerySet del listado**. Por eso respeta permisos, scoping por delegación y borrado lógico. El archivo se arma en memoria: `Workbook()` → `hoja.append(fila)` → `libro.save(response)`.

### Revisión de evidencias y estado de la actividad

- Aprobar o rechazar una evidencia pasa **siempre** por `registrar_revision()` (`evidencias/services.py`): formulario web del verificador, acción masiva, formulario de cambio y alta de `Validation` en el Admin. Esa función guarda el estado, asigna el revisor, crea la `Validation` y deja una traza en `AuditLog`. Una `Validation` ya registrada no se edita.
- **Regla del estado de la actividad:** una actividad queda **aprobada** si tiene al menos una evidencia aprobada; **pendiente** si alguna evidencia espera revisión (por ejemplo, la corrección de una rechazada) o si no tiene evidencias; y **rechazada** solo si todas sus evidencias fueron rechazadas. Así una actividad rechazada se recupera cuando el funcionario sube una evidencia corregida y el verificador la aprueba. Se recalcula sola (señal `post_save` de `Evidence`) al revisar, agregar, eliminar o restaurar una evidencia, y por eso el dashboard avanza con cada aprobación.
- **Período cerrado:** se declara una sola vez por modelo con `bloqueo_modificacion`. La actividad y todo lo que depende de ella (evidencias, gestiones y validaciones) quedan congelados en la web y en el Admin, también para el superusuario. Las listas de los formularios no ofrecen actividades cerradas.
- **Lo eliminado lo sigue viendo el administrador general:** cuando un administrador de delegación elimina una actividad, evidencia, gestión o compromiso (borrado lógico), deja de verlo él y su delegación, pero el superadmin lo sigue viendo en el Admin: columna «Registro» (activo o «Eliminado el …»), filtro «estado del registro» (activos, eliminados o todos) y ficha en solo lectura, con sus archivos. Además puede **restaurarlo** con la acción «Restaurar los registros eliminados seleccionados», que recupera también lo que se eliminó junto con él. Cada eliminación y restauración queda en la traza de auditoría con el usuario y la fecha.
- **Actividad aprobada:** el funcionario ya no la modifica, ni le agrega evidencias, ni edita sus gestiones sociales; un administrador sí. Se declara en el modelo con `bloqueo_funcionario` y la aplica la misma política única (`core/admin_utils.modificables`), en la web y en el Admin.
- **Fecha de la actividad:** debe estar dentro de su período y no puede ser futura (se registran actividades ya realizadas).
- **Revisión de evidencias:** rechazar exige indicar el motivo, para que el funcionario sepa qué corregir. El verificador solo cambia estado y resultado: no reasigna la evidencia a otra actividad ni reemplaza el archivo. El estado de validación de la actividad es de solo lectura también en el Admin, porque se deriva de las evidencias.
- **Archivos en el Admin:** el formulario de Evidencias y la evidencia en línea dentro de una actividad validan tipo, tamaño y contenido igual que la web (antes el Admin aceptaba cualquier archivo). Una imagen que declara millones de píxeles se rechaza en vez de agotar la memoria.
- **Seguimiento de compromisos:** registrar un seguimiento cambia el compromiso al «estado nuevo» indicado; si queda realizado sin observaciones, la descripción del seguimiento se usa como tales.
- **Funcionario desactivado** (`Employee.is_active=False`): no puede ingresar, aunque su usuario siga activo, y una sesión ya abierta recibe 403.
- **Metas de un período cerrado:** no se modifican, porque cambiarían el cumplimiento histórico.
- **Traza de auditoría:** en el Admin es de solo lectura (no se crea, edita ni borra a mano).

### Fechas de auditoría y traza de cambios (`BaseModel`)

Como pide la Clase 2 de la Unidad 2, los campos de auditoría están centralizados en modelos abstractos de `core/models.py` (no crean tabla propia):

| Modelo base | Campos | Lo heredan |
| --- | --- | --- |
| `TimeStampedModel` | `created_at` (`auto_now_add`), `updated_at` (`auto_now`) | Tablas maestras: `Delegation`, `Position`, `ActivityType`, `Period`, `Parameter`, `Employee`, `Goal`, `Weighting`, `Indicator` |
| `BaseModel` (hereda de `TimeStampedModel`) | + `deleted_at` y el borrado lógico | Entidades operacionales: `Activity`, `SocialCase`, `Evidence`, `Validation`, `Commitment`, `CommitmentFollowUp` |

Las tablas maestras no tienen borrado lógico: se desactivan con `is_active` y están protegidas con `on_delete=PROTECT` (un borrado lógico se saltaría esa protección).

- **Las fechas dicen cuándo; la traza dice quién y qué.** `updated_at` no sabe quién editó, por eso cada creación y modificación también queda en `AuditLog` con el usuario y los valores anteriores y nuevos (`changes = {campo: [antes, después]}`), registrados en los dos lugares por donde se escribe: el CRUD web (`CrudFormView.form_valid`, `core/crud.py`) y el Admin (`ScopedModelAdmin.save_model` / `save_formset` y `AuditarCambiosAdmin`, `core/admin_utils.py`). El único punto de entrada es `registrar_en_auditoria()`.
- `save(update_fields=[...])` agrega `updated_at` automáticamente (lo hace `TimeStampedModel.save`). `QuerySet.update()` no aplica `auto_now`, por eso las tres actualizaciones masivas del proyecto fijan `updated_at` a mano.
- En el Admin, `created_at` y `updated_at` se ven en la ficha de cada registro en solo lectura.
- Las migraciones `00xx_fechas_de_auditoria` asignan a los registros existentes la fecha de la migración.

### Borrado lógico (`deleted_at`)

`Activity`, `SocialCase`, `Evidence`, `Validation`, `Commitment` y `CommitmentFollowUp` heredan de `core.models.BaseModel` (los managers están en `core/soft_delete.py`):

- `delete()` (desde las vistas, el Admin o un QuerySet) **no borra la fila**: marca `deleted_at` y propaga la marca a los hijos (por ejemplo, una actividad a sus evidencias y atenciones).
- `Modelo.objects` devuelve solo registros activos y es el que usan listados, dashboard, Admin y exportaciones. `Modelo.all_objects` ve también los eliminados. Es el manager por defecto para que Django siga detectando valores únicos ocupados por registros eliminados, en vez de fallar con un error 500.
- Las llaves foráneas usan `limit_choices_to={'deleted_at__isnull': True}`, así los formularios no ofrecen registros eliminados.
- `restore()` recupera un registro; `hard_delete()` lo borra físicamente (no se usa en el flujo normal).

### Archivos y confirmaciones (Clase 8)

La carga (`enctype="multipart/form-data"`) valida el tamaño (máximo 2 MB), la extensión (JPG, PNG o PDF) y el **contenido real**: `Image.open().verify()` de Pillow para imágenes y la firma `%PDF-` para PDF. El nombre enviado se descarta y se guarda con un nombre UUID en `media/evidencias/AAAA/MM/`.
Al reemplazar el archivo de una evidencia, el anterior se borra (`evidencias/signals.py`). Al eliminarla, el borrado es lógico y el archivo se conserva; solo `hard_delete()` lo borra del disco.
SweetAlert2 (`static/js/confirmar.js`) pide confirmación antes de eliminar. La librería (v11.26.25, licencia MIT) se sirve desde `static/vendor/sweetalert2/`, así que la demo no depende de un CDN; si aun así no cargara, se usa la confirmación nativa del navegador y nunca se elimina sin preguntar. Es solo una ayuda visual: Django sigue exigiendo POST, CSRF, login y permisos.

## Despliegue en AWS Academy (EC2 + nginx + gunicorn)

Arquitectura: **nginx** (puerto 80) sirve `/static/` y `/media/` y reenvía el resto a **gunicorn** por un socket Unix. **systemd** mantiene gunicorn en ejecución. La base de datos es **RDS** (MySQL 8.4 / MariaDB 10.11 o superior) o **MariaDB 10.11 en la misma EC2**. Los archivos están en `deploy/`.

> ⚠️ Django 6.1 exige **Python 3.12+** y **MySQL 8.4+ / MariaDB 10.11+**. El script sirve para **Amazon Linux 2023** (instala `python3.12` y `mariadb1011-server`, porque su `python3` es la 3.9) y para **Ubuntu Server 24.04** (trae Python 3.12 y MariaDB 10.11). Detecta el sistema solo (`dnf` o `apt`) y usa el usuario de la instancia (`ec2-user` o `ubuntu`) y el grupo de nginx (`nginx` o `www-data`). Si el Learner Lab no ofrece esas versiones en RDS, use la opción `--db-local`.

1. **Learner Lab → AWS Console → EC2 → Launch instance:** **Amazon Linux 2023** (o Ubuntu Server 24.04 LTS), `t3.small` (o `t2.small`) y el key pair `vockey`.
   *Security group:* entrada **22** (solo su IP) y **80** (0.0.0.0/0). Si usa RDS, el security group de RDS debe permitir **3306 solo desde el security group de la EC2**.
2. Conectarse (`ssh -i labsuser.pem ec2-user@<IP-publica>` en Amazon Linux, `ubuntu@<IP-publica>` en Ubuntu) y ejecutar:
   ```bash
   curl -O https://raw.githubusercontent.com/<usuario>/<repo>/<rama>/deploy/setup_ec2.sh
   bash setup_ec2.sh https://github.com/<usuario>/<repo>.git <rama> --db-local   # o sin --db-local para RDS
   ```
   El script instala los paquetes, clona en `/srv/sgr` y crea el entorno virtual. También genera un `.env` de producción con `SECRET_KEY` aleatoria, `DEBUG=False` y la IP en `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS`. Después ejecuta `migrate`, `collectstatic` y `seed_data --volumen`, y deja gunicorn y nginx activos.
   Con RDS, la primera ejecución se detiene para que complete `DB_HOST`, `DB_USER` y `DB_PASSWORD` en `/srv/sgr/.env`; luego se vuelve a ejecutar.
3. **Contraseñas de demo:** páselas al script como variable de entorno: `DEMO_PASSWORD='<clave nueva>' bash setup_ec2.sh ...`. El script la guarda en `/srv/sgr/.env`. Si no la pasa, `seed_data` genera contraseñas aleatorias y las muestra **una sola vez** en la salida: anótelas. No reutilice contraseñas antiguas del historial de Git.
4. **Correo de recuperación:** con el backend de consola, el código aparece en `sudo journalctl -u gunicorn-sgr -f`. Para recibirlo por correo, configure SMTP (por ejemplo Mailtrap) con `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend` y `EMAIL_HOST`/`EMAIL_PORT`/`EMAIL_HOST_USER`/`EMAIL_HOST_PASSWORD`, y luego `sudo systemctl restart gunicorn-sgr`.

**Actualizar tras un nuevo push:**
```bash
cd /srv/sgr && git pull && .venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py migrate && .venv/bin/python manage.py collectstatic --noinput
sudo systemctl restart gunicorn-sgr
```

**Antes de la revisión, volver a cargar los datos con la fecha del día** (una base cargada antes conserva sus períodos y metas, ver «Fechas relativas al día de la carga»):
```bash
cd /srv/sgr
.venv/bin/python manage.py flush --noinput
.venv/bin/python manage.py seed_data --volumen
.venv/bin/python manage.py revisar_archivos --borrar-huerfanos
sudo systemctl restart gunicorn-sgr
```

**Learner Lab:** la sesión se apaga a las 4 horas y, al reiniciarse, la EC2 puede cambiar de IP pública. Actualice `ALLOWED_HOSTS` y `CSRF_TRUSTED_ORIGINS` en `.env` y reinicie gunicorn, o asocie una Elastic IP. Antes de la revisión, inicie el lab y verifique la URL.

**Si usa RDS:** en el *parameter group*, `character_set_server = utf8mb4` y `collation_server = utf8mb4_unicode_ci`. Para conexión cifrada, descargue `global-bundle.pem` de AWS y apunte `DB_SSL_CA` a esa ruta. Con HTTPS, active `COOKIE_SECURE=True` y `BEHIND_HTTPS_PROXY=True`.

**Diagnóstico:** `sudo systemctl status gunicorn-sgr`, `sudo journalctl -u gunicorn-sgr -n 50`, `sudo nginx -t` y `sudo tail /var/log/nginx/error.log`.

## Cuentas de prueba

`seed_data` crea estas cuentas de demostración. **Las contraseñas no están en el repositorio**: se definen en el `.env` con `DEMO_PASSWORD` (común a todas) o `DEMO_PASSWORD_<USUARIO>` (por ejemplo `DEMO_PASSWORD_ADMIN_CENTRO`). Si el `.env` no las define, `seed_data` genera contraseñas aleatorias y las muestra **una sola vez** en la terminal. Las contraseñas se entregan al docente en la demostración.

| Usuario | Rol / grupo | Alcance |
| --- | --- | --- |
| `admin_sgr` | Administrador general (superusuario) | Acceso total a todas las delegaciones y modelos |
| `admin_centro` | Administrador de delegación — grupo `Administradores` (Centro) | Gestiona actividades, evidencias, compromisos y funcionarios **solo de Centro**; no ve nada de Norte ni administra usuarios |
| `admin_norte` | Administrador de delegación — grupo `Administradores` (Norte) | Igual que el anterior, **solo Norte** |
| `funcionario_centro` | Funcionario — grupo `Funcionarios` (Centro) | Ve las actividades de **Centro**, pero solo registra y edita las **propias** (las ajenas dan 403); no puede eliminar |
| `funcionario_norte` | Funcionario — grupo `Funcionarios` (Norte) | Igual, solo **Norte** |
| `verificador_leia` | Verificador — grupo `Verificadores` | Ve evidencias de todas las delegaciones y las aprueba |

## Comandos de verificación

```bash
python manage.py check                      # configuración
python manage.py makemigrations --check     # modelos y migraciones sincronizados
python manage.py migrate                    # aplica migraciones
python manage.py seed_data --volumen        # demo + 1.600 registros (idempotente)
python manage.py revisar_archivos           # archivos de evidencias faltantes, dañados o huérfanos
python manage.py test                       # pruebas automáticas
python manage.py shell < scripts/verificacion_e2e.py  # recorre todos los puntos pedidos como cada rol (no deja cambios)
python manage.py runserver                  # servidor de desarrollo
```

## Guion de demostración (según la rúbrica)

| # | Criterio | Qué mostrar |
| --- | --- | --- |
| 1 | Modelo, Admin y nomenclatura | Admin con `admin_sgr`: maestras y operacionales, tablas en inglés (`SHOW TABLES`), inline de evidencias y acción "Aprobar evidencias seleccionadas" |
| 2 | Autenticación y recuperación | Login y logout; "¿Olvidó su contraseña?" → código de 6 dígitos (en la terminal o en Mailtrap) → nueva clave → reusar el código falla |
| 3 | Seguridad de contraseña | Intentar `debil123` o una clave sin símbolo: se rechaza; debe coincidir en los dos campos |
| 4 | Usuarios, permisos y scoping | `admin_centro` y `admin_norte` ven solo su delegación; `funcionario_centro` no tiene "Eliminar" y recibe 403 si fuerza la URL; `verificador_leia` recibe 403 en Compromisos |
| 5 | CRUD y validaciones | Crear y editar en el modal: número duplicado, período cerrado, gestión 4, vencimiento en el pasado, "realizado" sin observaciones |
| 6 | Archivos | Subir PNG/PDF válido; rechazo de `.exe`, PNG falso y archivo de más de 2 MB; miniatura en el listado |
| 7 | SweetAlert2 + borrado lógico | Eliminar con confirmación; el registro desaparece del listado, pero sigue en la base con `deleted_at` |
| 8 | Paginación y sesión | Elegir 5 → navegar a otro listado → se mantiene; `?page_size=999` se ignora |
| 9 | Excel | "Exportar Excel" como `admin_centro`: solo Centro, sin eliminados |
| 10 | 1.000 datos | `seed_data --volumen` y el total que muestra; la paginación en Actividades |
| 11 | Despliegue | Todo lo anterior desde la URL pública de AWS |

## Flujo de trabajo con Git

- `main` contiene solo el primer push de inicialización. El desarrollo se hace en ramas `feature/*` (por ejemplo `feature/soft-delete`, `feature/crud-excel-paginacion` o `feature/deploy-aws`), que se integran con `git merge --no-ff` para que el historial muestre cada integración, y luego se llevan a `main` mediante Pull Request.
- `.env`, entornos virtuales, `media/`, `staticfiles/` y la base de datos no se versionan (`.gitignore`). La plantilla de configuración es `.env.example`.

### Reglas de negocio de la guía (RN-001 a RN-013)

| Regla | Estado | Dónde |
| --- | --- | --- |
| RN-001 Ponderadores de un cargo y período suman 100 % | Cumple. Si no suman 100, el dashboard no calcula el cumplimiento de ese cargo y lo avisa; el Admin de Metas muestra la suma por cargo y advierte al guardar | `medicion/services.py` (`suma_ponderadores`), `dashboard/services.py`, `medicion/admin.py` |
| RN-002 Meta mayor que cero | Cumple | `medicion/models.py` (validación de `Goal`) |
| RN-003 Avance = actividades válidas del período | Cumple (solo actividades aprobadas del período) | `dashboard/services.py` |
| RN-004 % cumplimiento = avance / meta × 100 | Cumple | `medicion/services.py` (`calcular_cumplimiento_ponderado`) |
| RN-005 Ponderado con tope | Cumple, tope configurable por período (`Period.max_cap`), fijado en **100 %** | `core/models.py`, `medicion/services.py` |
| RN-006 Umbral colectivo configurable | Cumple (`Period.min_threshold`, 80 %); el dashboard dice si el grupo lo alcanza | `core/models.py`, `templates/dashboard/index.html` |
| RN-007 Meta esperada al día | Cumple (días transcurridos desde el inicio / días del período) | `medicion/services.py` |
| RN-008 Semáforo verde / ámbar (≥ 60 % de lo esperado) / rojo | Cumple | `medicion/services.py` (`calcular_semaforo`) |
| RN-009 Solo validación aprobada suma; rechazada o anulada no | Cumple | `evidencias/services.py` (`estado_segun_evidencias`) |
| RN-010 Código de evidencia único e inmutable | Cumple: lo genera el sistema (`EV-AAAAMM-XXXXXXXX`) y no se puede cambiar | `actividades/models.py` (`generar_codigo_evidencia`, `clean`) |
| RN-011 Felicitaciones, reclamos y ajustes parametrizables | **Pendiente a propósito**: la guía pide no fijar valores hasta la definición oficial. Los parámetros (`Parameter`) ya existen para cargarlos | `core/models.py` |
| RN-012 Hasta 3 gestiones por atención, con fecha y resultado | Cumple (gestión 1 a 3, fecha no futura ni anterior a la actividad, resultado) | `actividades/models.py` (`SocialCase`) |
| RN-013 Período cerrado no se modifica salvo reapertura auditada | Cumple: bloquea actividades, evidencias y metas; cerrar, reabrir y cambiar configuración queda en la auditoría | `core/admin_utils.py` (`AuditarCambiosAdmin`), `core/admin.py` |

Las pruebas de cada regla están en `core/tests_reglas_negocio.py` (`ReglasDeLaGuiaTests`).

**Superadministrador y registros eliminados.** Lo que borra un administrador de delegación (actividad, evidencia, etc.) desaparece para él, pero el superadministrador lo sigue viendo en el Admin (columna «Estado», filtro «Eliminados», solo lectura) y puede restaurarlo con la acción «Restaurar». Ambas acciones quedan en la auditoría. Un registro cuyo padre sigue eliminado (una evidencia, gestión o seguimiento de una actividad o compromiso eliminado) no se restaura: el Admin avisa «Restaure primero…», porque quedaría activo colgando de algo que nadie ve (`BaseModel.padre_eliminado` en `core/models.py`).

## Dónde está cada requisito en el código

| Requisito | Archivos |
| --- | --- |
| Conexión a BD por variables de entorno | `config/settings.py` (`DATABASES`), `.env.example` |
| Modelos (inglés, `db_table`) y Admin | `*/models.py`, `*/admin.py`, `core/admin_utils.py` (`ScopedModelAdmin`) |
| Fechas de auditoría y borrado lógico | `core/models.py` (`TimeStampedModel`, `BaseModel`), `core/soft_delete.py` (managers `objects` / `all_objects`) |
| Traza con valores anteriores y nuevos | `core/admin_utils.py` (`registrar_en_auditoria`, `cambios_del_formulario`), `core/crud.py` (`CrudFormView.form_valid`), `colaboracion/models.py` (`AuditLog.changes`) |
| Login, logout y rechazo de cuentas sin rol | `config/urls.py`, `funcionarios/forms.py` (`LoginForm`), `templates/registration/login.html` |
| Recuperación con código de 6 dígitos | `funcionarios/recuperacion.py`, `funcionarios/views.py`, modelo `PasswordResetCode` |
| Política de contraseñas | `config/settings.py` (`AUTH_PASSWORD_VALIDATORS`), `core/validators.py` |
| Roles, grupos y permisos | `funcionarios/security.py`, `core/admin_utils.py` (`get_rol`, `filtrar_por_delegacion`) |
| Quién puede modificar qué (web y Admin) | `owner_field` y `bloqueo_modificacion` en cada modelo; política única `puede_modificar` / `modificables` / `excluir_bloqueados` en `core/admin_utils.py` |
| Revisión de evidencias y estado de la actividad | `evidencias/services.py` (`registrar_revision`, `estado_segun_evidencias`), `evidencias/signals.py` |
| CRUD, modal, paginación en sesión | `core/crud.py`, `*/views.py`, `*/forms.py`, `templates/crud/list.html` |
| Archivos e imágenes | `evidencias/forms.py` (`clean_file`), `evidencias/models.py` (`ruta_evidencia`), `evidencias/signals.py` |
| SweetAlert2 | `static/js/confirmar.js`, `static/vendor/sweetalert2/`, `templates/base.html` |
| Excel | `reportes/services.py` (`respuesta_xlsx`), `core/crud.py` (`CrudExportView`) |
| Datos de volumen | `core/volume_data.py`, `core/management/commands/seed_data.py` |
| Dashboard por rol | `dashboard/views.py`, `dashboard/services.py` |
| Despliegue | `deploy/setup_ec2.sh`, `deploy/gunicorn-sgr.service`, `deploy/nginx-sgr.conf` |
