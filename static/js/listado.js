// Interacción de los listados (templates/crud/list.html). Solo interfaz: el servidor vuelve a
// aplicar permisos y alcance en cada petición, incluida la exportación de los seleccionados.
(function () {
    const lista = document.querySelector('.lista');
    if (!lista) {
        return;
    }

    // El tamaño de página (select[data-autoenviar]) lo envía static/js/autoenvio.js, cargado en base.html.

    // ----- Selección de filas y exportación de los seleccionados -----
    const todos = lista.querySelector('[data-seleccionar-todo]');
    const filas = Array.from(lista.querySelectorAll('[data-fila]'));
    const barra = lista.querySelector('[data-barra-seleccion]');
    const cantidad = lista.querySelector('[data-cantidad]');
    const exportar = lista.querySelector('[data-exportar-seleccion]');

    function actualizarSeleccion() {
        const marcadas = filas.filter(function (c) { return c.checked; });
        filas.forEach(function (c) { c.closest('tr').classList.toggle('seleccionada', c.checked); });
        if (todos) {
            todos.checked = marcadas.length > 0 && marcadas.length === filas.length;
            todos.indeterminate = marcadas.length > 0 && marcadas.length < filas.length;
        }
        barra.hidden = marcadas.length === 0;
        cantidad.textContent = marcadas.length;
        const ids = marcadas.map(function (c) { return c.value; }).join(',');
        const estado = lista.dataset.estado;
        exportar.href = lista.dataset.exportUrl + '?' + (estado ? estado + '&' : '') + 'ids=' + ids;
    }

    if (todos) {
        todos.addEventListener('change', function () {
            filas.forEach(function (c) { c.checked = todos.checked; });
            actualizarSeleccion();
        });
    }
    filas.forEach(function (c) { c.addEventListener('change', actualizarSeleccion); });
    lista.querySelector('[data-limpiar-seleccion]').addEventListener('click', function () {
        filas.forEach(function (c) { c.checked = false; });
        actualizarSeleccion();
    });

    // ----- Columnas visibles (preferencia del navegador; si no hay almacenamiento, se ven todas) -----
    const clave = 'sgr-columnas-' + lista.dataset.tabla;
    let ocultas = [];
    try {
        ocultas = JSON.parse(localStorage.getItem(clave) || '[]');
    } catch (e) {
        ocultas = [];
    }

    function aplicarColumnas() {
        lista.querySelectorAll('[data-col]').forEach(function (celda) {
            celda.classList.toggle('col-oculta', ocultas.indexOf(celda.dataset.col) !== -1);
        });
        lista.querySelectorAll('[data-columna]').forEach(function (casilla) {
            casilla.checked = ocultas.indexOf(casilla.dataset.columna) === -1;
        });
    }

    lista.querySelectorAll('[data-columna]').forEach(function (casilla) {
        casilla.addEventListener('change', function () {
            const col = casilla.dataset.columna;
            ocultas = ocultas.filter(function (c) { return c !== col; });
            if (!casilla.checked) {
                ocultas.push(col);
            }
            try {
                localStorage.setItem(clave, JSON.stringify(ocultas));
            } catch (e) { /* sin almacenamiento: el cambio dura hasta recargar */ }
            aplicarColumnas();
        });
    });
    aplicarColumnas();
})();
