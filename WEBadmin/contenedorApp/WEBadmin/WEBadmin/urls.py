"""
URL configuration for WEBadmin project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
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
from django.urls import path
from WEBadmin import views as vistas

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', vistas.login),
    path('loginotp',vistas.login_otp),
    path('dashboard/', vistas.panel),
    path('signupservidor/', vistas.registrar_servidor),
    path('signupservicio/', vistas.registrar_servicio),
    path('controlarservicio/', vistas.controlar_servicio),
    path('estado_servicios/', vistas.estado_servicios),
    path('', vistas.login),
]
