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
from database.models import Servidor, Servicio
from WEBadmin import enviar_otp as telegram
from django.core.validators import validate_ipv46_address
from django.core.exceptions import ValidationError
import re
import paramiko
import io


USUARIO_REGEX = re.compile(r'^[a-zA-Z][a-zA-Z0-9_-]{1,49}$')

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
        for servidor in servidores:
            servicios_estado = []
            for servicio in servidor.servicio_set.all():
                estado = obtener_estado_via_ssh(servidor, servicio.nombre)
                servicios_estado.append((servicio.nombre, estado))
            servidor.servicios_con_estado = servicios_estado
        return render(request, t, {'servidores': servidores})

@decoradores.verificar_login_otp
def controlar_servicio(request):
    if request.method == 'POST':
        servidor_ip = request.POST.get('servidor_ip')
        servicio_nombre = request.POST.get('servicio_nombre')
        accion = request.POST.get('accion')  # 'start' o 'stop'
        errores = []
        if accion in ['start', 'stop', 'restart']:

        ##Falta sanitizar entrada del nombre del servicio
            try:
                servidor = Servidor.objects.get(ip=servidor_ip)
            except Servidor.DoesNotExist:
                errorres.append(request, f"Servidor '{servidor_ip}' no encontrado.")
            try:
                comando = f"sudo systemctl {accion} {servicio_nombre}"
                ejecutar_comando_ssh(servidor, comando)
            except Exception:
                errores.append(f'Error al ejecutar {accion} en {servicio_nombre}')
            if errores:
                return render(request, 'panel.html', {'errores': errores, 'servidores': Servidor.objects.all()})
    return redirect('/dashboard')

def ejecutar_comando_ssh(servidor, comando):
    try:
        key = paramiko.RSAKey.from_private_key(io.StringIO(servidor.llave_ssh))
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname=servidor.ip,
            port=servidor.puerto,
            username=servidor.usuario,
            pkey=key
        )
        stdin, stdout, stderr = ssh.exec_command(comando)
        estado = stderr.read().decode().strip()
        ssh.close()
    except Exception as e:
        print(e) 

#Se hace del lado del servidor no se necesita auth porque ya se valida en el panel jsj
def obtener_estado_via_ssh(servidor, servicio_nombre):
    try:
        key_stream = io.StringIO(servidor.llave_ssh)
        key = paramiko.RSAKey.from_private_key(key_stream)

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname=servidor.ip,
            port=servidor.puerto,
            username=servidor.usuario,
            pkey=key,
            timeout=5
        )

        stdin, stdout, stderr = ssh.exec_command(f'systemctl is-active {servicio_nombre}')
        estado = stdout.read().decode().strip()
        ssh.close()
        return estado
    except Exception as e:
        print(e)

@decoradores.verificar_login_otp
def registrar_servidor(request):
    errores = []
    if request.method == 'POST':
        ip = request.POST.get('ip', '').strip()
        ssh_key = request.POST.get('llave_ssh', '').strip()
        usuario = request.POST.get('usuario', '').strip()

        try:
            validate_ipv46_address(ip)  
        except ValidationError:
    
            if not re.match(r'^(?=.{1,253}$)((?!-)[A-Za-z0-9-]{1,63}(?<!-)\.)+[A-Za-z]{2,}$', ip):
                errores.append("La IP o dominio no es válido.")
        
        # Validación de llave SSH (muy básica, solo comprobamos que no esté vacía)
        if not ssh_key:
            errores.append("La llave SSH no puede estar vacía.")

        if not errores:
            Servidor.objects.create(ip=ip, llave_ssh=ssh_key, usuario=usuario)
            return redirect('/dashboard')

    return render(request, 'panel.html', {'errores': errores, 'servidores': Servidor.objects.all()})

@decoradores.verificar_login_otp
def registrar_servicio(request):
    errores = []
    servidores = Servidor.objects.all()
    
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        servidor_ip = request.POST.get('servidor_ip')

        try:
            servidor = Servidor.objects.get(ip=servidor_ip)
        except (Servidor.DoesNotExist, ValueError, TypeError):
            errores.append(f"Servidor {servidor_ip} seleccionado no es válido.")
            servidor = None

        if not errores and servidor:
            Servicio.objects.create(nombre=nombre, servidor=servidor)
            return redirect('/dashboard')

    return render(request, 'panel.html', {'errores': errores, 'servidores': servidores })
