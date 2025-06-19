from cryptography.fernet import Fernet
from django.conf import settings

def encriptar_llave_ssh(llave_ssh: str):
    llave_maestra = Fernet(settings.CLAVE_FERNET)
    return str(llave_maestra.encrypt(llave_ssh.encode()))

def desencriptar_llave_ssh(llave_ssh_encriptada: str):
    llave_maestra = Fernet(settings.CLAVE_FERNET)
    return str(llave_maestra.decrypt(llave_ssh_encriptada.encode()).decode())