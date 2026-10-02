// Si el navegador muestra esta página desde su memoria de «atrás/adelante» (bfcache), sin pedirla al
// servidor, se recarga: así el servidor vuelve a revisar la sesión (si se cerró, envía al login). Las
// páginas con sesión ya se marcan como no almacenables; esto cubre a los navegadores que igual las guardan.
window.addEventListener('pageshow', function (event) {
    if (event.persisted) {
        window.location.reload();
    }
});
