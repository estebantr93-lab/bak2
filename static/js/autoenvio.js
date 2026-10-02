// Envía el formulario al cambiar un <select data-autoenviar> (tamaño de página, período del dashboard).
// Reemplaza a onchange="this.form.submit()": la CSP (OWASP A05) no ejecuta JavaScript escrito en atributos.
document.addEventListener('change', function (event) {
    const campo = event.target;
    if (campo.matches('select[data-autoenviar]') && campo.form) {
        campo.form.submit();
    }
});
