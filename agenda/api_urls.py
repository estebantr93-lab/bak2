from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .api_views import CommitmentViewSet

router = DefaultRouter()
# Lista: /api/compromisos/ · Detalle: /api/compromisos/<id>/ (nombres de ruta compromiso-list y compromiso-detail)
router.register('compromisos', CommitmentViewSet, basename='compromiso')

urlpatterns = [
    path('', include(router.urls)),
]
