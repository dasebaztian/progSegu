
import requests
import sys
import os
from datetime import datetime
import random
import hashlib

TOKEN = str(os.environ.get('TOKEN'))
CHAT_ID = str(os.environ.get('CHATID'))

def generar_mensaje() -> str:
    """Genera el código OTP a través de la fecha, entropia del sistema y una semilla

    Returns:
        str: Regresa el código OTP
    """    
    timestamp = int(datetime.now().timestamp() * 1_000_000)
    entropia_sistema = os.urandom(16)
    combinacion_semilla = str(timestamp).encode() + entropia_sistema
    semilla_hasheada = int(hashlib.sha256(combinacion_semilla).hexdigest(), 16)
    random.seed(semilla_hasheada)
    digits = "0123456789"
    random_string = ''.join(random.choice(digits) for _ in range(8))
    return random_string
    
def mandar_mensaje(mensaje: str) -> bool:
    """Se encarga de enviar el código al chat id seleccionado

    Args:
        mensaje (str): Código OTP para el sistema

    Returns:
        bool: Regresa True o False dependiendo de si se concreto el envío del mensaje
    """    
    url =  f'https://api.telegram.org/bot{TOKEN}/sendMessage'

    payload = {
        'chat_id': CHAT_ID,
        'text': mensaje,
        'parse_mode': 'Markdown'
    }
    try:
        requests.get(url, data=payload)
        print("Mande: " + url)
        return True
    except:
        return False
    
