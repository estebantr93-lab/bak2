from django.urls import path

from . import views

urlpatterns = [
    path('actividad/<int:pk>/', views.evidencias_actividad, name='evidencias_actividad'),
    path('<int:pk>/eliminar/', views.eliminar_evidencia, name='evidencia_delete'),
]
