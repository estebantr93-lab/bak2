# Evaluación 3: Implementación, pruebas y calidad de software

Rama de trabajo: `feature/evaluacion-3-sprint-pruebas` (sale de `claude/dashboard-delegaciones-permisos-d1zc35` y el 02-10-2026 se le
integraron los últimos cambios del proyecto: listados, filtros, validación y entrega protegida de archivos, diagnóstico de acceso).
Entrega: **jueves 08-10-2026, 23:59**. Grupal (3 integrantes), evaluación individual, 40 % de la asignatura.

El producto es un **informe** en tercera persona (portada, índice, glosario y bibliografía APA) con:

1. Un Sprint del proyecto «Delegaciones Municipales» (este SGR).
2. Un Plan de Pruebas: **[plan-de-pruebas.md](plan-de-pruebas.md)**.
3. La aplicación del Plan de Pruebas y la corrección de lo que falle: **registro de deficiencias** (abajo).

Todas las capturas están en [`capturas/`](capturas/), con el nombre del hallazgo y si son de antes o de después.
**[ERRORES.md](ERRORES.md)** explica cada error, cómo se corrigió y **dónde capturar** el antes y el después de los que aún no tienen captura.

## Cómo repetir las pruebas

```bash
python manage.py test                                   # 367 pruebas (unitarias, integración y seguridad)
python manage.py test funcionarios.tests_seguridad_owasp  # solo las de OWASP (19)
python manage.py test evidencias.tests_validacion_subida  # carga y entrega de archivos (16)
python manage.py shell < scripts/archivos_de_prueba.py  # archivos para capturar D-11 a D-14
python manage.py shell < scripts/verificacion_e2e.py    # 96 verificaciones funcionales de punta a punta
SGR_URL=http://127.0.0.1:8000 SGR_CLAVE='<clave>' node scripts/pruebas_navegador.js   # usabilidad y CSP (28)
pip install pip-audit && pip-audit -r requirements.txt  # dependencias con vulnerabilidades conocidas
```

`scripts/pruebas_navegador.js` necesita Node.js y Playwright (`npm install playwright && npx playwright install chromium`).

## Registro de deficiencias

Cada deficiencia sigue el mismo ciclo: **prueba que la demuestra (falla) → corrección → la misma prueba pasa**.

| ID | OWASP / área | Deficiencia encontrada | Corrección | Prueba que lo confirma | Estado |
| --- | --- | --- | --- | --- | --- |
| D-01 | A07 Identificación y autenticación | El login aceptaba intentos ilimitados: tras 6 claves incorrectas, la correcta entraba sin restricción (fuerza bruta posible) | Bloqueo temporal: 5 fallos por usuario o 20 por IP en 15 minutos. Se revisa antes de comprobar la clave, así la respuesta es igual con la clave correcta o incorrecta | `A07LimiteDeIntentosTests` (6 pruebas) | ✅ Corregida |
| D-02 | A09 Registro y monitoreo | Los ingresos fallidos, los cierres de sesión y los accesos denegados (403) no quedaban registrados | Traza de auditoría con usuario, IP y fecha para `login_exitoso`, `login_fallido`, `login_bloqueado`, `logout` y `acceso_denegado` (nunca la contraseña). Visible para el superadmin en el Admin | `A09RegistroDeEventosTests` (4 pruebas) | ✅ Corregida |
| D-03 | A05 Configuración de seguridad | Las respuestas no traían política de seguridad de contenido (CSP): un script inyectado se ejecutaría | Middleware de CSP de Django 6.1: scripts solo del sitio, de cdn.jsdelivr.net o con el nonce de la respuesta; `object-src 'none'`, `frame-ancestors 'none'`, `form-action 'self'` | `A05PoliticaDeContenidoTests` | ✅ Corregida |
| D-04 | A05 (regresión) | **Hallazgo al aplicar las pruebas:** con la CSP activa, los selectores «Por página» y «Período» dejaron de funcionar, porque usaban `onchange="this.form.submit()"` (JavaScript en línea) | El envío automático pasa a `static/js/autoenvio.js` (`data-autoenviar`); una prueba impide volver a usar `on…=` en las plantillas | `test_ninguna_plantilla_usa_javascript_en_atributos`, `scripts/pruebas_navegador.js` | ✅ Corregida |
| D-05 | Usabilidad | En tablet vertical (768 px) las listas de Actividades y Evidencias se desplazaban de lado y los botones Editar/Eliminar quedaban fuera de la vista; en tablet horizontal (1024 px), Actividades también se desplazaba | Hasta 991 px las tablas se muestran como tarjetas (una por registro). Desde 992 px, con el rediseño de listados, la tabla ancha se desplaza dentro de su caja con la columna de acciones fija (ver D-17) | `scripts/pruebas_navegador.js` (CP-U01 a CP-U03) | ✅ Corregida |
| D-06 | A06 Componentes vulnerables | Las dependencias no se revisaban en busca de vulnerabilidades conocidas | Auditoría con `pip-audit`: sin vulnerabilidades conocidas en las 9 dependencias (29-09-2026). Queda como paso antes de cada entrega | `pip-audit -r requirements.txt` | ✅ Verificada |
| D-07 | A03 Inyección (XSS) | `templates/includes/form_campos.html` muestra `help_text` sin escapar (`\|safe`). Primero se aceptó como riesgo | **Se verificó que el `\|safe` no hace falta:** el único texto con HTML (reglas de contraseña) Django ya lo marca como seguro. Se quitó: esa lista se sigue viendo igual y un texto con `<img onerror>` se muestra escapado | `test_textos_de_ayuda_se_escapan_salvo_el_html_marcado_como_seguro` | ✅ Corregida |
| D-08 | A02 Fallas criptográficas | El despliegue en AWS Academy usa HTTP: las credenciales viajan sin cifrar | La configuración ya admite HTTPS (`COOKIE_SECURE`, `BEHIND_HTTPS_PROXY`); falta un dominio con certificado, que el Learner Lab no entrega | Revisión de configuración | ⏳ Pendiente (fuera del alcance del laboratorio) |
| D-09 | Calidad de las pruebas | **Hallazgo al aplicar las pruebas:** después de D-01, `scripts/verificacion_e2e.py` fallaba (91/93) si alguien había fallado el ingreso en los últimos 15 minutos: la prueba dependía del estado de la base | El script descarta, dentro de su transacción (que se revierte), los intentos previos, y suma 3 verificaciones nuevas: bloqueo, traza con IP y cabecera CSP | `scripts/verificacion_e2e.py` (96/96) | ✅ Corregida |

