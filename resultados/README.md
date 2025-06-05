# Resultados de la base de datos

En esta carpeta se almacenarán los archivos CSV generados por el script `fill_release_year.py`.

Para ejecutar el script y completar la columna **AÑO DE LANZAMIENTO** se recomienda usar la siguiente secuencia de comandos:

```bash
# Instala las dependencias necesarias
pip install pandas musicbrainzngs unidecode

# Ejecuta el script con una pausa de al menos 1 segundo entre peticiones
python3 fill_release_year.py ../base_total_musical_notion.csv -o base_total_musical_notion_con_anos.csv --sleep 1.0
```

El parámetro `--sleep 1.0` es importante para cumplir con la política de uso de la API de MusicBrainz, que permite como máximo una petición por segundo.

El archivo de salida aparecerá en esta misma carpeta.
