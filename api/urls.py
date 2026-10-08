"""Rutas de la API (todas bajo /api/, ver config/urls.py)."""
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .autenticacion import ObtenerTokenView

urlpatterns = [
    path('token/', ObtenerTokenView.as_view(), name='token_obtener'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_renovar'),
]
