// Selector de tema (claro / oscuro / por defecto del sistema) del menú principal.
// Se usa en la app y en el admin: guarda la preferencia en la misma clave que el admin
// de Django ("theme") y marca ambos atributos: data-bs-theme (Bootstrap, en la app)
// y data-theme (hojas de estilo del admin). Si no se puede guardar, se usa la del sistema.
(function () {
    var CLAVE = 'theme';
    var sistema = window.matchMedia('(prefers-color-scheme: dark)');

    function leer() {
        var t = null;
        try { t = localStorage.getItem(CLAVE); } catch (e) {}
        return t === 'light' || t === 'dark' ? t : 'auto';
    }

    function aplicar(tema) {
        var oscuro = tema === 'dark' || (tema === 'auto' && sistema.matches);
        document.documentElement.setAttribute('data-bs-theme', oscuro ? 'dark' : 'light');
        document.documentElement.setAttribute('data-theme', tema);
        document.querySelectorAll('[data-tema]').forEach(function (boton) {
            var activo = boton.dataset.tema === tema;
            boton.classList.toggle('active', activo);
            boton.setAttribute('aria-pressed', activo ? 'true' : 'false');
        });
    }

    document.querySelectorAll('[data-tema]').forEach(function (boton) {
        boton.addEventListener('click', function () {
            try { localStorage.setItem(CLAVE, boton.dataset.tema); } catch (e) {}
            aplicar(boton.dataset.tema);
        });
    });

    sistema.addEventListener('change', function () {
        if (leer() === 'auto') aplicar('auto');
    });

    aplicar(leer());
})();
