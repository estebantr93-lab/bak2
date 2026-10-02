from django.utils.cache import add_never_cache_headers, patch_vary_headers


class SinCacheConSesionMiddleware:
    """Las páginas que se ven con una sesión iniciada no se guardan en la caché del navegador.

    Así, después de cerrar sesión (o de que el login la cierre), los botones atrás y adelante vuelven a
    pedir la página al servidor, que exige iniciar sesión, en vez de mostrar una copia guardada con datos
    de la sesión anterior. Las respuestas que ya traen su propio Cache-Control (Admin, login, archivos)
    se dejan como están.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        user = getattr(request, 'user', None)
        if user is not None and user.is_authenticated and not response.has_header('Cache-Control'):
            add_never_cache_headers(response)  # no-cache, no-store, must-revalidate, private
            patch_vary_headers(response, ('Cookie',))
        return response
