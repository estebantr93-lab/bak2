# Plan de Pruebas: SGR Delegaciones Municipales

Sistema de Gestión de Resultados (SGR) de la Ilustre Municipalidad de La Serena. Sigue la estructura del
ejemplo de la guía de la Evaluación 3. Cada caso indica la prueba automatizada que lo ejecuta, para que
cualquier integrante (o el docente) pueda repetirlo.

## 1. Objetivo

Verificar que el Sprint cumple los requisitos funcionales, no funcionales y de seguridad del SGR: control
de acceso por rol y delegación, registro de actividades con evidencia y validación, cálculo de
cumplimiento, usabilidad en PC, tablet y celular, y conformidad con OWASP Top 10 y la Ley 21.459.

## 2. Alcance

- **Módulos:** ingreso y recuperación de contraseña, actividades y atenciones sociales, evidencias y su
  revisión, compromisos, metas y cumplimiento, dashboard por rol, Admin y exportación a Excel.
- **No funcional:** usabilidad por dispositivo (PC 1366 px, tablet 768/1024 px, celular 390 px),
  seguridad (sesión, permisos, CSRF, CSP, límite de intentos) y validación de datos.
- **Normativa y estándares:** OWASP Top 10 (numeración de la edición 2021; equivalencias con la 2025 en `README.md`), Ley 21.459 de delitos informáticos (acceso indebido),
  Ley 19.628 de protección de datos personales (trazabilidad y alcance de los datos).
- **Fuera de alcance:** carga (rendimiento con muchos usuarios simultáneos) y pruebas de penetración
  externas.

## 3. Tipos de prueba

| Tipo | Qué valida | Cómo se ejecuta |
| --- | --- | --- |
| Unitarias | Funciones y reglas aisladas: cálculo ponderado, semáforo, validaciones de formularios y modelos | `python manage.py test` |
| Integración | Módulos conectados: evidencia → estado de la actividad → cumplimiento → dashboard | `python manage.py test` |
| Funcionales | Cada requisito del caso, de punta a punta por rol | `python manage.py shell < scripts/verificacion_e2e.py` (96 verificaciones) |
| Seguridad (OWASP) | Inyección SQL, XSS, CSRF, sesión, control de acceso, límite de intentos, registro de eventos, CSP, dependencias | `python manage.py test funcionarios.tests_seguridad_owasp`, `pip-audit` |
| Usabilidad | Interfaz sin desplazamiento lateral y con acciones visibles en PC, tablet y celular | `node scripts/pruebas_navegador.js` (28 verificaciones) |
| Aceptación | Validación final por los usuarios de cada rol | Guion de la sección 7, con las cuentas de prueba |

**Entorno:** Ubuntu 24.04 / Amazon Linux 2023, Python 3.12, Django 6.1.1, MariaDB 10.11, Chromium.
Datos: `python manage.py seed_data --volumen` (más de 1.000 registros, fechas relativas al día de la carga).

## 4. Casos de prueba

Resultado: ✅ aprobado en la ejecución del 29-09-2026. La columna «Prueba» es el nombre del test o del
script que ejecuta el caso.

### 4.1 Ingreso, sesión y recuperación

