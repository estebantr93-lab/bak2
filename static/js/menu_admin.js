// Menú hamburguesa del admin (<details>): se cierra al hacer clic fuera o con Escape.
(function () {
    var menu = document.querySelector('details.sgr-menu');
    if (!menu) return;

    document.addEventListener('click', function (evento) {
        if (menu.open && !menu.contains(evento.target)) menu.open = false;
    });

    document.addEventListener('keydown', function (evento) {
        if (evento.key === 'Escape' && menu.open) {
            menu.open = false;
            menu.querySelector('summary').focus();
        }
    });
})();
