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
├── core/            # Delegacion, Cargo, TipoActividad, Periodo, Parametro + admin_utils (scoping) + seed_data
├── funcionarios/    # Funcionario (perfil), grupos/permisos (security.py), recuperación de contraseña con código
├── actividades/     # Actividad, AtencionSocial + CRUD web protegido (ListView/CreateView/UpdateView/DeleteView + modal)
├── evidencias/      # Evidencia, Validacion + acción "Aprobar evidencias seleccionadas" + carga de archivos validada
├── agenda/          # Compromiso, SeguimientoCompromiso
├── medicion/        # Meta, Ponderacion, Indicador + fórmulas de cálculo (services.py)
├── monitoreo/       # TableroPanel
├── dashboard/       # Dashboard de resumen por funcionario y rol (services.py)
├── reportes/        # Servicios de exportación (sin modelos ni vistas propias todavía)
├── colaboracion/    # Comentario, Alerta, TrazaAuditoria
├── templates/       # landing, base, registration/ (login y recuperación), dashboard/, actividades/, evidencias/
├── static/          # static/css/style.css y static/js/confirmar.js (SweetAlert2)
├── .env.example
├── .gitignore
├── manage.py
├── README.md
└── requirements.txt
```

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
SECRET_KEY=change-this-secret-key-in-your-local-env
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
| **http://127.0.0.1:8000/actividades/** | CRUD protegido de actividades (modal para crear/editar, eliminar por POST). |
| **http://127.0.0.1:8000/evidencias/actividad/&lt;id&gt;/** | Evidencias de una actividad: carga de archivos JPG/PNG/PDF y eliminación. |
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
Solo se guarda el **hash** del código (`CodigoRecuperacion`). El código vence en **120 s**, es de **uso único**, admite **5 intentos** y pedir uno nuevo invalida los anteriores. La respuesta es siempre genérica («Si el correo corresponde…»).
En desarrollo el correo se imprime en la terminal de `runserver`. Django 6.1 reemplaza `EMAIL_BACKEND`/`EMAIL_HOST`/... por `MAILERS`, y definir ambos es un error; por eso `settings.py` lee las mismas variables de `.env` (`EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`) dentro de `MAILERS`. Para usar Mailtrap basta con cambiar esas variables.

### CRUD protegido con modal (Clase 7)

`/actividades/` usa `ListView`, `CreateView`, `UpdateView` y `DeleteView` con `LoginRequiredMixin` y `PermissionRequiredMixin`, y el mismo `ActividadWebForm` (ModelForm) para crear y editar. Ese formulario tiene `clean_numero()`, `clean()` y las validaciones del modelo.
Crear y editar se hacen en un modal de Bootstrap. Si hay errores, la misma plantilla vuelve a mostrarse con el modal abierto. Cada operación conserva su URL (`/actividades/nueva/`, `/<id>/editar/`, `/<id>/eliminar/`).
Eliminar funciona solo por POST y exige `delete_actividad`, que tienen los administradores y no los funcionarios. Ocultar un botón no protege nada: cada vista vuelve a verificar el permiso y el alcance, y responde 403 o 404.

### Archivos y confirmaciones (Clase 8)

La carga (`enctype="multipart/form-data"`) valida el tamaño (máximo 2 MB), la extensión (JPG, PNG o PDF) y el **contenido real**: `Image.open().verify()` de Pillow para imágenes y la firma `%PDF-` para PDF. El nombre enviado se descarta y se guarda con un nombre UUID en `media/evidencias/AAAA/MM/`.
Al eliminar o reemplazar una evidencia, su archivo físico también se borra (señales en `evidencias/signals.py`), para no dejar archivos huérfanos.
SweetAlert2 (`static/js/confirmar.js`) pide confirmación antes de eliminar. Es solo una ayuda visual: Django sigue exigiendo POST, CSRF, login y permisos.

## Cuentas de prueba

Cuentas de demostración creadas por `seed_data` (no personales; contraseñas ficticias solo para uso académico):

| Usuario | Contraseña | Rol / grupo | Alcance en el Admin |
| --- | --- | --- | --- |
| `admin_sgr` | `Admin#2026SGR` | Administrador general (superusuario) | Acceso total a todas las delegaciones y modelos |
| `admin_centro` | `AdminCentro#2026SGR` | Administrador de delegación — grupo `Administradores` (Centro) | Gestiona actividades, evidencias, compromisos y funcionarios **solo de Centro**; no ve nada de Norte ni administra usuarios |
| `admin_norte` | `AdminNorte#2026SGR` | Administrador de delegación — grupo `Administradores` (Norte) | Igual que el anterior, **solo Norte** |
| `funcionario_centro` | `Centro#2026SGR` | Funcionario — grupo `Funcionarios` (Delegación Centro) | Solo ve/edita actividades, evidencias, atenciones sociales, compromisos y seguimientos de **Centro** |
| `funcionario_norte` | `Norte#2026SGR` | Funcionario — grupo `Funcionarios` (Delegación Norte) | Solo ve/edita registros de **Norte** |
| `verificador_leia` | `Verifica#2026SGR` | Verificador — grupo `Verificadores` | Ve evidencias de todas las delegaciones; único rol con permiso para ejecutar la acción "Aprobar evidencias seleccionadas" |

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
6. Ingresar con `admin_sgr` y mostrar el Admin completo: maestras (`Delegacion`, `Cargo`, `TipoActividad`, `Periodo`, `Parametro`), operativas de todas las apps, el Inline de evidencias dentro de una actividad, la acción "Aprobar evidencias seleccionadas" y la validación controlada (por ejemplo, intentar registrar una actividad en el período `2026-Q1 (cerrado)`).
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
