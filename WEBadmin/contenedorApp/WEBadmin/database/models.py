from django.db import models

from datetime import timedelta
from django.utils import timezone
from django.core.validators import MaxValueValidator, MinValueValidator



def default_expiration():
    return timezone.localtime(timezone.now()) + timedelta(minutes=10)

# Create your models here.
class Usuario(models.Model):
    usuario = models.CharField(max_length=5, unique=True)
    salt_passwd = models.BinaryField(default=b'')
    passwd = models.CharField(max_length=129)

class OTP(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    password_otp = models.CharField(max_length=8)
    fecha_vencimiento = models.DateTimeField(default=default_expiration)

class ContadorIntentos(models.Model):
    ip = models.GenericIPAddressField(primary_key=True)
    contador = models.PositiveIntegerField()
    ultimo_intento = models.DateTimeField()

class Servidor(models.Model):
    nombre_servidor = models.CharField(max_length=50, unique=True)
    usuario = models.CharField(max_length=50)
    ip = models.GenericIPAddressField(primary_key=True)
    puerto = models.PositiveIntegerField(
    default=22,
    validators=[
        MinValueValidator(1),
        MaxValueValidator(65535)
    ]
)
    salt_passwd = models.BinaryField(default=b'')
    password = models.CharField(max_length=129)

class Servicio(models.Model):
    nombre = models.CharField(max_length=100)
    servidor = models.ForeignKey(Servidor, on_delete=models.CASCADE)
    puerto = models.PositiveIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(65535)
        ]
    )
    estado = models.CharField(max_length=20, default="desconocido")