| ID | Módulo | Descripción | Datos de prueba | Resultado esperado | Criterio de aceptación | Prueba | Res. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CP-01 | Login | Ingreso con credenciales válidas | `admin_centro`, clave válida | Entra al dashboard de su delegación | Acceso solo a usuarios registrados con rol | `config/tests_login.py::test_login_correcto_redirige_al_dashboard` | ✅ |
| CP-02 | Login | Ingreso con credenciales inválidas | `admin_centro`, clave incorrecta | «Usuario o contraseña incorrectos.» | No revela cuál dato falló | `test_contrasena_incorrecta_muestra_un_solo_mensaje_generico` | ✅ |
| CP-03 | Login | Cuenta sin rol asignado (D-18) | Usuario sin grupo, clave correcta | «Usuario o contraseña incorrectos.»; el motivo queda en la traza | Sin rol no hay acceso, y la respuesta no revela que la clave era correcta | `test_usuario_sin_rol_no_puede_iniciar_sesion` | ✅ |
| CP-03b | Login | Cuenta con rol, pero sin perfil de funcionario (D-15, D-18) | Usuario en el grupo Funcionarios sin perfil | Mensaje genérico; `diagnosticar_acceso` muestra el motivo («sin perfil de funcionario con delegación») | El administrador sabe qué corregir; el usuario no ve el estado de su cuenta | `funcionarios/tests_diagnostico.py` (5 pruebas) | ✅ |
| CP-04 | Login | Fuerza bruta sobre una cuenta | 5 claves incorrectas y luego la correcta | «Usuario o contraseña incorrectos.» incluso con la clave correcta; queda `login_bloqueado` en la traza | Bloqueo de 15 min; misma respuesta con clave buena o mala | `test_bloquea_la_cuenta_tras_el_maximo_de_intentos_fallidos`, `test_el_bloqueo_no_revela_si_la_clave_era_correcta` | ✅ |
| CP-05 | Login | Una clave probada contra muchas cuentas | 20 usuarios distintos desde la misma IP | La IP queda bloqueada; otra IP no | Bloqueo por IP sin afectar a otras | `test_bloquea_una_ip_que_prueba_muchas_cuentas` | ✅ |
| CP-06 | Login | Fin del bloqueo | Fallos con más de 15 min de antigüedad | La clave correcta vuelve a entrar | El bloqueo es temporal | `test_el_bloqueo_termina_al_pasar_la_ventana` | ✅ |
| CP-07 | Sesión | Cierre de sesión | POST a `/accounts/logout/` | Sesión eliminada; GET no permitido | Logout solo por POST | `test_logout_por_get_no_esta_permitido`, `test_logout_muestra_mensaje_y_limpia_la_sesion` | ✅ |
| CP-07b | Sesión | Atrás después de ingresar (D-19) | Ingresar, recargar, atrás y adelante | «Atrás» cierra la sesión y avisa; «adelante» pide la clave; páginas con sesión `no-store` | Navegar por el historial no reabre una sesión | `SesionAlVolverAtrasTests` (5 pruebas) | ✅ |
| CP-08 | Sesión | Fijación de sesión | Identificador de sesión anterior al login | El identificador cambia al ingresar | Un identificador conocido deja de servir | `test_la_sesion_cambia_de_identificador_al_ingresar` | ✅ |
| CP-09 | Recuperación | Código de 6 dígitos | Correo de un usuario | Llega el código; se guarda solo su hash | Código de un solo uso, vence y admite 5 intentos | `funcionarios/tests_recuperacion.py` (9 pruebas) | ✅ |
| CP-10 | Contraseña | Política de contraseñas | `debil123`, clave sin símbolo | Rechazadas; se pide dos veces | 10+ caracteres, mayúscula, minúscula, número y símbolo | `test_validadores_rechazan_claves_debiles` | ✅ |

### 4.2 Permisos y alcance por delegación

| ID | Módulo | Descripción | Datos de prueba | Resultado esperado | Criterio de aceptación | Prueba | Res. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CP-11 | Permisos | Anónimo en páginas internas | Sin sesión | Redirige al login | Nada interno sin sesión | `test_anonimo_va_al_login_en_todos_los_crud` | ✅ |
| CP-12 | Alcance | Admin de delegación ve solo la suya | `admin_centro` | Listas, Excel y Admin solo con Centro | Ningún dato de otra delegación | `test_listados_respetan_scoping_de_delegacion`, `test_admin_de_delegacion_no_ve_la_otra_ni_en_los_filtros` | ✅ |
| CP-13 | Alcance | Editar un registro de otra delegación | URL con id de Norte | 404 | No se confirma que exista | `test_objeto_de_otra_delegacion_da_404_al_editar_y_eliminar` | ✅ |
| CP-14 | Permisos | Rol sin permiso sobre un módulo | `verificador_leia` en Compromisos | 403 | Tener sesión no da todos los permisos | `test_verificador_sin_permiso_sobre_compromisos_recibe_403` | ✅ |
| CP-15 | Permisos | Funcionario intenta eliminar | `funcionario_centro` | 403, aunque conozca la URL | Solo administradores eliminan | `test_funcionario_no_puede_eliminar_en_ningun_crud` | ✅ |

### 4.3 Actividades, evidencias y cálculo

