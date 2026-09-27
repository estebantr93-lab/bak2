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
- Para compilar `mysqlclient` en Linux: `sudo apt install pkg-config libmariadb-dev` (Debian/Ubuntu) o `sudo dnf install pkgconf mariadb-connector-c-devel gcc python3-devel` (Amazon Linux). En Windows y macOS `pip` descarga una rueda precompilada.
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
├── templates/       # landing, base, registration/ (login y recuperación), dashboard/, actividades/, evidencias/
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

El comando `seed_data` (definido en `core/management/commands/seed_data.py`) ejecuta, en orden de dependencias, los seeders de `core → funcionarios → medicion → actividades → evidencias → agenda → colaboracion`, creando de forma **idempotente**: 2 delegaciones, 4 cargos, 5 tipos de actividad, 2 períodos (uno cerrado, uno abierto), parámetros, metas/ponderaciones/indicadores, 8 actividades (con evidencias y validaciones) repartidas entre ambas delegaciones, 4 compromisos de agenda (con seguimientos) y los usuarios/grupos de prueba. Al finalizar imprime un resumen de conteos y las credenciales de demostración.

#### Datos de volumen (1.000+ registros)

```bash
python manage.py seed_data --volumen
```

Además de la demo, agrega de forma **reproducible** (semilla fija) e **idempotente**, sin duplicar si se vuelve a ejecutar, **más de 1.400 registros de negocio** repartidos **en partes iguales entre ambas delegaciones** y entre ambos períodos:

| Por delegación (aprox.) | Centro | Norte |
| --- | --- | --- |
| Actividades | 254 | 254 |
| Evidencias (con archivo PNG/PDF real) | 169 (37) | 179 (48) |
| Atenciones sociales | 83 | 94 |
| Compromisos | 64 | 65 |
| Funcionarios | 10 | 10 |

- Las cuentas de demostración tienen datos propios. `funcionario_centro` y `funcionario_norte` tienen unas 60 actividades cada uno, con evidencias y compromisos. Los admins tienen un bloque menor.
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

Por cada funcionario visible muestra, para el período elegido: actividades (total, aprobadas, pendientes, rechazadas), evidencias pendientes, compromisos abiertos y vencidos, meta del cargo y % de cumplimiento con semáforo (`medicion/services.py`). Los funcionarios se agrupan por delegación y, dentro de ella, por rol, con subtotales.

| Rol | Qué ve en el dashboard |
| --- | --- |
| Administrador general (superusuario) | Ambas delegaciones |
| Administrador de delegación (grupo `Administradores`) | Solo los funcionarios de **su** delegación |
| Verificador (grupo `Verificadores`) | Ambas delegaciones (revisa evidencias de todas) |
| Funcionario (grupo `Funcionarios`) | Solo su propio resumen |

### Autenticación y sesiones (Clase 6)

- Rutas de `django.contrib.auth.urls` en `config/urls.py`; `LOGIN_URL = 'login'`, `LOGIN_REDIRECT_URL = 'dashboard'`, `LOGOUT_REDIRECT_URL = 'login'`.
- Seguridad por capas: `login_required` / `LoginRequiredMixin` (autenticación), `permission_required` / `PermissionRequiredMixin` (autorización) y `filtrar_por_delegacion` en cada QuerySet (scoping). Una cuenta sin rol o sin perfil de delegación recibe **403**.
- `request.session` guarda solo preferencias: el período elegido en el dashboard y la cantidad de filas por página en actividades.
- Mensajes (`django.contrib.messages`) al ingresar, al cerrar sesión y en cada operación del CRUD.
- El login (`LoginView` con `funcionarios.forms.LoginForm`) rechaza las cuentas sin rol, o sin perfil de delegación, con el mensaje «Su cuenta no tiene un rol asignado». La misma regla (`tiene_acceso_al_sistema`) protege el dashboard. Si la contraseña es incorrecta, el mensaje es genérico: «Usuario o contraseña incorrectos.».
- `MESSAGE_TAGS` asigna la clase `danger` de Bootstrap a `messages.error()`, y `templates/403.html` muestra «Acceso denegado» con el estilo del sitio.
- Cookies: `SESSION_COOKIE_AGE` de 2 horas, `HTTPONLY`, `SAMESITE='Lax'` y `SESSION/CSRF_COOKIE_SECURE` desde `COOKIE_SECURE` en `.env`.

