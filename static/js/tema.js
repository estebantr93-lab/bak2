// Selector de tema (claro / oscuro / por defecto del sistema) del menú principal.
// La preferencia se guarda solo en este navegador; si no se puede guardar, se usa la del sistema.
(function () {
    var CLAVE = 'sgr-tema';
    var sistema = window.matchMedia('(prefers-color-scheme: dark)');

    function leer() {
        try { return localStorage.getItem(CLAVE) || 'auto'; } catch (e) { return 'auto'; }
    }

    function aplicar(tema) {
        var oscuro = tema === 'dark' || (tema === 'auto' && sistema.matches);
        document.documentElement.setAttribute('data-bs-theme', oscuro ? 'dark' : 'light');
        document.querySelectorAll('[data-tema]').forEach(function (boton) {
            var activo = boton.dataset.tema === tema;
            boton.classList.toggle('active', activo);
            boton.setAttribute('aria-pressed', activo ? 'true' : 'false');
        });
    }

    document.querySelectorAll('[data-tema]').forEach(function (boton) {
        boton.addEventListener('click', function () {
            try {
                if (boton.dataset.tema === 'auto') localStorage.removeItem(CLAVE);
                else localStorage.setItem(CLAVE, boton.dataset.tema);
            } catch (e) {}
            aplicar(boton.dataset.tema);
        });
    });

    sistema.addEventListener('change', function () {
        if (leer() === 'auto') aplicar('auto');
    });

    aplicar(leer());
})();
