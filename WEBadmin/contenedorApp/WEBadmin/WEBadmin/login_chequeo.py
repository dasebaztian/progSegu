from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from WEBadmin import settings
from database import models
from datetime import datetime
from datetime import timezone
from database.models import ContadorIntentos


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    print(ip)
    return ip

def ip_registrada(ip: str) -> bool:
    """
    True si la IP ya está en la BD.

    ip
    returns: bool 
    """
    try:
        models.ContadorIntentos.objects.get(pk=ip)
        return True
    except:
        return False
    

def fecha_en_ventana(fecha, segundos_ventana=settings.SEGUNDOS_INTENTO) -> bool:
    """
    True si la fecha está en la ventana de tiempo.

    fecha
    returns: bool 
    """
    actual = datetime.now(timezone.utc)
    diferencia = (actual - fecha).seconds
    return diferencia <= segundos_ventana
    
    


def tienes_intentos_login(request) -> tuple[bool, int]:
    ip = get_client_ip(request)
    actual = datetime.now(timezone.utc)

    if not ip_registrada(ip):
        ContadorIntentos.objects.create(ip=ip, contador=1, ultimo_intento=actual)
        return True, 1

    registro = ContadorIntentos.objects.get(pk=ip)
    if not fecha_en_ventana(registro.ultimo_intento):
        registro.contador = 1
        registro.ultimo_intento = actual
        registro.save()
        return True, 1

    if registro.contador < settings.NUMERO_INTENTOS:
        registro.contador += 1
        registro.ultimo_intento = actual
        registro.save()
        return True, registro.contador
    
    return False, registro.contador