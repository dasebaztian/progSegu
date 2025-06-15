from django.http import HttpRequest, HttpResponse, JsonResponse
from django.template import Template, Context
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect


from django.utils import timezone
from datetime import timedelta
import paramiko
from os import urandom

from WEBadmin import settings, hasher as hash, decoradores, login_chequeo as login_check, enviar_otp as telegram
from WEBadmin.forms import LoginForm
from WEBadmin.verificaciones import puerto_abierto

from database.models import Usuario, OTP, ContadorIntentos, Servidor, Servicio



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
            request.session['logueado_otp'] = True
            otp_valido.delete()
            return redirect('/dashboard')
            
        else:
            request.session.flush()
            ultimo_otp = OTP.objects.all().last().delete()
            return redirect('/login')

@decoradores.verificar_login_otp
def panel(request):
    t = "panel.html"
    errores = []
    if request.method == 'GET':
        servidores = Servidor.objects.all()
        servicios = Servicio.objects.select_related('servidor').all()

        for servicio in servicios:
            ip = str(servicio.servidor.ip)
            puerto = servicio.puerto

            if puerto_abierto(ip, puerto):
                servicio.estado = "activo"
            else:
                servicio.estado = "inactivo"
            servicio.save()

        return render(request, t, {
            "servidores": servidores,
            "servicios": Servicio.objects.select_related('servidor').all(),
            "errores": errores
        })

@decoradores.verificar_login_otp
def registrar_servidor(request):
    t = "registrar_servidor.html"
    errores = []
    if request.method == 'GET':
        return render(request,t)
    elif request.method == 'POST':
        nombre_servidor = request.POST.get('nombre_servidor', '').strip()
        usuario_ssh = request.POST.get('usuario', '').strip()
        ip = request.POST.get('ip', '').strip()
        puerto = request.POST.get('puerto', '').strip()
        password = request.POST.get('password', '').strip()

        if not all([nombre_servidor, usuario_ssh, ip, puerto, password]):
            errores.append("Todos los campos son obligatorios.")
            return render(request, t, {'errores': errores})

        try:
            puerto = int(puerto)
            if puerto < 1 or puerto > 65535:
                raise ValueError("Puerto fuera de rango.")
        except ValueError:
            errores.append("El puerto debe ser un número entre 1 y 65535.")
            return render(request, t, {'errores': errores})

        if Servidor.objects.filter(ip=ip).exists():
            errores.append("Ya existe un servidor registrado con esa IP.")
            return render(request, t, {'errores': errores})

        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(
                hostname=ip,
                port=puerto,
                username=usuario_ssh,
                password=password,
                timeout=5
            )
            client.close()

            salt = urandom(16)
            servidor = Servidor.objects.create(
                nombre_servidor=nombre_servidor,
                usuario=usuario_ssh,
                ip=ip,
                puerto=puerto,
                salt_passwd=salt,
                password=hash.hashearPassword(password, salt)
            )

            Servicio.objects.create(
                nombre="ssh",
                servidor=servidor,
                puerto=puerto,
                estado="activo"
            )

            return render(request, t, {'mensaje': f"Servidor '{nombre_servidor}' registrado correctamente."})

        except Exception as e:
            errores.append(f"No se pudo conectar con el servidor: {str(e)}")
            return render(request, t, {'errores': errores})

@decoradores.verificar_login_otp
def registrar_servicio(request):
    t = "registrar_servicio.html"
    errores = []

    if request.method == 'GET':
        servidores = Servidor.objects.all()
        return render(request, t, {'servidores': servidores})

    elif request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        ip_servidor = request.POST.get('servidor', '').strip()
        puerto = request.POST.get('puerto', '').strip()

        if not all([nombre, ip_servidor, puerto]):
            errores.append("Todos los campos son obligatorios.")
        else:
            try:
                puerto = int(puerto)
                if puerto < 1 or puerto > 65535:
                    raise ValueError()
            except ValueError:
                errores.append("El puerto debe ser un número entre 1 y 65535.")

        try:
            servidor = Servidor.objects.get(ip=ip_servidor)
        except Servidor.DoesNotExist:
            errores.append("Servidor no encontrado.")

        if not errores:
            servicio_existente = Servicio.objects.filter(servidor=servidor, puerto=puerto).first()
            if servicio_existente:
                errores.append("Ya existe un servicio en ese puerto para este servidor.")
            else:
                estado = "activo" if puerto_abierto(str(servidor.ip), puerto) else "inactivo"
                Servicio.objects.create(
                    nombre=nombre,
                    servidor=servidor,
                    puerto=puerto,
                    estado=estado
                )
                return render(request, t, {
                    'mensaje': f"Servicio '{nombre}' registrado correctamente.",
                    'servidores': Servidor.objects.all()
                })

        return render(request, t, {
            'errores': errores,
            'servidores': Servidor.objects.all()
        })