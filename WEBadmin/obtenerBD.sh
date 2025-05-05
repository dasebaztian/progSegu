#!/usr/bin/env bash

while read -r linea; do    
    export "$linea"
#    echo "$linea"
done < <(ccdecrypt -c secretos.env.cpt)

mysqldump --add-drop-database --add-drop-table --databases "$DB_NAME" -u"$DB_USER" -p"$DB_PASS" > ./web.sql && echo "Se creo el SQL, ahora encriptalo con una contraseña:"
ccrypt -e ./web.sql && echo "SQL encriptado" || echo "Error al ecriptar"