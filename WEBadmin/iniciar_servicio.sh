#!/usr/bin/env bash

while read -r linea; do    
    export "$linea"
    echo "$linea"
done < <(ccdecrypt -c secretos.env.cpt)

python3 manage.py runserver 0.0.0.0:8000