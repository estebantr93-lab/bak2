# Sistema de Gestión de Resultados (SGR)

Proyecto integrado académico (INACAP) correspondiente al caso de las delegaciones municipales de la Ilustre Municipalidad de La Serena.

## Descripción

El **Sistema de Gestión de Resultados (SGR)** es una aplicación web que centraliza el registro, seguimiento, verificación y medición de la gestión de funcionarios y delegaciones, generando indicadores individuales y colectivos que apoyan el control operativo y la toma de decisiones.

Esta entrega corresponde a la **Evaluación Sumativa II — "Taller: Aplicación web con Django Admin"**: aplicación Django con base de datos configurada mediante variables de entorno y un Django Admin funcional, personalizado y protegido según la problemática municipal.

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
├── reportes/        # Servicios de exportación (sin modelos ni vistas propias todavía)
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
git clone https://github.com/ChristianInacapBarrera/Proyecto_Integrado_SGR.git
cd Proyecto_Integrado_SGR
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

### 4.2 Despliegue en AWS (Amazon RDS)

- Crear la instancia RDS con motor **MySQL 8.4** o **MariaDB 10.11 / 11.4**. Django 6.1 rechaza MySQL 8.0 y MariaDB 10.6.
- En el *parameter group* de RDS: `character_set_server = utf8mb4` y `collation_server = utf8mb4_unicode_ci`.
- `DB_HOST` es el *endpoint* de RDS. El *security group* de RDS debe permitir el puerto 3306 **solo** desde el servidor de la aplicación (EC2 o Elastic Beanstalk), nunca desde `0.0.0.0/0`.
- TLS: descargar `global-bundle.pem` desde la documentación de AWS RDS y apuntar `DB_SSL_CA` a esa ruta.
- En producción: `DEBUG=False`, `COOKIE_SECURE=True` (con HTTPS), `ALLOWED_HOSTS` con el dominio real y un `SECRET_KEY` propio. Las credenciales van en variables de entorno o en AWS Secrets Manager, nunca en el repositorio.

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

- **Seguridad por capas en cada vista:** `LoginRequiredMixin` (anónimo → login), `PermissionRequiredMixin` (sin permiso → 403) y scoping por delegación en `get_queryset` (un objeto de otra delegación → 404). Ocultar un botón no protege nada; cada vista vuelve a verificar.
- **Modal:** crear y editar usan el mismo ModelForm en un modal de Bootstrap. Si hay errores, la misma plantilla se vuelve a mostrar con el modal abierto. Cada operación conserva su URL (`nueva/`, `<id>/editar/`, `<id>/eliminar/`).
- **Eliminar:** solo por POST con CSRF, previa confirmación con SweetAlert2 (`static/js/confirmar.js`). El resultado es un **borrado lógico**.
- **Paginación:** 5, 15 o 30 registros por página. La elección se guarda en `request.session['page_size']` y aplica a todos los listados. Los valores no permitidos se ignoran.
- **Exportar a Excel:** el botón "Exportar Excel" descarga un `.xlsx` generado con **openpyxl** (`CrudExportView`), con encabezados y los datos del **mismo QuerySet del listado**. Por eso respeta permisos, scoping por delegación y borrado lógico. El archivo se arma en memoria: `Workbook()` → `hoja.append(fila)` → `libro.save(response)`.

### Borrado lógico (`deleted_at`)

`Activity`, `SocialCase`, `Evidence`, `Commitment` y `CommitmentFollowUp` heredan de `core.soft_delete.SoftDeleteModel`:

- `delete()` (desde las vistas, el Admin o un QuerySet) **no borra la fila**: marca `deleted_at` y propaga la marca a los hijos (por ejemplo, una actividad a sus evidencias y atenciones).
- `Modelo.objects` devuelve solo registros activos y es el que usan listados, dashboard, Admin y exportaciones. `Modelo.all_objects` ve también los eliminados. Es el manager por defecto para que Django siga detectando valores únicos ocupados por registros eliminados, en vez de fallar con un error 500.
- Las llaves foráneas usan `limit_choices_to={'deleted_at__isnull': True}`, así los formularios no ofrecen registros eliminados.
- `restore()` recupera un registro; `hard_delete()` lo borra físicamente (no se usa en el flujo normal).

### Archivos y confirmaciones (Clase 8)