### Recuperación de contraseña (guía autónoma)

Enlace **¿Olvidó su contraseña?** en el login → correo → código de 6 dígitos (`secrets`) → nueva contraseña (`SetPasswordForm`, que usa `set_password()`).
Solo se guarda el **hash** del código (`PasswordResetCode`). El código vence en **120 s**, es de **uso único**, admite **5 intentos** y pedir uno nuevo invalida los anteriores. La respuesta es siempre genérica («Si el correo corresponde…»).
En desarrollo el correo se imprime en la terminal de `runserver`. Django 6.1 reemplaza `EMAIL_BACKEND`/`EMAIL_HOST`/... por `MAILERS`, y definir ambos es un error; por eso `settings.py` lee las mismas variables de `.env` (`EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`) dentro de `MAILERS`. Para usar Mailtrap basta con cambiar esas variables.

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

- **Propiedad (rol funcionario):** ve toda su delegación, pero solo modifica lo propio. La regla se declara en el modelo (`owner_field`, `motivo_no_modificable()`) y la aplica una política única (`core/admin_utils.py`) en el CRUD web y en el Django Admin: cambio, borrado, opciones de formularios y autocompletado. Una actividad de un **período cerrado** no se edita ni se elimina (403), y el período es obligatorio en el formulario.
- **Seguridad por capas en cada vista:** `LoginRequiredMixin` (anónimo → login), `PermissionRequiredMixin` (sin permiso → 403) y scoping por delegación en `get_queryset` (un objeto de otra delegación → 404). Ocultar un botón no protege nada; cada vista vuelve a verificar.
- **Modal:** crear y editar usan el mismo ModelForm en un modal de Bootstrap. Si hay errores, la misma plantilla se vuelve a mostrar con el modal abierto. Cada operación conserva su URL (`nueva/`, `<id>/editar/`, `<id>/eliminar/`).
- **Eliminar:** solo por POST con CSRF, previa confirmación con SweetAlert2 (`static/js/confirmar.js`). El resultado es un **borrado lógico**.
- **Paginación:** 5, 15 o 30 registros por página. La elección se guarda en `request.session['page_size']` y aplica a todos los listados. Los valores no permitidos se ignoran.
- **Exportar a Excel:** el botón "Exportar Excel" descarga un `.xlsx` generado con **openpyxl** (`CrudExportView`), con encabezados y los datos del **mismo QuerySet del listado**. Por eso respeta permisos, scoping por delegación y borrado lógico. El archivo se arma en memoria: `Workbook()` → `hoja.append(fila)` → `libro.save(response)`.

### Borrado lógico (`deleted_at`)

`Activity`, `SocialCase`, `Evidence`, `Validation`, `Commitment` y `CommitmentFollowUp` heredan de `core.soft_delete.SoftDeleteModel`:

- `delete()` (desde las vistas, el Admin o un QuerySet) **no borra la fila**: marca `deleted_at` y propaga la marca a los hijos (por ejemplo, una actividad a sus evidencias y atenciones).
- `Modelo.objects` devuelve solo registros activos y es el que usan listados, dashboard, Admin y exportaciones. `Modelo.all_objects` ve también los eliminados. Es el manager por defecto para que Django siga detectando valores únicos ocupados por registros eliminados, en vez de fallar con un error 500.
- Las llaves foráneas usan `limit_choices_to={'deleted_at__isnull': True}`, así los formularios no ofrecen registros eliminados.
- `restore()` recupera un registro; `hard_delete()` lo borra físicamente (no se usa en el flujo normal).

### Archivos y confirmaciones (Clase 8)

