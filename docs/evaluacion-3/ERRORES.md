# Errores encontrados, corrección y dónde capturarlos

Guía para armar la evidencia del informe de la Evaluación 3. Cada error dice **qué fallaba**, **cómo se
solucionó** y **dónde se captura**: la pantalla, la URL o el comando que muestra el error en la versión
anterior (**antes**) y la solución en la versión actual (**después**). El resumen de estado está en el
[registro de deficiencias](README.md#registro-de-deficiencias).

| ID | Error | Tipo | Estado |
| --- | --- | --- | --- |
| [D-01](#d-01-intentos-de-ingreso-ilimitados) | Intentos de ingreso ilimitados | OWASP A07 | ✅ Corregido · capturas listas |
| [D-02](#d-02-accesos-sin-registrar) | Accesos y 403 sin registrar | OWASP A09 | ✅ Corregido · capturas listas |
| [D-03](#d-03-sin-política-de-seguridad-de-contenido-csp) | Sin política de seguridad de contenido | OWASP A05 | ✅ Corregido · capturas listas |
| [D-04](#d-04-la-csp-bloqueaba-los-selectores) | La CSP bloqueaba los selectores | Regresión | ✅ Corregido · capturas listas |
| [D-05](#d-05-tablas-desbordadas-en-tablet) | Tablas desbordadas en tablet | Usabilidad | ✅ Corregido · capturas listas |
| [D-06](#d-06-dependencias-sin-revisar) | Dependencias sin revisar | OWASP A06 | ✅ Verificado · captura lista |
| [D-07](#d-07-textos-de-ayuda-sin-escapar) | Textos de ayuda sin escapar (`\|safe`) | OWASP A03 | ✅ Corregido · **falta capturar** |
| [D-08](#d-08-el-despliegue-usa-http) | El despliegue usa HTTP | OWASP A02 | ⏳ Pendiente (entorno) |
| [D-09](#d-09-la-verificación-dependía-del-estado-de-la-base) | La verificación dependía del estado de la base | Calidad de pruebas | ✅ Corregido · captura lista |
| [D-10](#d-10-archivos-de-evidencias-públicos) | Archivos de evidencias públicos | OWASP A01 | ✅ Corregido · **falta capturar** |
| [D-11](#d-11-se-aceptaba-un-pdf-falso) | Se aceptaba un PDF falso | OWASP A04 | ✅ Corregido · **falta capturar** |
| [D-12](#d-12-se-aceptaban-pdf-con-javascript) | Se aceptaban PDF con JavaScript | OWASP A04 / A03 | ✅ Corregido · **falta capturar** |
| [D-13](#d-13-extensión-distinta-del-contenido-y-código-escondido) | Extensión distinta del contenido y código escondido | OWASP A04 | ✅ Corregido · **falta capturar** |
| [D-14](#d-14-fotos-con-la-ubicación-gps) | Fotos con la ubicación GPS | Ley 19.628 | ✅ Corregido · **falta capturar** |
| [D-15](#d-15-mensaje-de-ingreso-ambiguo) | Mensaje de ingreso ambiguo | Usabilidad / soporte | ✅ Corregido · **falta capturar** |
| [D-16](#d-16-doble-envío-al-elegir-el-tamaño-de-página) | Doble envío al elegir el tamaño de página | Integración | ✅ Corregido · **falta capturar** |
| [D-17](#d-17-la-prueba-en-navegador-daba-ok-sin-revisar) | La prueba en navegador daba OK sin revisar | Calidad de pruebas | ✅ Corregido · **falta capturar** |

Los archivos de prueba para D-11 a D-14 se generan con:

```bash
python manage.py shell < scripts/archivos_de_prueba.py      # deja los archivos en archivos_de_prueba/
```

## Cómo levantar la versión anterior sin tocar la actual

Para capturar el **antes** se levanta una copia del código en la versión indicada, con **otra base de
datos**, en otro puerto. La versión actual sigue intacta.

```bash
# 1) Copia del código en la versión "antes" (en una carpeta aparte)
git worktree add ../sgr-antes <commit-antes>
cp .env ../sgr-antes/.env
cd ../sgr-antes

# 2) Base de datos aparte (una vez, como root de MariaDB/MySQL)
#    CREATE DATABASE sgr_antes CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
#    GRANT ALL PRIVILEGES ON sgr_antes.* TO '<usuario de .env>'@'localhost';

# 3) Datos y servidor en el puerto 8001
DB_NAME=sgr_antes python manage.py migrate
DB_NAME=sgr_antes DEMO_PASSWORD='<clave de prueba>' python manage.py seed_data
DB_NAME=sgr_antes python manage.py runserver 8001

# 4) Al terminar
cd ../<carpeta del proyecto> && git worktree remove ../sgr-antes
```

La versión actual se levanta como siempre (`python manage.py runserver`, puerto 8000). En cada error,
**antes** = `http://127.0.0.1:8001` y **después** = `http://127.0.0.1:8000`.

---

## D-01 Intentos de ingreso ilimitados

- **Qué fallaba:** tras 6 claves incorrectas, la correcta entraba igual. Se podía probar claves sin límite (fuerza bruta).
- **Solución:** bloqueo temporal de 5 fallos por usuario o 20 por IP en 15 minutos. El bloqueo se revisa antes de comprobar la clave (`funcionarios/accesos.py`, `funcionarios/forms.py`).
- **Antes / después:** ya capturados en [`capturas/a07-*`](capturas/).
- **Prueba:** `python manage.py test funcionarios.tests_seguridad_owasp.A07LimiteDeIntentosTests`.

## D-02 Accesos sin registrar

- **Qué fallaba:** los ingresos fallidos, los cierres de sesión y los 403 no quedaban en ninguna traza.
- **Solución:** la traza de auditoría registra `login_exitoso`, `login_fallido`, `login_bloqueado`, `logout` y `acceso_denegado`, con usuario, IP y fecha.
- **Antes / después:** ya capturados en [`capturas/a09-*`](capturas/). Para repetirlo: Admin → Colaboración → Trazas de auditoría.

## D-03 Sin política de seguridad de contenido (CSP)

- **Qué fallaba:** las respuestas no traían cabecera `Content-Security-Policy`.
- **Solución:** `SECURE_CSP` en `config/settings.py`, con el middleware de CSP de Django 6.1.
- **Antes / después:** ya capturados en [`capturas/a05-*`](capturas/). Para repetirlo: `curl -I http://127.0.0.1:8000/accounts/login/` o en el navegador, Herramientas de desarrollo → Red → Cabeceras.

## D-04 La CSP bloqueaba los selectores

- **Qué fallaba:** con la CSP activa, «Por página» y «Período» usaban `onchange=` (JavaScript en línea) y dejaron de funcionar.
- **Solución:** `static/js/autoenvio.js` con `data-autoenviar`. Una prueba impide volver a usar `on…=` en las plantillas.
- **Antes / después:** ya capturados en [`capturas/a05-regresion-*`](capturas/) y [`a05-despues-navegador-*`](capturas/).

## D-05 Tablas desbordadas en tablet

- **Qué fallaba:** en tablet los listados se desplazaban de lado y los botones Editar/Eliminar quedaban fuera de la vista.
- **Solución:**
  - hasta 991 px, cada registro se muestra como tarjeta;
  - desde 992 px (rediseño de listados, ver D-17), una tabla ancha se desplaza dentro de su caja, con la columna de acciones fija a la derecha, y la página nunca se desplaza.
- **Antes / después:** ya capturados en [`capturas/u01-*`](capturas/) y [`capturas/usabilidad/`](capturas/usabilidad/).
- **Después, con el diseño nuevo:** abrir `/actividades/` a 1024 px de ancho (Herramientas de desarrollo → modo dispositivo) y desplazar la tabla: los íconos de editar y eliminar no se mueven.

## D-06 Dependencias sin revisar

- **Solución:** `pip install pip-audit && pip-audit -r requirements.txt`, antes de cada entrega.
- **Captura:** ya está [`capturas/a06-pip-audit-dependencias.png`](capturas/a06-pip-audit-dependencias.png). Conviene repetirla el día de la entrega.

## D-07 Textos de ayuda sin escapar

- **Qué fallaba:** `templates/includes/form_campos.html` mostraba `{{ field.help_text|safe }}`. Si un texto de ayuda llegara a contener HTML o un script, se ejecutaría en la página. Antes se había **aceptado como riesgo**, porque los textos salen del código.
- **Verificación hecha:** se comprobó que el `|safe` **no hace falta**. El único texto de ayuda con HTML es la lista de reglas de contraseña, y Django ya lo marca como HTML seguro. Sin `|safe`:
  - esa lista se sigue viendo como lista;
  - un texto con `<img src=x onerror=alert(1)>` se muestra como texto.
- **Por eso se aplica la corrección** (commit `2719322`): se quitó el `|safe` y se agregó una prueba que, además, revisa que ninguna plantilla vuelva a usar `help_text|safe`.
- **Dónde capturar:**
  - **Antes:** con la plantilla anterior, la prueba nueva falla.
    ```bash
    git checkout f870c88 -- templates/includes/form_campos.html
    python manage.py test funcionarios.tests_seguridad_owasp.A03InyeccionCsrfYSesionTests.test_textos_de_ayuda_se_escapan_salvo_el_html_marcado_como_seguro
    git checkout HEAD -- templates/includes/form_campos.html       # volver a la versión corregida
    ```
  - **Después:** el mismo comando sin el `git checkout` pasa (OK).
  - **Pantalla:** en `/accounts/recuperar/` → código → nueva contraseña, la lista de reglas de contraseña se sigue viendo como lista.

## D-08 El despliegue usa HTTP

- **Estado:** pendiente por el entorno. El Learner Lab no entrega dominio ni certificado. La configuración ya admite HTTPS (`COOKIE_SECURE=True`, `BEHIND_HTTPS_PROXY=True`).
- **Captura:** la barra del navegador en `http://<IP-EC2>` muestra «No seguro». Sirve para justificarlo en el informe.

## D-09 La verificación dependía del estado de la base

- **Antes / después:** ya capturado en [`capturas/d09-verificacion-reproducible.png`](capturas/d09-verificacion-reproducible.png).
- **Para repetirlo:** `python manage.py shell < scripts/verificacion_e2e.py`.

## D-10 Archivos de evidencias públicos

- **Qué fallaba:** nginx publicaba la carpeta `/media/`. Con el enlace de un archivo, cualquiera lo descargaba **sin iniciar sesión**, y un usuario de otra delegación también. Los respaldos tienen datos personales.
- **Solución** (commit `044ca44`):
  - los archivos se entregan por `/archivos/<nombre>`, una vista que exige sesión, el permiso de ver evidencias y que la evidencia sea de su delegación (404 si no lo es);
  - `/media/` ya no responde (nginx `return 404`);
  - la respuesta lleva `nosniff` y `Cache-Control: private, no-store`;
  - se verificó que el visor de PDF del navegador funciona con la CSP de D-03.
- **Dónde capturar el antes:**
  - **En la EC2, antes de actualizar nginx** (es la captura más real): sin iniciar sesión, `curl -I http://<IP-EC2>/media/evidencias/<año>/<mes>/<archivo>.pdf` responde `200 OK`. El nombre del archivo se ve en Evidencias → «Ver archivo».
  - **O en local:** versión anterior `b936ac1` con `DEBUG=True`. En una ventana privada, sin sesión, se abre `http://127.0.0.1:8001/media/evidencias/…` y el archivo se descarga.
- **Dónde capturar el después:**
  - en una ventana privada, `http://127.0.0.1:8000/archivos/evidencias/…` redirige al login;
  - `http://127.0.0.1:8000/media/evidencias/…` da 404;
  - con `admin_norte`, un archivo de una evidencia de Centro da 404.
- **Prueba:** `python manage.py test evidencias.tests_validacion_subida.EntregaProtegidaTests`.

## D-11 Se aceptaba un PDF falso

- **Qué fallaba:** solo se revisaba que el archivo empezara con `%PDF-`. Un archivo de 15 bytes sin páginas pasaba como PDF.
- **Solución** (commit `044ca44`): `evidencias/archivos.py` exige la estructura completa: cabecera, al menos una página, tabla `xref` y `%%EOF`.
- **Dónde capturar:** Evidencias → Nueva evidencia → subir `archivos_de_prueba/D11-pdf-falso.pdf`.
  - **Antes** (versión `b936ac1`, puerto 8001): se guarda la evidencia.
  - **Después** (puerto 8000): el formulario muestra «El archivo no es un PDF válido.».

## D-12 Se aceptaban PDF con JavaScript

- **Qué fallaba:** un PDF podía traer código JavaScript, acciones de ejecución (`/Launch`) o archivos incrustados.
- **Solución:** se rechazan los PDF con `/JavaScript`, `/JS`, `/Launch`, archivos incrustados, `/RichMedia` o XFA:
  - también cuando el nombre viene disfrazado (`/J#61vaScript`) o está dentro de un flujo comprimido;
  - se rechazan además los PDF cifrados, porque no se pueden revisar.
- **Dónde capturar:** subir `D12-pdf-con-javascript.pdf` y `D12-pdf-javascript-comprimido.pdf`.
  - **Antes:** se aceptan.
  - **Después:** «El PDF contiene código o archivos incrustados…».

## D-13 Extensión distinta del contenido y código escondido

- **Qué fallaba:**
  - un JPEG renombrado a `.png` se aceptaba;
  - una imagen con código agregado al final (archivo «políglota») se guardaba tal cual, con el código adentro.
- **Solución:**
  - el formato real debe coincidir con la extensión;
  - toda imagen se vuelve a guardar con Pillow, lo que descarta cualquier contenido agregado.
- **Dónde capturar:**
  - `D13-jpeg-con-extension-png.png`: **antes** se acepta; **después** dice «El contenido no coincide con la extensión: la imagen es JPEG…».
  - `D13-png-con-codigo-agregado.png`: se acepta en ambas versiones. La diferencia está en el archivo guardado.
    - **Antes:** descargarlo con «Ver archivo» y abrirlo en un editor de texto: al final aparece `<?php echo "codigo escondido"; ?>`.
    - **Después:** el archivo descargado ya no lo tiene.

## D-14 Fotos con la ubicación GPS

- **Qué fallaba:** las fotos de celular se guardaban con sus metadatos EXIF, incluida la **ubicación GPS** de quien tomó la foto. Es un dato personal (Ley 19.628) que el sistema no necesita.
- **Solución:** al volver a guardar la imagen (D-13) se descartan los metadatos, y la orientación de la foto se conserva.
- **Dónde capturar:** subir `D14-foto-con-ubicacion-gps.jpg`, descargarla con «Ver archivo» y ver sus propiedades. En Windows: clic derecho → Propiedades → Detalles. En Mac: Vista previa → Herramientas → Mostrar inspector → GPS. También sirve <https://exif.tools>, con un archivo de prueba, nunca con uno real.
  - **Antes:** la descargada muestra latitud y longitud.
  - **Después:** no tiene datos GPS.

## D-15 Mensaje de ingreso ambiguo

- **Qué fallaba:** **caso real del equipo.** Una cuenta creada en el Admin con grupo pero sin perfil de funcionario veía «Su cuenta no tiene un rol asignado», aunque sí tenía rol. El mismo mensaje cubría dos problemas distintos, así que no se sabía qué corregir.
- **Solución** (commit `e090b7c`):
  - el mensaje distingue «sin rol» de «tiene el rol, pero no tiene un perfil de funcionario con delegación»;
  - nuevo comando `python manage.py diagnosticar_acceso <usuario o correo>`, que dice qué le falta a una cuenta (grupo mal escrito, perfil en otra cuenta, etc.).
- **Dónde capturar:**
  1. En el Admin, crear un usuario, agregarlo al grupo **Funcionarios** y **no** crearle perfil.
  2. **Antes** (versión `6000f68`): al ingresar, «Su cuenta no tiene un rol asignado».
  3. **Después:** «Su cuenta tiene el rol funcionario, pero no tiene un perfil de funcionario con delegación».
  4. Capturar también la salida de `python manage.py diagnosticar_acceso <usuario>`.
- **Prueba:** `python manage.py test funcionarios.tests_diagnostico`.

## D-16 Doble envío al elegir el tamaño de página

- **Qué fallaba:** **hallazgo al integrar** el rediseño de listados con esta rama. El selector «Por página» quedaba con dos manejadores: `autoenvio.js` (D-04) y `listado.js` (rediseño). Al elegir un valor, el formulario se enviaba dos veces.
- **Solución** (commit `cc72fe0`): se quitó el envío duplicado de `static/js/listado.js`. Ahora lo hace solo `autoenvio.js`.
- **Dónde capturar:**
  - **Antes:** no hubo una versión publicada con el error, porque se corrigió durante la integración. La evidencia es el cambio: `git show cc72fe0` (o el commit `cc72fe0` en GitHub).
  - **Después:** Herramientas de desarrollo → Red, elegir 30 en «Por página»: aparece **una** sola petición `?page_size=30`.

## D-17 La prueba en navegador daba OK sin revisar

- **Qué fallaba:** **hallazgo al aplicar las pruebas** después del rediseño. `scripts/pruebas_navegador.js` tenía tres problemas:
  1. Si el ingreso fallaba (clave incorrecta o cuenta bloqueada), revisaba la **página de login** y marcaba OK todos los listados.
  2. Buscaba los botones como `td.celda-acciones .btn`, pero en el diseño nuevo los botones son `.btn-icono`. No encontraba ninguno y la revisión pasaba sin revisar nada.
  3. Exigía que **ninguna tabla** se desplazara de lado, pero el diseño nuevo desplaza a propósito las tablas anchas con la columna de acciones fija. Marcaba 7 fallas aunque los botones estaban siempre a la vista.
- **Solución** (commit `1f6ec1e`):
  - el script se detiene con error si no logra iniciar sesión;
  - busca los botones reales de la primera fila (sin los enlaces del menú «⋯», que están ocultos hasta abrirlo);
  - exige lo que importa para el usuario: que la página no se desplace y que los botones estén a la vista sin desplazar nada. Si una tabla se desplaza dentro de su caja, lo informa.
  - Resultado: 28/28.
- **Dónde capturar:**
  - **Antes:** `git show f870c88:scripts/pruebas_navegador.js > /tmp/pruebas_antes.js` y ejecutarlo con una clave **incorrecta**: `SGR_URL=http://127.0.0.1:8000 SGR_CLAVE=incorrecta node /tmp/pruebas_antes.js`. Muestra «OK … sin desplazamiento lateral» en los cinco listados de PC sin haber entrado, y recién después se cae esperando el selector «Por página», con un error que no dice que el problema fue el ingreso.
  - **Después:** con la misma clave incorrecta, `node scripts/pruebas_navegador.js` se detiene con «FALLA … no se pudo iniciar sesión». Con la clave correcta: 28/28.

---

## Capturas de cierre (después de todo)

```bash
python manage.py test                                     # batería completa
python manage.py test funcionarios.tests_seguridad_owasp evidencias.tests_validacion_subida funcionarios.tests_diagnostico
python manage.py shell < scripts/verificacion_e2e.py      # verificaciones de punta a punta
SGR_URL=http://127.0.0.1:8000 SGR_CLAVE='<clave>' node scripts/pruebas_navegador.js
pip-audit -r requirements.txt
```

Nombre sugerido para las capturas nuevas, igual que las existentes: `capturas/d10-antes-media-publica.png`,
`capturas/d10-despues-archivos-login.png`, `capturas/d11-antes-pdf-falso-aceptado.png`, etc.
