from django.urls import path

from . import views

urlpatterns = [
    path('', views.CompromisoListView.as_view(), name='compromiso_list'),
    path('nuevo/', views.CompromisoCreateView.as_view(), name='compromiso_create'),
    path('<int:pk>/editar/', views.CompromisoUpdateView.as_view(), name='compromiso_update'),
    path('<int:pk>/eliminar/', views.CompromisoDeleteView.as_view(), name='compromiso_delete'),
    path('exportar/', views.CompromisoExportView.as_view(), name='compromiso_export'),
]