La carga (`enctype="multipart/form-data"`) valida el tamaño (máximo 2 MB), la extensión (JPG, PNG o PDF) y el **contenido real**: `Image.open().verify()` de Pillow para imágenes y la firma `%PDF-` para PDF. El nombre enviado se descarta y se guarda con un nombre UUID en `media/evidencias/AAAA/MM/`.
Al reemplazar el archivo de una evidencia, el anterior se borra (`evidencias/signals.py`). Al eliminarla, el borrado es lógico y el archivo se conserva; solo `hard_delete()` lo borra del disco.
SweetAlert2 (`static/js/confirmar.js`) pide confirmación antes de eliminar. Es solo una ayuda visual: Django sigue exigiendo POST, CSRF, login y permisos.

## Despliegue en AWS Academy (EC2 + nginx + gunicorn)

Arquitectura: **nginx** (puerto 80) sirve `/static/` y `/media/` y reenvía el resto a **gunicorn** por un socket Unix. **systemd** mantiene gunicorn en ejecución. La base de datos es **RDS** (MySQL 8.4 / MariaDB 10.11 o superior) o **MariaDB 10.11 en la misma EC2**. Los archivos están en `deploy/`.

> ⚠️ Django 6.1 exige **Python 3.12+** y **MySQL 8.4+ / MariaDB 10.11+**. Ubuntu Server 24.04 trae Python 3.12 y MariaDB 10.11. Si el Learner Lab no ofrece esas versiones en RDS, use la opción `--db-local`.

1. **Learner Lab → AWS Console → EC2 → Launch instance:** Ubuntu Server 24.04 LTS, `t3.small` (o `t2.small`) y el key pair `vockey`.
   *Security group:* entrada **22** (solo su IP) y **80** (0.0.0.0/0). Si usa RDS, el security group de RDS debe permitir **3306 solo desde el security group de la EC2**.
2. Conectarse (`ssh -i labsuser.pem ubuntu@<IP-publica>`) y ejecutar:
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
python manage.py seed_data --volumen        # demo + 1.400 registros (idempotente)
python manage.py test                       # pruebas automáticas
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

## Dónde está cada requisito en el código

| Requisito | Archivos |
| --- | --- |
| Conexión a BD por variables de entorno | `config/settings.py` (`DATABASES`), `.env.example` |
| Modelos (inglés, `db_table`) y Admin | `*/models.py`, `*/admin.py`, `core/admin_utils.py` (`ScopedModelAdmin`) |
| Borrado lógico | `core/soft_delete.py` (`SoftDeleteModel`, managers `objects` / `all_objects`) |
| Login, logout y rechazo de cuentas sin rol | `config/urls.py`, `funcionarios/forms.py` (`LoginForm`), `templates/registration/login.html` |
| Recuperación con código de 6 dígitos | `funcionarios/recuperacion.py`, `funcionarios/views.py`, modelo `PasswordResetCode` |
| Política de contraseñas | `config/settings.py` (`AUTH_PASSWORD_VALIDATORS`), `core/validators.py` |
| Roles, grupos y permisos | `funcionarios/security.py`, `core/admin_utils.py` (`get_rol`, `filtrar_por_delegacion`) |
| Quién puede modificar qué (web y Admin) | `owner_field` y `motivo_no_modificable()` en cada modelo; política única `puede_modificar` / `modificables` en `core/admin_utils.py` |
| CRUD, modal, paginación en sesión | `core/crud.py`, `*/views.py`, `*/forms.py`, `templates/crud/list.html` |
| Archivos e imágenes | `evidencias/forms.py` (`clean_file`), `evidencias/models.py` (`ruta_evidencia`), `evidencias/signals.py` |
| SweetAlert2 | `static/js/confirmar.js`, `templates/base.html` |
| Excel | `reportes/services.py` (`respuesta_xlsx`), `core/crud.py` (`CrudExportView`) |
| Datos de volumen | `core/volume_data.py`, `core/management/commands/seed_data.py` |
| Dashboard por rol | `dashboard/views.py`, `dashboard/services.py` |
| Despliegue | `deploy/setup_ec2.sh`, `deploy/gunicorn-sgr.service`, `deploy/nginx-sgr.conf` |