| ID | Módulo | Descripción | Datos de prueba | Resultado esperado | Criterio de aceptación | Prueba | Res. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CP-16 | Actividades | Registrar una actividad | Datos válidos del período abierto | Se guarda con código de evidencia automático | Código único e inmutable (RN-010) | `test_crear_actividad`, `test_codigo_evidencia_lo_genera_el_sistema_y_es_inmutable` | ✅ |
| CP-17 | Actividades | Período cerrado | Actividad en período cerrado | Rechazada con mensaje | Lo cerrado no se modifica (RN-013) | `test_no_permite_periodo_cerrado` | ✅ |
| CP-18 | Atenciones | Más de 3 gestiones | Gestión n.º 4 | Rechazada | Máximo 3, con fecha y resultado (RN-012) | `test_rango_de_gestion_1_a_3` | ✅ |
| CP-19 | Evidencias | Archivo válido | PNG real | Se guarda con nombre seguro | Solo JPG, PNG o PDF de hasta 2 MB | `test_sube_imagen_valida_con_nombre_seguro` | ✅ |
| CP-20 | Evidencias | Archivo malicioso | `.exe`; PNG falso; archivo de 3 MB | Los tres se rechazan | Se valida el contenido real, no el nombre | `test_rechaza_extension_no_permitida`, `test_rechaza_contenido_falso_con_extension_de_imagen`, `test_rechaza_archivo_mayor_a_2mb` | ✅ |
| CP-21 | Revisión | El verificador aprueba o rechaza | Evidencia pendiente | La actividad cambia de estado; queda la validación | Solo lo aprobado suma (RN-009) | `evidencias/tests_revision.py::ViasDeRevisionTests` (7 pruebas) | ✅ |
| CP-22 | Cálculo | Cumplimiento ponderado con tope | Metas por tipo y actividades aprobadas | Promedio ponderado; nadie pasa de 100 % | RN-001 a RN-008 | `core/tests_reglas_negocio.py::ReglasDeLaGuiaTests` | ✅ |
| CP-23 | Dashboard | Indicadores y listas coinciden | Clic en un indicador | La lista filtrada muestra el mismo total | Mismo filtro en indicador y lista | `test_valor_del_indicador_igual_a_las_filas_de_la_lista` | ✅ |
| CP-24 | Borrado | Eliminar es lógico y auditado | Eliminar una actividad | Desaparece de las listas; el superadmin la ve y restaura | Nada se borra físicamente | `core/tests_soft_delete.py`, `test_lo_que_elimina_un_admin_de_delegacion_lo_sigue_viendo_el_superadmin` | ✅ |
| CP-25 | Excel | Exportación | `admin_centro` | `.xlsx` real con encabezados, solo Centro y sin eliminados | Respeta permisos y alcance | `test_excel_tiene_encabezados_y_solo_datos_del_alcance`, `test_excel_excluye_eliminados` | ✅ |

### 4.4 Seguridad OWASP Top 10