| D-10 | A01 Control de acceso | nginx publicaba `/media/`: con el enlace de un archivo de evidencia, cualquiera lo descargaba sin iniciar sesión, incluso de otra delegación | Los archivos se entregan por `/archivos/…`, que exige sesión, permiso y delegación (404 fuera del alcance); nginx responde 404 en `/media/`. Se verificó que el visor de PDF funciona con la CSP | `EntregaProtegidaTests` (6 pruebas) | ✅ Corregida |
| D-11 | A04 Diseño inseguro (carga de archivos) | Un archivo de 15 bytes que solo empezaba con `%PDF-` se aceptaba como PDF | Se exige la estructura completa: cabecera, página, `xref` y `%%EOF` | `test_pdf_falso_o_incompleto_se_rechaza` | ✅ Corregida |
| D-12 | A04 / A03 | Se aceptaban PDF con JavaScript, `/Launch` o archivos incrustados | Se rechazan, también disfrazados (`/J#61vaScript`) o dentro de flujos comprimidos; también los PDF cifrados | `test_pdf_con_codigo_o_archivos_incrustados_se_rechaza`, `test_pdf_cifrado_se_rechaza` | ✅ Corregida |
| D-13 | A04 | Un JPEG con extensión `.png` se aceptaba, y una imagen con código agregado al final se guardaba con el código | El formato real debe coincidir con la extensión, y la imagen se vuelve a guardar con Pillow (se descarta lo agregado); tope de 50 megapíxeles | `test_el_contenido_debe_coincidir_con_la_extension`, `test_la_foto_se_guarda_sin_metadatos_ni_contenido_agregado` | ✅ Corregida |
| D-14 | Ley 19.628 (datos personales) | Las fotos se guardaban con su ubicación GPS (metadatos EXIF) | Al volver a guardarlas se descartan los metadatos; la orientación se conserva | `test_la_foto_se_guarda_sin_metadatos_ni_contenido_agregado` | ✅ Corregida |
| D-15 | Usabilidad / soporte | **Caso real del equipo:** una cuenta con grupo pero sin perfil de funcionario no podía entrar y no se sabía por qué | Comando `diagnosticar_acceso <usuario>` que dice qué le falta (grupo, perfil, grupo mal escrito, perfil en otra cuenta) y muestra los últimos rechazos con su motivo. El motivo ya no se muestra en el login (ver D-18) | `funcionarios/tests_diagnostico.py` (5 pruebas) | ✅ Corregida |
| D-16 | Integración | **Hallazgo al integrar** el rediseño de listados: el selector «Por página» quedaba con dos manejadores (`autoenvio.js` y `listado.js`) y el formulario se enviaba dos veces | Queda solo `autoenvio.js` | `scripts/pruebas_navegador.js` y Herramientas de desarrollo → Red | ✅ Corregida |
| D-17 | Calidad de las pruebas | **Hallazgo al aplicar las pruebas:** `pruebas_navegador.js` marcaba OK sin revisar si el ingreso fallaba; no encontraba los botones del diseño nuevo (`.btn-icono`), y exigía que ninguna tabla se desplazara, aunque el diseño nuevo desplaza las tablas anchas con la columna de acciones fija (7 falsas fallas) | Se detiene si no logra ingresar, busca los botones reales y exige que la página no se desplace y que los botones estén a la vista | `scripts/pruebas_navegador.js` (28/28) | ✅ Corregida |
| D-18 | A07 Identificación y autenticación | **Hallazgo del equipo al probar el login:** con la clave correcta, el mensaje revelaba el estado de la cuenta («no tiene un rol asignado», «tiene el rol…, pero no tiene un perfil», «perfil desactivado») y el bloqueo decía «Demasiados intentos fallidos». Así se confirmaba que la clave era correcta y que la cuenta existía | Todo rechazo responde «Usuario o contraseña incorrectos.» (clase 6). El motivo real queda en la traza (`login_rechazado`) y en `diagnosticar_acceso`. Los rechazos con clave correcta también cuentan para el bloqueo | `A07LimiteDeIntentosTests`, `test_usuario_sin_rol_no_puede_iniciar_sesion`, `DiagnosticoDeAccesoTests` | ✅ Corregida |
| D-19 | A07 Gestión de sesiones | **Hallazgo del equipo:** después de ingresar, «atrás» mostraba el login con la sesión abierta y «adelante» volvía al dashboard sin pedir la clave. Las páginas con sesión no traían `Cache-Control`, así que el navegador podía mostrar copias guardadas | Abrir el login con sesión la cierra (queda en la traza) y avisa «Por seguridad, se cerró su sesión». Las páginas con sesión se envían con `no-store, private`, y `sesion.js` recarga las páginas que el navegador restaura de memoria | `SesionAlVolverAtrasTests` (5 pruebas) | ✅ Corregida |

