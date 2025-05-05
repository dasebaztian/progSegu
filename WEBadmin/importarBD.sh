#!/usr/bin/env bash

# Cargar variables desde archivo cifrado
while read -r linea; do    
    export "$linea"
done < <(ccdecrypt -c secretos.env.cpt)

# Importar directamente desde el archivo encriptado sin tocar disco
ccdecrypt -c ./web.sql.enc | mysql -u"$DB_USER" -p"$DB_PASS" && echo "Importación completada sin escribir archivos temporales" || echo "❌ Error al desencriptar o importar la base de datos"