| ID | OWASP | Descripción | Datos de prueba | Resultado esperado | Criterio de aceptación | Prueba | Res. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CP-S01 | A01 Control de acceso | Acceso a datos ajenos | Ver CP-12 a CP-15 | 403/404 | Permiso y alcance verificados en el servidor | (ver CP-12 a CP-15) | ✅ |
| CP-S02 | A03 Inyección SQL | Texto SQL en filtros y búsquedas | `1 OR 1=1`, `' OR '1'='1' --` | Respuesta 200, mismo resultado que sin filtro o 0 coincidencias | Sin error ni datos extra | `test_sql_en_filtros_y_busquedas_no_altera_la_consulta` | ✅ |
| CP-S03 | A03 XSS | Script guardado en una descripción | `<script>alert("xss")</script>` | Se muestra como texto escapado | El script nunca llega sin escapar | `test_xss_guardado_se_muestra_escapado` | ✅ |
| CP-S03b | A03 XSS | Texto de ayuda de un formulario (D-07) | `help_text` con `<img onerror>` | Se muestra escapado; la lista de reglas de contraseña sigue como lista | Ninguna plantilla usa `help_text\|safe` | `test_textos_de_ayuda_se_escapan_salvo_el_html_marcado_como_seguro` | ✅ |
| CP-S04 | A01/CSRF | Envío sin token CSRF | POST a eliminar sin token | 403 y el registro sigue | Toda escritura exige CSRF | `test_post_sin_token_csrf_es_rechazado` | ✅ |
| CP-S05 | A02/A07 Sesión | Cookie de sesión | Respuesta del login | `HttpOnly` y `SameSite=Lax` | JavaScript no lee la sesión | `test_la_cookie_de_sesion_no_es_accesible_desde_javascript`, `test_cookies_de_sesion_seguras` | ✅ |
| CP-S06 | A07 Autenticación | Límite de intentos | Ver CP-04 a CP-06 | Bloqueo temporal | Fuerza bruta impracticable | (ver CP-04 a CP-06) | ✅ |
| CP-S07 | A09 Registro | Ingresos, bloqueos, cierres y 403 | Un fallo, un ingreso, un 403 | Quedan en la traza con usuario, IP y fecha, sin la clave | El superadmin consulta quién hizo qué y cuándo | `A09RegistroDeEventosTests` (4 pruebas) | ✅ |
| CP-S08 | A05 Configuración | Política de seguridad de contenido | Cabeceras de cualquier página | `Content-Security-Policy` estricta, sin `unsafe-inline` en scripts | Un script inyectado no se ejecuta | `test_las_respuestas_traen_una_politica_de_contenido_estricta` | ✅ |
| CP-S09 | A05 Configuración | Scripts propios compatibles con la CSP | Login, dashboard, listas, Admin | Cada `<script>` en línea lleva el nonce; ninguna plantilla usa `onchange=` | La interfaz sigue funcionando con la CSP | `test_los_scripts_en_linea_propios_llevan_el_nonce_de_la_respuesta`, `test_ninguna_plantilla_usa_javascript_en_atributos` | ✅ |
| CP-S10 | A05 Configuración | Sin violaciones de CSP en el navegador | 5 páginas × 4 equipos | 0 violaciones; los selectores automáticos funcionan | Nada legítimo queda bloqueado | `scripts/pruebas_navegador.js` | ✅ |
| CP-S11 | A06 Componentes | Dependencias con vulnerabilidades conocidas | `requirements.txt` | «No known vulnerabilities found» | Sin avisos abiertos | `pip-audit -r requirements.txt` | ✅ |
| CP-S12 | A02/A05 Secretos | Secretos fuera del repositorio | Código fuente | Sin claves de demo ni `SECRET_KEY` | Configuración por `.env` | `test_no_hay_contrasenas_de_demo_en_el_codigo` | ✅ |
| CP-S13 | A01 Control de acceso | Archivo de una evidencia por su enlace (D-10) | Enlace del archivo sin sesión, desde otra delegación y por `/media/` | Login, 404 y 404 | Solo quien puede ver la evidencia descarga su archivo | `EntregaProtegidaTests` (6 pruebas) | ✅ |
| CP-S14 | A04 Carga de archivos | PDF falso (D-11) | `%PDF-1.4 %%EOF`, HTML con extensión `.pdf` | «El archivo no es un PDF válido.» | Solo PDF completos | `test_pdf_falso_o_incompleto_se_rechaza` | ✅ |
| CP-S15 | A04 Carga de archivos | PDF con contenido activo (D-12) | `/JavaScript`, `/Launch`, incrustados, `/J#61vaScript`, flujo comprimido, cifrado | Rechazado con mensaje | Ningún PDF con código llega al servidor | `test_pdf_con_codigo_o_archivos_incrustados_se_rechaza`, `test_pdf_cifrado_se_rechaza` | ✅ |
| CP-S16 | A04 Carga de archivos | Extensión y contenido (D-13) | JPEG como `.png`, PNG con código agregado, imagen de 400 MP | Rechazo; el código agregado no se guarda | El formato real coincide con la extensión | `test_el_contenido_debe_coincidir_con_la_extension`, `test_la_foto_se_guarda_sin_metadatos_ni_contenido_agregado`, `test_imagen_enorme_se_rechaza_sin_procesarla` | ✅ |
| CP-S17 | Ley 19.628 Datos personales | Ubicación GPS de las fotos (D-14) | JPEG con EXIF GPS | El archivo guardado y el descargado no tienen GPS | No se guardan datos personales innecesarios | `test_la_foto_se_guarda_sin_metadatos_ni_contenido_agregado`, `test_misma_delegacion_y_verificador_lo_ven` | ✅ |

