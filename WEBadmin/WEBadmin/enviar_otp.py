
import requests
import sys
import os
from datetime import datetime
import random
import hashlib

TOKEN = str(os.environ.get('TOKEN'))
CHAT_ID = str(os.environ.get('CHATID'))

# CUIDADO la rutina usa get, hay que cambiar por POST
def generar_mensaje() -> str:
    timestamp = int(datetime.now().timestamp() * 1_000_000)
    entropia_sistema = os.urandom(16)
    combinacion_semilla = str(timestamp).encode() + entropia_sistema
    semilla_hasheada = int(hashlib.sha256(combinacion_semilla).hexdigest(), 16)
    random.seed(semilla_hasheada)
    digits = "0123456789"
    random_string = ''.join(random.choice(digits) for _ in range(8))
    return random_string
    
def mandar_mensaje(mensaje: str):
    url =  f'https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&parse_mode=Markdown&text={mensaje}'
    try:
        requests.get(url)
        print("Mande: " + url)
        print(TOKEN)
        print(CHAT_ID)
        return True
    except:
        return False
    
