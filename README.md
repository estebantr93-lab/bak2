# Sistema de Gestión de Resultados (SGR)

Proyecto integrado académico (INACAP) correspondiente al caso de las delegaciones municipales de la Ilustre Municipalidad de La Serena.

## Descripción

El **Sistema de Gestión de Resultados (SGR)** es una aplicación web que centraliza el registro, seguimiento, verificación y medición de la gestión de funcionarios y delegaciones, generando indicadores individuales y colectivos que apoyan el control operativo y la toma de decisiones.

Esta entrega corresponde a la **Evaluación Sumativa II — "Taller: Aplicación web con Django Admin"**: aplicación Django con base de datos configurada mediante variables de entorno y un Django Admin funcional, personalizado y protegido según la problemática municipal.

> **Importante:** el proyecto se usa únicamente con **datos ficticios**. Está prohibido cargar información real de ciudadanos o funcionarios.

## Stack y dependencias

- **Backend:** Python 3 + Django 6.1.1
- **Base de datos:** SQLite (desarrollo, portable) / PostgreSQL (producción, opcional vía variables de entorno)
- **Variables de entorno:** `python-dotenv`

| Paquete | Versión |
| --- | --- |
| asgiref | 3.12.1 |
| Django | 6.1.1 |
| python-dotenv | 1.2.3 |
| sqlparse | 0.6.0 |
| tzdata | 2026.3 |

## Requisitos previos

- **Git** instalado.
- **Python 3** instalado (entorno de desarrollo verificado con Python 3.12).
- Se documentan comandos para **Linux/macOS (bash/zsh)**; para Windows se usan los equivalentes de `venv`/`activate`.

## Arquitectura modular (apps Django)

Cada módulo del dominio SGR es una app Django independiente:

```
Proyecto_Integrado_SGR/
├── config/          # Proyecto Django (settings, urls, wsgi, asgi) + vista de la página de inicio
├── core/            # Delegacion, Cargo, TipoActividad, Periodo, Parametro + admin_utils (scoping) + seed_data
├── funcionarios/    # Funcionario (perfil), grupos/permisos (security.py)
├── actividades/     # Actividad, AtencionSocial
├── evidencias/      # Evidencia, Validacion + acción "Aprobar evidencias seleccionadas"
├── agenda/          # Compromiso, SeguimientoCompromiso
├── medicion/        # Meta, Ponderacion, Indicador + fórmulas de cálculo (services.py)
├── monitoreo/       # TableroPanel
├── reportes/        # Servicios de exportación (sin modelos propios)
├── colaboracion/    # Comentario, Alerta, TrazaAuditoria
├── templates/       # Plantillas de proyecto: landing.html y override de admin/base_site.html
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
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3
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

> Para reconstruir desde cero: eliminar `db.sqlite3` y repetir los pasos 5 y 6.

### 7. Levantar el servidor

```bash
python manage.py runserver
```

El proyecto expone dos rutas:

| URL | Contenido |
| --- | --- |
| **http://127.0.0.1:8000/** | Portada pública del sistema. Solo identifica al SGR y ofrece el botón **Ingresar al sistema**; no expone datos ni estructura interna. |
| **http://127.0.0.1:8000/admin/** | Django Admin, donde se realiza toda la operación y la demostración de la evaluación. |

## Cuentas de prueba

Cuentas de demostración creadas por `seed_data` (no personales; contraseñas ficticias solo para uso académico):

| Usuario | Contraseña | Rol / grupo | Alcance en el Admin |
| --- | --- | --- | --- |
| `admin_sgr` | `Admin#2026SGR` | Administrador (superusuario) | Acceso total a todas las delegaciones y modelos |
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
7. Cerrar sesión e ingresar con `funcionario_centro` para demostrar que solo ve/edita registros de Delegación Centro (no ve los de Norte).
8. Ejecutar sobre datos cargados: búsqueda, filtros, ordenamiento, Inline, acción personalizada, validación y scoping/rol.

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