### 4.5 Usabilidad

| ID | Módulo | Descripción | Datos de prueba | Resultado esperado | Criterio de aceptación | Prueba | Res. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CP-U01 | Listados | Tablet vertical (768×1024) | 5 listados como `admin_sgr` | Una tarjeta por registro; Editar/Eliminar visibles | Sin desplazamiento lateral | `scripts/pruebas_navegador.js` | ✅ |
| CP-U02 | Listados | Tablet horizontal (1024×768) y PC (1366×768) | 5 listados | Tabla; si es más ancha que la pantalla se desplaza dentro de su caja con la columna de acciones fija (D-17) | La página no se desplaza de lado y Editar/Eliminar están a la vista | `scripts/pruebas_navegador.js` | ✅ |
| CP-U03 | Listados | Celular (390×844) | 5 listados | Una tarjeta por registro | Sin desplazamiento lateral | `scripts/pruebas_navegador.js` | ✅ |
| CP-U04 | Navegación | Menú en pantalla táctil | Tablet | Menú hamburguesa con navegación, tema y cerrar sesión | Todo alcanzable con el dedo | Captura `capturas/usabilidad/usabilidad-despues-tablet-menu.png` | ✅ |
| CP-U05 | Accesibilidad | Tema claro, oscuro o del sistema | Selector de tema | Se aplica en la app y en el Admin | Colores de estado con icono y texto (no solo color) | `test_app_y_admin_guardan_el_tema_en_la_misma_clave` | ✅ |
| CP-U06 | Listados | Selector «Por página» (D-16) | Elegir 30 | Una sola petición `?page_size=30` | Sin envíos duplicados | `scripts/pruebas_navegador.js` y Herramientas de desarrollo → Red | ✅ |

## 5. Criterios de aceptación del plan

- Todos los casos críticos aprobados: ingreso, permisos y alcance, registro de actividades y evidencias.
- Sin vulnerabilidades críticas de OWASP Top 10 abiertas (ver el registro de deficiencias en `README.md`).
- Usabilidad confirmada en PC, tablet y celular.
- Cada deficiencia encontrada queda corregida antes de la entrega, con una prueba que lo confirma.

## 6. Roles y responsabilidades

- **Equipo de desarrollo:** pruebas unitarias y de integración (`python manage.py test`).
- **QA / testers:** pruebas funcionales, de seguridad y de usabilidad (scripts de verificación y navegador).
- **Usuarios finales** (administrador general, administrador de delegación, verificador y funcionario): pruebas de aceptación.

## 7. Guion de aceptación por rol

| Rol (cuenta) | Tarea | Aceptado si |
| --- | --- | --- |
| Funcionario (`funcionario_centro`) | Registrar una actividad y subir su evidencia | La actividad queda pendiente y aparece en su dashboard |
| Verificador (`verificador_leia`) | Aprobar una evidencia pendiente | La actividad pasa a aprobada y suma al cumplimiento |
| Admin de delegación (`admin_centro`) | Revisar el avance de su equipo y exportar a Excel | Solo ve y exporta la Delegación Centro |
| Administrador general (`admin_sgr`) | Consultar la traza de accesos y restaurar un registro eliminado | Ve los ingresos fallidos con IP y puede restaurar |

Las 96 verificaciones de `scripts/verificacion_e2e.py` automatizan estos recorridos. La validación con
usuarios reales queda a cargo del grupo.

## 8. Resultado de la ejecución (02-10-2026)

| Conjunto | Resultado |
| --- | --- |
| `python manage.py test` | 367 pruebas, todas correctas |
| `scripts/verificacion_e2e.py` | 96/96 verificaciones correctas |
| `scripts/pruebas_navegador.js` | 28/28 verificaciones correctas |
| `pip-audit -r requirements.txt` | Sin vulnerabilidades conocidas |

Las deficiencias encontradas, sus correcciones y las capturas de antes y después están en
[`README.md`](README.md#registro-de-deficiencias).
