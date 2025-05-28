#!/usr/bin/env bash

sleep 5

python -u manage.py makemigrations
python -u manage.py migrate

gunicorn --bind :8000 inseguro.wsgi:application --reload
#python /code/manage.py runserver 0.0.0.0:8080
