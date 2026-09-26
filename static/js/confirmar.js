// Confirmación visual con SweetAlert2 para formularios marcados con data-confirmar.
// Es solo experiencia de usuario: el servidor sigue exigiendo POST, CSRF, login y permisos.
document.addEventListener('submit', async function (event) {
    const form = event.target;
    if (!form.matches('form[data-confirmar]') || form.dataset.confirmado === '1') {
        return;
    }
    if (typeof Swal === 'undefined') {
        return; // sin SweetAlert2 disponible, el formulario se envía igual (el backend decide).
    }
    event.preventDefault();
    const result = await Swal.fire({
        title: '¿Está seguro?',
        text: form.dataset.confirmar,
        icon: 'warning',
        showCancelButton: true,
        confirmButtonText: 'Sí, eliminar',
        cancelButtonText: 'Cancelar',
        confirmButtonColor: '#ad0000',
        focusCancel: true,
    });
    if (result.isConfirmed) {
        form.dataset.confirmado = '1';
        form.requestSubmit();
    }
});
