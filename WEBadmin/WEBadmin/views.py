from django.http import HttpResponse, JsonResponse
from django.template import Template, Context
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect

from WEBadmin import hasher as hash
from django.utils import timezone
from datetime import timedelta
from WEBadmin import decoradores
from WEBadmin.forms import LoginForm
from database.models import Usuario
from database.models import OTP
from WEBadmin import enviar_otp as telegram

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
                    return redirect('/loginotp')
                else:
                    errores.append("Usuario y/o Contraseña incorrectos")
            except Usuario.DoesNotExist:
                errores.append("Usuario y/o Contraseña incorrectos")
        else:
            errores.append("Formulario inválido. Verifica los campos.")
        return render(request, 'login.html', {'form': form, 'errores': errores})

@decoradores.verificar_login
def login_otp(request):
    t = "otp.html"
    if request.method == 'GET':
        usuario_nombre = request.session.get('usuario')

        usuario_obj = Usuario.objects.get(usuario=usuario_nombre)

        codigo = telegram.generar_mensaje()

        # Enviar mensaje y guardar solo si fue exitoso
        if telegram.mandar_mensaje(codigo):
            OTP.objects.create(
                usuario=usuario_obj,
                password_otp=codigo,
                fecha_vencimiento=timezone.localtime(timezone.now()) + timedelta(minutes=10)
            )
            return render(request, t)
        else:
            return render(request, t, {'errores': ['No se pudo enviar el código. Intenta más tarde.']})
    elif request.method == 'POST':
        codigo_ingresado = request.POST.get('otp', '').strip()

        if not codigo_ingresado.isdigit() or len(codigo_ingresado) != 8:
            return render(request, t, {'errores': ['El código debe de estar en el formato adecuado.']})
        
        usuario_nombre = request.session.get('usuario')
        ahora = timezone.localtime(timezone.now())
        usuario_obj = Usuario.objects.get(usuario=usuario_nombre)

        # Buscar un OTP válido
        otp_valido = OTP.objects.filter(
            usuario=usuario_obj,
            password_otp=codigo_ingresado,
            fecha_vencimiento__gte=ahora
        ).first()

        if otp_valido:
            # (Opcional) eliminar el OTP usado
            otp_valido.delete()

            # Redirigir al dashboard u otra página protegida
            request.session['logueado_otp'] = True
            return redirect('/dashboard')
        else:
            return render(request, t, {'errores': ['Código incorrecto o expirado.']})


@decoradores.verificar_login_otp
def panel(request):
    t = "base.html"
    errores = []
    if request.method == 'GET':
        return render(request,t)

@decoradores.verificar_login_otp
def registrar_servidor(request):
    t = "base.html"
    errores = []
    if request.method == 'GET':
        return render(request,t)

@decoradores.verificar_login_otp
def registrar_servicio(request):
    t = "base.html"
    errores = []
    if request.method == 'GET':
        return render(request,t)