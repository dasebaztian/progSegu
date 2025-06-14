import socket
import subprocess

def esta_activo(ip):
    """Hace ping al servidor."""
    try:
        salida = subprocess.run(['ping', '-c', '1', '-W', '1', ip], stdout=subprocess.DEVNULL)
        return salida.returncode == 0
    except Exception:
        return False

def puerto_abierto(ip, puerto):
    """Verifica si el puerto está abierto en el servidor."""
    try:
        with socket.create_connection((ip, puerto), timeout=1):
            return True
    except Exception:
        return False