# Evaluación 3: Implementación, pruebas y calidad de software

Rama de trabajo: `feature/evaluacion-3-sprint-pruebas` (sale de `claude/dashboard-delegaciones-permisos-d1zc35`).
Entrega: **jueves 08-10-2026, 23:59**. Grupal (3 integrantes), evaluación individual, 40 % de la asignatura.

El producto es un **informe** en tercera persona (portada, índice, glosario y bibliografía APA) con:

1. Un Sprint del proyecto «Delegaciones Municipales» (este SGR).
2. Un Plan de Pruebas.
3. La aplicación del Plan de Pruebas y la corrección de lo que falle.

## Rúbrica y dónde está la evidencia en el proyecto

| Criterio | Peso | Qué ya existe | Qué falta |
| --- | --- | --- | --- |
| Usabilidad y tendencias (UI/UX, accesibilidad, dispositivos) | 10 % | Bootstrap 5.3 responsivo; tablas en tarjetas en el celular; tema claro, oscuro o del sistema; colores validados para daltonismo; menú hamburguesa | Medición de accesibilidad (Lighthouse o axe) y capturas en tablet y PC; texto sobre SaaS, IaaS y cloud (AWS EC2 = IaaS) |
| Normativa de delitos informáticos (Ley 21.459, Ley 19.628) | 15 % | Autenticación con política de contraseñas, roles y alcance por delegación, auditoría (`AuditLog`), borrado lógico sin pérdida de datos, sin secretos en el repositorio | Relacionar cada medida con la ley (acceso ilícito, protección de datos personales); registro de ingresos fallidos |
| Buenas prácticas (documentación, versiones, modularidad, código limpio) | 15 % | 10 apps Django, ramas `feature/*` con merge `--no-ff`, README, `pyflakes` sin avisos salvo los dos `import .signals` que registran las señales a propósito | Guía breve de estilo y convenciones para el informe |
| Plan de pruebas (unitarias, integración, aceptación) | 30 % | 289 pruebas automáticas (`python manage.py test`) y 93 verificaciones de punta a punta (`scripts/verificacion_e2e.py`) | Plan formal con casos CP-xx (módulo, datos, resultado esperado, criterio de aceptación) enlazados a esas pruebas; pruebas de aceptación por rol; informe de ejecución |
| Cumplimiento OWASP Top 10 | 20 % | CSRF, ORM sin SQL crudo, autoescape contra XSS, contraseñas con hash, validación real de archivos, control de acceso en el servidor (403), cookies `HttpOnly` | Ver deficiencias preliminares |
| Corrección de deficiencias | 10 % | Historial de correcciones en Git | Registro «deficiencia → corrección → prueba que lo confirma» |

## Deficiencias preliminares (por confirmar con pruebas)

Aparecen al revisar la configuración actual. Cada una debe quedar con su caso de prueba antes y después de corregirla.

| OWASP | Deficiencia | Corrección propuesta |
| --- | --- | --- |
| A07 Fallas de identificación y autenticación | El login no limita los intentos fallidos | Bloqueo temporal por usuario o IP tras N intentos, con prueba |
| A09 Fallas de registro y monitoreo | Los ingresos fallidos no quedan registrados | Registrar en `AuditLog` los ingresos fallidos y los accesos denegados (403) |
| A05 Configuración de seguridad incorrecta | Sin política de seguridad de contenido (CSP) | Middleware de CSP de Django (`django.middleware.csp`) |
| A06 Componentes vulnerables | No se revisan las dependencias | `pip-audit` sobre `requirements.txt` y registrar el resultado |
| A03 Inyección (XSS) | `form_campos.html` muestra `help_text\|safe`; hoy solo trae textos del propio código | Revisar que ningún `help_text` venga de datos de usuario, o quitar `\|safe` |
| A02 Fallas criptográficas | El despliegue en AWS usa HTTP | Documentar HTTPS (certificado) o justificar el alcance académico; HSTS si hay HTTPS |

## Plan de trabajo sugerido

1. Definir el Sprint: historias de usuario elegidas, criterios de aceptación y tablero.
2. Escribir el Plan de Pruebas siguiendo el ejemplo de la guía (objetivo, alcance, tipos, casos CP-xx, criterios de aceptación, roles).
3. Ejecutar las pruebas y registrar los resultados.
4. Corregir las deficiencias en esta rama, con una prueba que las confirme.
5. Redactar el informe con las evidencias (capturas, salidas de las pruebas, commits).
