# Generated by Django 3.2.19 on 2025-06-18 22:34

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('database', '0004_servicio_servidor'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='servidor',
            name='nombre_servidor',
        ),
    ]
