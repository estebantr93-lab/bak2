from django.urls import path

from . import views

urlpatterns = [
    path('', views.EvidenciaListView.as_view(), name='evidencia_list'),
    path('nueva/', views.EvidenciaCreateView.as_view(), name='evidencia_create'),
    path('<int:pk>/editar/', views.EvidenciaUpdateView.as_view(), name='evidencia_update'),
    path('<int:pk>/eliminar/', views.EvidenciaDeleteView.as_view(), name='evidencia_delete'),
    path('exportar/', views.EvidenciaExportView.as_view(), name='evidencia_export'),
]
