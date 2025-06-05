# Music Database Build

Este repositorio contiene la base de datos musical `base_total_musical_notion.csv`.

Para completar la columna de **AÑO DE LANZAMIENTO** se utiliza el script `fill_release_year.py` que consulta MusicBrainz.

Los archivos generados se guardan en la carpeta `resultados`.

## Uso rapido

```bash
pip install pandas musicbrainzngs unidecode
python3 fill_release_year.py base_total_musical_notion.csv -o resultados/base_total_musical_notion_con_anos.csv --sleep 1.0
```

El archivo de salida `base_total_musical_notion_con_anos.csv` incluirá los años de lanzamiento obtenidos y se encontrará dentro de `resultados/`.
