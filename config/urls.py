"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path, reverse_lazy
from django.views.generic import RedirectView

from evidencias.views import archivo_evidencia
from funcionarios.views import IngresoView

from .views import inicio

# url= (y no pattern_name=) porque la ruta reset/<uidb64>/<token>/ no debe pasar sus argumentos al destino.
a_recuperacion = RedirectView.as_view(url=reverse_lazy('recuperar_solicitar'))

urlpatterns = [
    path('', inicio, name='inicio'),
    path('admin/login/', RedirectView.as_view(pattern_name='login', permanent=False, query_string=True)),
    path('admin/', admin.site.urls),
    # Recuperación con código temporal (antes del include para no chocar con las rutas de Django).
    path('accounts/recuperar/', include('funcionarios.urls')),
    # LoginView de Django: un solo mensaje para todo rechazo y cierra la sesión si se vuelve al login.
    # Va antes del include para reemplazar solo la ruta 'login'.
    path('accounts/login/', IngresoView.as_view(), name='login'),
    # La recuperación exigida es por código de 6 dígitos: el flujo por enlace de Django redirige a ella.
    path('accounts/password_reset/', a_recuperacion),
    path('accounts/password_reset/done/', a_recuperacion),
    path('accounts/reset/<uidb64>/<token>/', a_recuperacion),
    path('accounts/reset/done/', RedirectView.as_view(url=reverse_lazy('login'))),
    # logout y cambio de contraseña incluidos por Django.
    path('accounts/', include('django.contrib.auth.urls')),
    path('actividades/', include('actividades.urls')),
    path('evidencias/', include('evidencias.urls')),
    path('compromisos/', include('agenda.urls')),
    # API REST (Unidad 3): CRUD JSON de compromisos sobre el mismo modelo.
    path('api/', include('agenda.api_urls')),
    # Archivos subidos (MEDIA_URL): siempre pasan por la verificación de acceso, también en producción.
    path('archivos/<path:nombre>', archivo_evidencia, name='archivo_evidencia'),
    path('', include('dashboard.urls')),
]

# OWASP A09: los accesos denegados (403) quedan en la traza de auditoría.
handler403 = 'funcionarios.accesos.acceso_denegado'
