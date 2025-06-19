from django.http import HttpRequest, HttpResponse, JsonResponse
from django.template import Template, Context
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect
import paramiko.ssh_exception

from WEBadmin import settings, hasher as hash, decoradores, login_chequeo as login_check, enviar_otp as telegram, fernet_metodos

from django.utils import timezone
from datetime import timedelta

from WEBadmin.forms import LoginForm
from database.models import Usuario, OTP, ContadorIntentos, Servidor, Servicio

from django.core.validators import validate_ipv46_address
from django.core.exceptions import ValidationError
import re, paramiko, io

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
        

        if not ssh_key:
            errores.append("La llave SSH no puede estar vacía.")
        elif not ('BEGIN OPENSSH PRIVATE KEY' in ssh_key or 'BEGIN RSA PRIVATE KEY' in ssh_key):
            errores.append("La llave privada SSH no tiene un formato válido.")
        else:
            try:
                key_obj = paramiko.RSAKey.from_private_key(io.StringIO(ssh_key))
            except paramiko.ssh_exception:
                errores.append("No se pudo leer la llave privada SSH. ¿Es válida y sin passphrase?")

        if not errores:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                ssh.connect(
                    hostname=ip,
                    username=usuario,
                    pkey=key_obj,
                    timeout=5
                )
                ssh.close()

            except Exception as e:
                errores.append(f"No se pudo establecer conexión SSH: {str(e)}")
    if not errores:
            llave_cifrada = fernet_metodos.encriptar_llave_ssh(ssh_key)
            Servidor.objects.create(ip=ip,
                                    llave_ssh = llave_cifrada,
                                    usuario=usuario)
            
            return redirect('/dashboard')
    
    return render(request, 'panel.html', {'errores': errores, 'servidores': Servidor.objects.all()})

@decoradores.verificar_login_otp
def registrar_servicio(request):
    t = "base.html"
    errores = []
    if request.method == 'GET':
        return render(request,t)
    
def obtener_estado_via_ssh(servidor, servicio_nombre):
    try:
        key_stream = io.StringIO(fernet_metodos.desencriptar_llave_ssh(servidor.llave_ssh))
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