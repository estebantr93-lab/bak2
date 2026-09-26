from django.urls import path

from . import views

urlpatterns = [
    path('', views.solicitar, name='recuperar_solicitar'),
    path('codigo/', views.ingresar_codigo, name='recuperar_codigo'),
    path('nueva/', views.nueva_contrasena, name='recuperar_nueva'),
]
