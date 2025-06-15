# Descripción general
WEBAdmin es una solución que permite a los administradores de sistema o SysAdmins realizar la gestión de múltiples servicios alojados en varíos servidores, a través de una aplicación web.

## Tecnologías utilizadas
- Pyhton 3.12
- MariaDB
- Nginx
- Django
- Docker
- Conexiones SSH

## Objetivo
Permitir la administración de servicios y servidores en una aplicación web, con el fin de realizar la gestión de los servicios en múltiples servidores.

## Características
- Permite agregar n cantidad de servidores.
- Permite agregar n cantidad de servicios por servidor.
- Cada servicio tiene una relación unica con un servidor.

## Seguridad
- Bloqueo de IPs para ataques de fuerza bruta.
- Implementación de cooldown para la congelación de cuentas en caso de ataques de fuerza bruta.
- Hashing de contraseñas.
- Uso de captchas para el formulario de login.
- Implementación de OTP a través del servicio de Telegram.
- Uso de HTTPS.
- Validaciones para los servicios
- Uso de contenedores docker.
