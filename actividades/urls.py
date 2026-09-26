from django.urls import path

from . import views

urlpatterns = [
    path('', views.ActividadListView.as_view(), name='actividad_list'),
    path('nueva/', views.ActividadCreateView.as_view(), name='actividad_create'),
    path('<int:pk>/editar/', views.ActividadUpdateView.as_view(), name='actividad_update'),
    path('<int:pk>/eliminar/', views.ActividadDeleteView.as_view(), name='actividad_delete'),
]
