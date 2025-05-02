from django.db import models

# Create your models here.
class Usuario(models.Model):
    usuario = models.CharField(max_length=5, unique=True)
    salt_passwd = models.BinaryField(default=b'')
    passwd = models.CharField(max_length=129)