### Evidencia (capturas)

| Hallazgo | Antes | Después |
| --- | --- | --- |
| Resumen de las pruebas OWASP | [01-pruebas-owasp-antes.png](capturas/01-pruebas-owasp-antes.png): de 12 pruebas, 10 fallan (14 fallas al contar cada página por separado); las 2 que pasan comprueban que un usuario legítimo sigue entrando | [02-pruebas-owasp-despues.png](capturas/02-pruebas-owasp-despues.png): 13 de 13 pasan (más 5 de A03, sesión y CSRF que ya pasaban) |
| D-01 Límite de intentos | [Intento 6 fallido](capturas/a07-antes-1-sexto-intento-fallido.png) · [intento 7 con la clave correcta: entra](capturas/a07-antes-2-septimo-intento-clave-correcta.png) | [Intento 6 bloqueado](capturas/a07-despues-1-sexto-intento-fallido.png) · [intento 7 con la clave correcta: sigue bloqueado](capturas/a07-despues-2-septimo-intento-clave-correcta.png) |
| D-02 Registro de accesos | [Bitácora sin accesos](capturas/a09-antes-bitacora-accesos.png) | [Bitácora con fallidos, bloqueos e IP](capturas/a09-despues-bitacora-accesos.png) · [verificador recibe 403](capturas/a09-despues-1-verificador-recibe-403.png) · [el 403 queda registrado](capturas/a09-despues-2-bitacora-acceso-denegado.png) |
| D-03 CSP | [Cabeceras sin CSP](capturas/a05-antes-cabeceras-sin-csp.png) | [Cabeceras con CSP](capturas/a05-despues-cabeceras-con-csp.png) |
| D-04 Regresión por la CSP | [Selectores bloqueados](capturas/a05-regresion-onchange-bloqueado.png) | [Sin violaciones y selectores funcionando](capturas/a05-despues-navegador-sin-violaciones.png) |
| D-05 Usabilidad en tablet | [Medición](capturas/u01-antes-medicion-tablet.png) · [tablet vertical](capturas/usabilidad/usabilidad-antes-tablet-actividades.png) · [tablet horizontal](capturas/usabilidad/usabilidad-antes-tablet-horizontal-actividades.png) | [Medición](capturas/u01-despues-medicion-tablet.png) · [tablet vertical](capturas/usabilidad/usabilidad-despues-tablet-actividades.png) · [tablet horizontal](capturas/usabilidad/usabilidad-despues-tablet-horizontal-actividades.png) |
| D-06 Dependencias | – | [pip-audit sin vulnerabilidades](capturas/a06-pip-audit-dependencias.png) |
| D-09 Verificación reproducible | [91/93 por intentos previos](capturas/d09-verificacion-reproducible.png) | (misma captura: 96/96) |
| D-07, D-10 a D-19 (y nueva captura de D-01) | Ver **[ERRORES.md](ERRORES.md)**: dónde capturar cada uno en la versión anterior | Ver [ERRORES.md](ERRORES.md) |
| Regresión general | – | [Batería completa](capturas/03-bateria-completa-despues.png) · [pruebas en navegador 28/28](capturas/04-pruebas-navegador.png) |

