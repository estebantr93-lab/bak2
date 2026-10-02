// Pruebas en navegador de la Evaluación 3 (usabilidad por dispositivo y CSP). Casos CP-U01..U03 y CP-S10.
//
// Uso, con el servidor levantado (python manage.py runserver):
//   npm install playwright && npx playwright install chromium   (una sola vez)
//   SGR_URL=http://127.0.0.1:8000 SGR_USUARIO=admin_sgr SGR_CLAVE='<clave>' node scripts/pruebas_navegador.js
//
// Para cada equipo (PC, tablet vertical y horizontal, celular) recorre los listados y revisa que la
// página no se desplace de lado y que los botones de acción de la primera fila estén a la vista sin
// desplazar nada (una tabla ancha puede desplazarse dentro de su caja con la columna de acciones fija). En todas las páginas cuenta las violaciones de la política de
// seguridad de contenido (CSP) que informa el navegador. Termina con código 1 si algo falla.
const { chromium } = require('playwright');

const URL = process.env.SGR_URL || 'http://127.0.0.1:8000';
const USUARIO = process.env.SGR_USUARIO || 'admin_sgr';
const CLAVE = process.env.SGR_CLAVE;
const EQUIPOS = [['PC', 1366, 768], ['Tablet vertical', 768, 1024], ['Tablet horizontal', 1024, 768], ['Celular', 390, 844]];
const LISTADOS = ['/dashboard/', '/actividades/', '/actividades/atenciones/', '/evidencias/', '/compromisos/'];

(async () => {
    if (!CLAVE) {
        console.error('Falta SGR_CLAVE (contraseña de la cuenta de prueba).');
        process.exit(2);
    }
    const navegador = await chromium.launch();
    let fallas = 0;
    const revisar = (ok, texto) => { console.log(`${ok ? 'OK   ' : 'FALLA'} ${texto}`); if (!ok) fallas++; };

    for (const [equipo, ancho, alto] of EQUIPOS) {
        const contexto = await navegador.newContext({ viewport: { width: ancho, height: alto }, hasTouch: equipo !== 'PC' });
        const pagina = await contexto.newPage();
        const violaciones = [];
        pagina.on('console', m => { if (/Content Security Policy/.test(m.text())) violaciones.push(m.text()); });
        await pagina.goto(URL + '/accounts/login/');
        await pagina.fill('input[name=username]', USUARIO);
        await pagina.fill('input[name=password]', CLAVE);
        await Promise.all([pagina.waitForNavigation(), pagina.click('button[type=submit]')]);
        // Sin sesión, cada listado redirige al login y las revisiones de abajo pasarían sin revisar nada.
        if (pagina.url().includes('/accounts/login/')) {
            console.error(`FALLA ${equipo}: no se pudo iniciar sesión con ${USUARIO} (clave incorrecta o cuenta bloqueada).`);
            process.exit(2);
        }

        for (const ruta of LISTADOS) {
            await pagina.goto(URL + ruta);
            const r = await pagina.evaluate(() => {
                // Último botón visible de la primera fila (Eliminar o «⋯»; no los enlaces del menú cerrado).
                const botones = document.querySelectorAll('tbody tr:first-child td.celda-acciones :is(a, button):not(.dropdown-menu *)');
                const ultimo = botones[botones.length - 1];
                const visible = el => {
                    if (!el) return true;  // fila sin acciones (el rol no puede editar)
                    const b = el.getBoundingClientRect();
                    const caja = (el.closest('.table-responsive') || document.body).getBoundingClientRect();
                    return b.width > 0 && b.left >= 0 && b.right <= innerWidth && b.left >= caja.left - 1 && b.right <= caja.right + 1;
                };
                return {
                    pagina: document.documentElement.scrollWidth > innerWidth + 1,
                    // Las tablas anchas pueden desplazarse dentro de su caja (con la columna de acciones fija);
                    // se informa, pero lo que se exige es que los botones queden a la vista sin desplazar.
                    tablas: [...document.querySelectorAll('.table-responsive')]
                        .filter(c => c.querySelector('table').scrollWidth > c.clientWidth + 2).length,
                    botones: visible(ultimo),
                };
            });
            revisar(!r.pagina && r.botones,
                `${equipo} (${ancho}x${alto}) ${ruta}: la página no se desplaza de lado y los botones están a la vista`
                + (r.tablas ? ' (tabla con desplazamiento interno y columna de acciones fija)' : ''));
        }
        // Los selectores que se envían solos (tamaño de página) deben seguir funcionando con la CSP.
        await pagina.goto(URL + '/actividades/');
        await pagina.selectOption('#page_size', '30');
        await pagina.waitForURL(/page_size=30/, { timeout: 3000 }).catch(() => {});
        revisar(pagina.url().includes('page_size=30'), `${equipo}: el tamaño de página se aplica al elegirlo`);
        revisar(violaciones.length === 0, `${equipo}: sin violaciones de CSP (${violaciones.length})`);
        await contexto.close();
    }
    await navegador.close();
    console.log(fallas ? `\n${fallas} verificación(es) con falla` : '\nTodas las verificaciones correctas');
    process.exit(fallas ? 1 : 0);
})();