La carga (`enctype="multipart/form-data"`) valida el tamaño (máximo 2 MB), la extensión (JPG, PNG o PDF) y el **contenido real**: `Image.open().verify()` de Pillow para imágenes y la firma `%PDF-` para PDF. El nombre enviado se descarta y se guarda con un nombre UUID en `media/evidencias/AAAA/MM/`.
Al reemplazar el archivo de una evidencia, el anterior se borra (`evidencias/signals.py`). Al eliminarla, el borrado es lógico y el archivo se conserva; solo `hard_delete()` lo borra del disco.
SweetAlert2 (`static/js/confirmar.js`) pide confirmación antes de eliminar. Es solo una ayuda visual: Django sigue exigiendo POST, CSRF, login y permisos.

## Cuentas de prueba

`seed_data` crea estas cuentas de demostración. **Las contraseñas no están en el repositorio**: se definen en el `.env` con `DEMO_PASSWORD` (común a todas) o `DEMO_PASSWORD_<USUARIO>` (por ejemplo `DEMO_PASSWORD_ADMIN_CENTRO`). Si el `.env` no las define, `seed_data` genera contraseñas aleatorias y las muestra **una sola vez** en la terminal. Las contraseñas se entregan al docente en la demostración.

| Usuario | Rol / grupo | Alcance |
| --- | --- | --- |
| `admin_sgr` | Administrador general (superusuario) | Acceso total a todas las delegaciones y modelos |
| `admin_centro` | Administrador de delegación — grupo `Administradores` (Centro) | Gestiona actividades, evidencias, compromisos y funcionarios **solo de Centro**; no ve nada de Norte ni administra usuarios |
| `admin_norte` | Administrador de delegación — grupo `Administradores` (Norte) | Igual que el anterior, **solo Norte** |
| `funcionario_centro` | Funcionario — grupo `Funcionarios` (Centro) | Registra y ve actividades de **Centro**; no puede eliminar |
| `funcionario_norte` | Funcionario — grupo `Funcionarios` (Norte) | Igual, solo **Norte** |
| `verificador_leia` | Verificador — grupo `Verificadores` | Ve evidencias de todas las delegaciones y las aprueba |

## Comandos de verificación

Con el entorno activado y desde la raíz del proyecto:

```bash
# Comprueba la configuración del proyecto
python manage.py check

# Aplica las migraciones
python manage.py migrate

# Carga datos de prueba idempotentes
python manage.py seed_data

# Ejecuta las pruebas automáticas (todas las apps)
python manage.py test

# Levanta el servidor de desarrollo
python manage.py runserver
```

## Revisión en vivo (laboratorio)

Secuencia de la demostración:

1. Clonar el repositorio entregado.
2. Crear/activar el entorno virtual e instalar dependencias.
3. Configurar `.env` a partir de `.env.example`.
4. Ejecutar `migrate`.
5. Ejecutar `seed_data`.
6. Ingresar con `admin_sgr` y mostrar el Admin completo: maestras (`Delegation`, `Position`, `ActivityType`, `Period`, `Parameter`), operativas de todas las apps, el Inline de evidencias dentro de una actividad, la acción "Aprobar evidencias seleccionadas" y la validación controlada (por ejemplo, intentar registrar una actividad en el período `2026-Q1 (cerrado)`).
7. Ingresar con `admin_centro` y luego con `admin_norte` para mostrar que cada administrador solo ve su delegación (dashboard y Admin).
8. Cerrar sesión e ingresar con `funcionario_centro` para demostrar que solo ve/edita registros de Delegación Centro (no ve los de Norte).
9. Ejecutar sobre datos cargados: búsqueda, filtros, ordenamiento, Inline, acción personalizada, validación y scoping/rol.

## Flujo de trabajo en 4 pasos

La implementación se realizó en **4 pasos secuenciales** (ver `INSTRUCCIONES_AGENTE_IMPLEMENTACION_SGR.md`):

1. **P1 — Base, configuración y dominio:** 9 apps, `.env`/settings, modelos y migraciones.
2. **P2 — Admin Básico + Admin Pro + Seguridad:** ModelAdmins, Inline/acción/validaciones y scoping por delegación (`core/admin_utils.py`) + grupos/permisos (`funcionarios/security.py`).
3. **P3 — Datos de demostración reproducibles:** seeders por app + comando `seed_data`, cuentas de prueba documentadas arriba.
4. **P4 — Verificación integral, informe y entrega.**

> **Los commits los realiza el humano a cargo.** El agente de IA desarrolla y deja los cambios en el árbol de trabajo, pero no ejecuta operaciones Git de escritura (commit, push, ramas ni PRs).

## Referencias

- `Evaluacion_Sumativa_II_BackEnd_Flex_parte_1.md` — pauta de evaluación.
- `Resumen_Guia_Proyecto_SGR.md` — resumen de la guía del proyecto SGR.
- `INSTRUCCIONES_AGENTE_IMPLEMENTACION_SGR.md` — especificación técnica de implementación.
