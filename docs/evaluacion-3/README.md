# Evaluación 3: Implementación, pruebas y calidad de software

Rama de trabajo: `feature/evaluacion-3-sprint-pruebas` (sale de `claude/dashboard-delegaciones-permisos-d1zc35`).
Entrega: **jueves 08-10-2026, 23:59**. Grupal (3 integrantes), evaluación individual, 40 % de la asignatura.

El producto es un **informe** en tercera persona (portada, índice, glosario y bibliografía APA) con:

1. Un Sprint del proyecto «Delegaciones Municipales» (este SGR).
2. Un Plan de Pruebas: **[plan-de-pruebas.md](plan-de-pruebas.md)**.
3. La aplicación del Plan de Pruebas y la corrección de lo que falle: **registro de deficiencias** (abajo).

Todas las capturas están en [`capturas/`](capturas/), con el nombre del hallazgo y si son de antes o de después.

## Cómo repetir las pruebas

```bash
python manage.py test                                   # 307 pruebas (unitarias, integración y seguridad)
python manage.py test funcionarios.tests_seguridad_owasp  # solo las de OWASP (18)
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
| D-05 | Usabilidad | En tablet vertical (768 px) las listas de Actividades y Evidencias se desplazaban de lado y los botones Editar/Eliminar quedaban fuera de la vista; en tablet horizontal (1024 px), Actividades también se desplazaba | Hasta 991 px las tablas se muestran como tarjetas (una por registro); entre 992 y 1199 px los botones de acción pasan a una segunda línea | `scripts/pruebas_navegador.js` (CP-U01 a CP-U03) | ✅ Corregida |
| D-06 | A06 Componentes vulnerables | Las dependencias no se revisaban en busca de vulnerabilidades conocidas | Auditoría con `pip-audit`: sin vulnerabilidades conocidas en las 9 dependencias (29-09-2026). Queda como paso antes de cada entrega | `pip-audit -r requirements.txt` | ✅ Verificada |
| D-07 | A03 Inyección (XSS) | `templates/includes/form_campos.html` muestra `help_text` sin escapar (`\|safe`) | Riesgo aceptado: los textos de ayuda salen del código (por ejemplo, la lista de reglas de contraseña de Django, que es HTML) y nunca de datos de usuarios. La CSP (D-03) impide además ejecutar un script inyectado | `test_xss_guardado_se_muestra_escapado` | ⚠️ Aceptado con justificación |
| D-08 | A02 Fallas criptográficas | El despliegue en AWS Academy usa HTTP: las credenciales viajan sin cifrar | La configuración ya admite HTTPS (`COOKIE_SECURE`, `BEHIND_HTTPS_PROXY`); falta un dominio con certificado, que el Learner Lab no entrega | Revisión de configuración | ⏳ Pendiente (fuera del alcance del laboratorio) |
| D-09 | Calidad de las pruebas | **Hallazgo al aplicar las pruebas:** después de D-01, `scripts/verificacion_e2e.py` fallaba (91/93) si alguien había fallado el ingreso en los últimos 15 minutos: la prueba dependía del estado de la base | El script descarta, dentro de su transacción (que se revierte), los intentos previos, y suma 3 verificaciones nuevas: bloqueo, traza con IP y cabecera CSP | `scripts/verificacion_e2e.py` (96/96) | ✅ Corregida |

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
| Regresión general | – | [Batería completa](capturas/03-bateria-completa-despues.png) · [pruebas en navegador 28/28](capturas/04-pruebas-navegador.png) |

La carpeta [`capturas/usabilidad/`](capturas/usabilidad/) tiene además las vistas de PC, tablet y celular
del dashboard y de Actividades, y el [menú en tablet](capturas/usabilidad/usabilidad-despues-tablet-menu.png).

## Rúbrica y dónde está la evidencia

| Criterio | Peso | Evidencia en el proyecto |
| --- | --- | --- |
| Usabilidad y tendencias (UI/UX, accesibilidad, dispositivos) | 10 % | Bootstrap 5.3 adaptable; tablas en tarjetas en celular y tablet (D-05); tema claro, oscuro o del sistema; estados con icono y texto; menú hamburguesa. Pendiente para el informe: texto sobre SaaS, IaaS y cloud (AWS EC2 = IaaS) |
| Normativa de delitos informáticos (Ley 21.459, Ley 19.628) | 15 % | Autenticación robusta (política de contraseñas, límite de intentos D-01), trazabilidad (D-02: quién entró, desde qué IP, qué se le negó), alcance por delegación (cada funcionario ve solo los datos que le corresponden), borrado lógico auditado, secretos fuera del repositorio |
| Buenas prácticas (documentación, versiones, modularidad, código limpio) | 15 % | 10 apps Django, ramas `feature/*` con merge `--no-ff`, README, pruebas junto al código, `pyflakes` sin avisos salvo los tres `import` de `apps.py` que registran receptores de señales a propósito |
| Plan de pruebas (unitarias, integración, aceptación) | 30 % | [plan-de-pruebas.md](plan-de-pruebas.md): 42 casos CP enlazados a 307 pruebas automáticas, 96 verificaciones funcionales y 28 de navegador |
| Cumplimiento OWASP Top 10 | 20 % | Casos CP-S01 a CP-S12 y deficiencias D-01 a D-09 |
| Corrección de deficiencias | 10 % | Registro de deficiencias: 7 corregidas o verificadas, 1 aceptada con justificación y 1 pendiente por el entorno |

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
- `scripts/pruebas_navegador.js`: pruebas de usabilidad y CSP en navegador.

## Pendiente para el informe

1. Definir el Sprint: historias de usuario, criterios de aceptación y tablero.
2. Redactar el informe (tercera persona, portada, índice, glosario, APA) con este registro y las capturas.
3. Ejecutar el guion de aceptación con usuarios reales (sección 7 del plan).
