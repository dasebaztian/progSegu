from django.http import HttpRequest, HttpResponse, JsonResponse
from django.template import Template, Context
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect

from WEBadmin import settings
from WEBadmin import hasher as hash
from django.utils import timezone
from datetime import timedelta
from WEBadmin import decoradores
from WEBadmin import login_chequeo as login_check
from WEBadmin.forms import LoginForm
from database.models import Usuario
from database.models import OTP
from database.models import ContadorIntentos
from WEBadmin import enviar_otp as telegram

def campo_vacio(campo: str) -> str:
    """Campo vacio se encarga de validar que la entrada del usuario no este vacia

    Args:
        campo (string): Texto enviado por el usuario

    Returns:
        String: regresa el campo sin espacios
    """    
    return campo.strip() == ''

def login(request: HttpRequest) -> HttpResponse:
    """Se encarga de validar el tipo de petición, en casos de GET responde con la página de login,
    mientras que en casos de POST esta hace las validaciones necesarias para autenticar al usuario dentro
    del sistema.

    Args:
        request (HttpRrequest): Solicitud del cliente

    Returns:
        HttpResponse: Respuesta del servidor de acuerdo a las validaciones o tipo de solicitud.
    """    
    errores = []
    if request.method == 'GET':
        form = LoginForm()
        request.session['logueado'] = False
        request.session['usuario'] = ''
        request.session['logueado_otp'] = False
        return render(request, 'login.html', {'form': form}) 
    elif request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            usuario = form.cleaned_data['usuario']
            passwd = form.cleaned_data['passwd']

            permitido, intentos = login_check.tienes_intentos_login(request)
            if not permitido:
                errores.append(f'Debes esperar {settings.SEGUNDOS_INTENTO} segundos antes de volver a intentar.')
                return render(request, 'login.html', {'form': form, 'errores': errores})
            try:
                usuario_bd = Usuario.objects.get(usuario=usuario)
                salt_bd = usuario_bd.salt_passwd
                passwd_bd = usuario_bd.passwd
                if hash.verificarPassword(passwd, passwd_bd, salt_bd):
                    ip = login_check.get_client_ip(request)
                    try:
                        registro = ContadorIntentos.objects.get(pk=ip)
                        registro.contador = 0
                        registro.save()
                    except ContadorIntentos.DoesNotExist:
                        pass
                    request.session['logueado'] = True
                    request.session['usuario'] = usuario
                    return redirect('/loginotp')
                else:
                    errores.append(f"Usuario y/o Contraseña incorrectos. Intento {intentos} de {settings.NUMERO_INTENTOS}")
            except Usuario.DoesNotExist:
                errores.append(f"Usuario y/o Contraseña incorrectos. Intento {intentos} de {settings.NUMERO_INTENTOS}")
        else:
            errores.append("Formulario inválido. Verifica los campos.")
        return render(request, 'login.html', {'form': form, 'errores': errores})

@decoradores.verificar_login
def login_otp(request: HttpRequest) -> HttpResponse:
    """Esta vista responde a cuando un usuario ya autenticado por contraseña necesita autenticarse a través de su OTP
    en este caso el servido genera el OTP y de acuerdo a la petición del cliente hace las validaciones
    necesarias

    Args:
        request (HttpRequest): Solicitud del cliente

    Returns:
        HttpResponse: Respuesta del servidor
    """    
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
                fecha_vencimiento=timezone.localtime(timezone.now()) + timedelta(minutes=1)
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
            # Redirigir al dashboard u otra página protegida
            request.session['logueado_otp'] = True
            return redirect('/dashboard')
            otp_valido.delete()
        else:
            request.session['logueado'] = True
            return render(request, t, {'errores': ['Código incorrecto o expirado.']})
            otp_valido.delete


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