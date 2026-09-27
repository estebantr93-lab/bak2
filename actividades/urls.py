from django.urls import path

from . import views

urlpatterns = [
    path('', views.ActividadListView.as_view(), name='actividad_list'),
    path('nueva/', views.ActividadCreateView.as_view(), name='actividad_create'),
    path('<int:pk>/editar/', views.ActividadUpdateView.as_view(), name='actividad_update'),
    path('<int:pk>/eliminar/', views.ActividadDeleteView.as_view(), name='actividad_delete'),
    path('exportar/', views.ActividadExportView.as_view(), name='actividad_export'),

    path('atenciones/', views.AtencionListView.as_view(), name='atencion_list'),
    path('atenciones/nueva/', views.AtencionCreateView.as_view(), name='atencion_create'),
    path('atenciones/<int:pk>/editar/', views.AtencionUpdateView.as_view(), name='atencion_update'),
    path('atenciones/<int:pk>/eliminar/', views.AtencionDeleteView.as_view(), name='atencion_delete'),
    path('atenciones/exportar/', views.AtencionExportView.as_view(), name='atencion_export'),
]
