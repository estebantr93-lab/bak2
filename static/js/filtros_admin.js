// Listas del Admin. Filtros en un botón tipo hamburguesa: el panel no ocupa ancho fijo junto a la tabla
// (así se ven todas las columnas); se despliega encima al pulsar «Filtros». Muestra cuántos hay activos.
(function () {
    // Etiquetas por celda: en celular cada fila se muestra como tarjeta «etiqueta: valor».
    var tabla = document.getElementById('result_list');
    if (tabla) {
        var encabezados = Array.prototype.map.call(tabla.querySelectorAll('thead th'), function (th) {
            return th.textContent.trim();
        });
        tabla.querySelectorAll('tbody tr').forEach(function (fila) {
            Array.prototype.forEach.call(fila.children, function (celda, i) {
                if (encabezados[i]) celda.setAttribute('data-etiqueta', encabezados[i]);
            });
        });
    }
})();

(function () {
    var panel = document.getElementById('changelist-filter');
    var contenedor = document.getElementById('changelist');
    if (!panel || !contenedor) return;

    // Parámetros que no son filtros: búsqueda, orden, página y los propios del Admin.
    var noFiltros = ['q', 'o', 'p', 'all', '_changelist_filters', '_popup', '_to_field', 'e'];
    var activos = 0;
    new URLSearchParams(window.location.search).forEach(function (valor, clave) {
        if (noFiltros.indexOf(clave) === -1) activos += 1;
    });

    var boton = document.createElement('button');
    boton.type = 'button';
    boton.className = 'sgr-filtros-boton';
    boton.setAttribute('aria-expanded', 'false');
    boton.setAttribute('aria-controls', 'changelist-filter');
    boton.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M7 12h10M10 17h4"/></svg>' +
        '<span>Filtros</span>' + (activos ? '<span class="sgr-filtros-cuenta">' + activos + '</span>' : '');

    var barra = document.getElementById('toolbar');
    if (barra) {
        barra.appendChild(boton);
    } else {
        var zona = document.createElement('div');
        zona.id = 'toolbar';
        zona.className = 'sgr-toolbar-solo-filtros';
        zona.appendChild(boton);
        contenedor.querySelector('.changelist-form-container > div').prepend(zona);
    }

    contenedor.classList.add('sgr-filtros-plegables');

    function abrir(si) {
        contenedor.classList.toggle('sgr-filtros-abiertos', si);
        boton.setAttribute('aria-expanded', si ? 'true' : 'false');
    }

    boton.addEventListener('click', function (evento) {
        evento.stopPropagation();
        abrir(!contenedor.classList.contains('sgr-filtros-abiertos'));
    });
    document.addEventListener('click', function (evento) {
        if (!panel.contains(evento.target) && evento.target !== boton) abrir(false);
    });
    document.addEventListener('keydown', function (evento) {
        if (evento.key === 'Escape') abrir(false);
    });
})();
