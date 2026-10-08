"""Rutas de la API (todas bajo /api/, ver config/urls.py)."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from . import views
from .autenticacion import ObtenerTokenView

router = DefaultRouter()
# Principales: CRUD completo
router.register('actividades', views.ActivityViewSet, basename='actividad')
router.register('atenciones', views.SocialCaseViewSet, basename='atencion')
router.register('compromisos', views.CommitmentViewSet, basename='compromiso')
router.register('evidencias', views.EvidenceViewSet, basename='evidencia')
# Operacionales: solo GET lista y detalle
router.register('validaciones', views.ValidationViewSet, basename='validacion')
router.register('seguimientos', views.CommitmentFollowUpViewSet, basename='seguimiento')

urlpatterns = [
    path('token/', ObtenerTokenView.as_view(), name='token_obtener'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_renovar'),
    path('', include(router.urls)),
]
