from django.http import HttpResponse, JsonResponse
from django.template import Template, Context
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect

from WEBadmin import hasher as hash
from WEBadmin import decodadores
from WEBadmin.forms import LoginForm
from database.models import Usuario

def campo_vacio(campo):
    return campo.strip() == ''

def login(request):
    errores = []
    if request.method == 'GET':
        form = LoginForm()
        request.session['logueado'] = False
        request.session['usuario'] = ''
        return render(request, 'login.html', {'form': form})
    
    elif request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            usuario = form.cleaned_data['usuario']
            passwd = form.cleaned_data['passwd']
            try:
                usuario_bd = Usuario.objects.get(usuario=usuario)
                salt_bd = usuario_bd.salt_passwd
                passwd_bd = usuario_bd.passwd
                if hash.verificarPassword(passwd, passwd_bd, salt_bd):
                    request.session['logueado'] = True
                    request.session['usuario'] = usuario
                    return redirect('/dashboard')
                else:
                    errores.append("Usuario y/o Contraseña incorrectos")
            except Usuario.DoesNotExist:
                errores.append("Usuario y/o Contraseña incorrectos")
        else:
            errores.append("Formulario inválido. Verifica los campos.")
        return render(request, 'login.html', {'form': form, 'errores': errores})

@decodadores.verificar_login
def panel(request):
    t = "base.html"
    errores = []
    if request.method == 'GET':
        return render(request,t)

@decodadores.verificar_login 
def registrar_servidor(request):
    t = "base.html"
    errores = []
    if request.method == 'GET':
        return render(request,t)

@decodadores.verificar_login 
def registrar_servicio(request):
    t = "base.html"
    errores = []
    if request.method == 'GET':
        return render(request,t)