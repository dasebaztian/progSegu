#!/usr/bin/env bash

while read -r linea; do    
    export "$linea"
done < <(ccdecrypt -c secretos.env.cpt)

docker-compose down && sleep .5 && docker-compose up -d