La carpeta [`capturas/usabilidad/`](capturas/usabilidad/) tiene además las vistas de PC, tablet y celular
del dashboard y de Actividades, y el [menú en tablet](capturas/usabilidad/usabilidad-despues-tablet-menu.png).

## Rúbrica y dónde está la evidencia

| Criterio | Peso | Evidencia en el proyecto |
| --- | --- | --- |
| Usabilidad y tendencias (UI/UX, accesibilidad, dispositivos) | 10 % | Bootstrap 5.3 adaptable; tablas en tarjetas en celular y tablet (D-05); listados con pestañas, búsqueda, orden, filtros por módulo y columna de acciones fija; tema claro, oscuro o del sistema; estados con icono y texto; menú hamburguesa. Pendiente para el informe: texto sobre SaaS, IaaS y cloud (AWS EC2 = IaaS) |
| Normativa de delitos informáticos (Ley 21.459, Ley 19.628) | 15 % | Autenticación robusta (política de contraseñas, límite de intentos D-01), trazabilidad (D-02: quién entró, desde qué IP, qué se le negó), archivos con datos personales solo para quien corresponde (D-10) y fotos sin ubicación GPS (D-14), alcance por delegación (cada funcionario ve solo los datos que le corresponden), borrado lógico auditado, secretos fuera del repositorio |
| Buenas prácticas (documentación, versiones, modularidad, código limpio) | 15 % | 10 apps Django, ramas `feature/*` con merge `--no-ff`, README, pruebas junto al código, `pyflakes` sin avisos salvo los tres `import` de `apps.py` que registran receptores de señales a propósito |
| Plan de pruebas (unitarias, integración, aceptación) | 30 % | [plan-de-pruebas.md](plan-de-pruebas.md): 51 casos CP enlazados a 367 pruebas automáticas, 96 verificaciones funcionales y 28 de navegador |
| Cumplimiento OWASP Top 10 | 20 % | Casos CP-S01 a CP-S17 y deficiencias D-01 a D-19 |
| Corrección de deficiencias | 10 % | Registro de deficiencias: 19 en total, 18 corregidas o verificadas y 1 pendiente por el entorno (D-08); [ERRORES.md](ERRORES.md) explica cada una |

### Equivalencia OWASP Top 10 2021 → 2025

Este registro usa la numeración de 2021, la más citada en la bibliografía. En la edición 2025, A05
(configuración) pasa a A02, A06 (componentes vulnerables) se amplía a A03 (cadena de suministro),
A03 (inyección) pasa a A05, A02 (criptografía) pasa a A04, y A07 y A09 conservan su número.

## Archivos de la corrección

- `funcionarios/accesos.py`: registro de accesos (D-02), límite de intentos (D-01) y `handler403`.
- `funcionarios/forms.py`: el formulario de ingreso revisa el bloqueo antes de comprobar la clave.
- `config/settings.py`: `SECURE_CSP` (D-03) y `LOGIN_MAX_INTENTOS`, `LOGIN_MAX_INTENTOS_IP`, `LOGIN_VENTANA_MINUTOS`, `CONFIAR_X_FORWARDED_FOR`.
- `static/js/autoenvio.js`, `templates/crud/list.html`, `templates/dashboard/index.html`: D-04.
- `static/css/style.css`: D-05.
- `funcionarios/tests_seguridad_owasp.py`: 18 pruebas de seguridad.
- `scripts/pruebas_navegador.js`: pruebas de usabilidad y CSP en navegador (D-17).
- `templates/includes/form_campos.html`: D-07.
- `evidencias/archivos.py`, `evidencias/views.py` (`archivo_evidencia`), `config/urls.py`, `deploy/nginx-sgr.conf`: D-10 a D-14.
- `funcionarios/management/commands/diagnosticar_acceso.py`: D-15.
- `funcionarios/forms.py`, `funcionarios/accesos.py`: D-18.
- `funcionarios/views.py` (`IngresoView`), `core/middleware.py`, `static/js/sesion.js`: D-19.
- `static/js/listado.js`: D-16.
- `scripts/archivos_de_prueba.py`: genera los archivos para capturar D-11 a D-14.

## Pendiente para el informe

1. Definir el Sprint: historias de usuario, criterios de aceptación y tablero.
2. Redactar el informe (tercera persona, portada, índice, glosario, APA) con este registro y las capturas.
3. Ejecutar el guion de aceptación con usuarios reales (sección 7 del plan).
