#!/usr/bin/env python3
"""Rellena la columna 'AÑO DE LANZAMIENTO' en un CSV musical usando MusicBrainz.

El script lee el archivo CSV especificado, consulta MusicBrainz y completa
aquellas filas en las que falte el año de lanzamiento. Las filas que ya
contengan el año no se modifican.  Puede ejecutarse sobre un archivo nuevo o
sobre uno parcialmente completado.
"""
import pandas as pd
import musicbrainzngs
import unidecode
import time
import argparse
import tempfile
import os
import re

# Identifícate para cumplir las políticas de MusicBrainz
musicbrainzngs.set_useragent("VibraMusicYearFiller", "1.0", "contacto@tusitio.com")

def normalize_text(text):
    """Normaliza texto para búsqueda más efectiva."""
    if pd.isna(text):
        return ""
    
    # Convierte a string y elimina espacios extra
    text = str(text).strip()
    
    # Elimina caracteres especiales y acentos
    text = unidecode.unidecode(text)
    
    # Elimina contenido entre paréntesis como "(feat. Artist)"
    text = re.sub(r'\([^)]*\)', '', text).strip()
    
    # Elimina "feat", "ft", "featuring" etc.
    text = re.sub(r'\b(feat\.?|ft\.?|featuring)\b.*', '', text, flags=re.IGNORECASE).strip()
    
    return text

def clean_artist_name(artist):
    """Limpia nombres de artistas para mejorar búsquedas."""
    if pd.isna(artist):
        return ""
    
    artist = str(artist).strip()
    
    # Normaliza acentos
    artist = unidecode.unidecode(artist)
    
    # Si hay múltiples artistas separados por &, "and", "y", "/" o "," toma solo el primero
    parts = re.split(r'\s*(?:&|/|,|\band\b|\by\b)\s*', artist, maxsplit=1, flags=re.IGNORECASE)
    if parts:
        artist = parts[0].strip()
    
    return artist

def is_year_missing(value):
    """Devuelve True si el valor de año es vacío o no válido."""
    if pd.isna(value):
        return True
    text = str(value).strip().lower()
    if text in ("", "nan"):
        return True
    return False

def search_release_year(title, artist):
    """Busca el año de lanzamiento usando múltiples estrategias."""
    
    # Normaliza los términos de búsqueda
    clean_title = normalize_text(title)
    clean_artist = clean_artist_name(artist)
    
    if not clean_title or not clean_artist:
        return None
    
    # Estrategia 1: Búsqueda exacta de recording
    try:
        query = f'recording:"{clean_title}" AND artist:"{clean_artist}"'
        print(f"   Búsqueda 1: {query}")
        
        result = musicbrainzngs.search_recordings(query=query, limit=5)
        if result.get("recording-list"):
            for recording in result["recording-list"]:
                date = recording.get("first-release-date", "")
                if date and len(date) >= 4:
                    year = int(date[:4])
                    if 1900 <= year <= 2025:  # Validación de año razonable
                        return year
    except Exception as e:
        print(f"   Error en búsqueda 1: {e}")
    
    # Estrategia 2: Búsqueda más flexible
    try:
        query = f'"{clean_title}" AND artist:"{clean_artist}"'
        print(f"   Búsqueda 2: {query}")
        
        result = musicbrainzngs.search_recordings(query=query, limit=5)
        if result.get("recording-list"):
            for recording in result["recording-list"]:
                date = recording.get("first-release-date", "")
                if date and len(date) >= 4:
                    year = int(date[:4])
                    if 1900 <= year <= 2025:
                        return year
    except Exception as e:
        print(f"   Error en búsqueda 2: {e}")
    
    # Estrategia 3: Búsqueda por release en lugar de recording
    try:
        query = f'release:"{clean_title}" AND artist:"{clean_artist}"'
        print(f"   Búsqueda 3: {query}")
        
        result = musicbrainzngs.search_releases(query=query, limit=5)
        if result.get("release-list"):
            for release in result["release-list"]:
                date = release.get("date", "")
                if date and len(date) >= 4:
                    year = int(date[:4])
                    if 1900 <= year <= 2025:
                        return year
    except Exception as e:
        print(f"   Error en búsqueda 3: {e}")
    
    return None

def clean_csv_headers(df):
    """Limpia los headers del CSV eliminando espacios extra."""
    df.columns = df.columns.str.strip()
    return df

def process_file(input_path, output_path, batch_sleep=1.0):
    """Procesa el archivo por lotes para optimizar memoria y evitar bloqueos API."""
    
    print(f"🎵 Leyendo archivo: {input_path}")
    
    # Lee el archivo completo primero para verificar estructura
    try:
        df = pd.read_csv(input_path, dtype=str)
        df = clean_csv_headers(df)
        print(f"📊 Archivo cargado: {len(df)} filas, {len(df.columns)} columnas")
        print(f"📋 Columnas disponibles: {list(df.columns)}")
        
    except Exception as e:
        print(f"❌ Error leyendo archivo: {e}")
        return
    
    # Mapeo de columnas posibles
    title_column = None
    artist_column = None
    year_column = None
    
    # Busca columnas de título
    for col in df.columns:
        if any(keyword in col.upper() for keyword in ['CANCION', 'CANCIÓN', 'TITULO', 'TÍTULO', 'SONG', 'TRACK', 'NOMBRE']):
            title_column = col
            break
    
    # Busca columnas de artista
    for col in df.columns:
        if any(keyword in col.upper() for keyword in ['ARTISTA', 'ARTIST', 'INTERPRETE', 'INTÉRPRETE']):
            artist_column = col
            break
    
    # Busca columnas de año
    for col in df.columns:
        if any(keyword in col.upper() for keyword in ['AÑO', 'ANO', 'YEAR', 'FECHA', 'LANZAMIENTO']):
            year_column = col
            break
    
    if not title_column or not artist_column:
        print(f"❌ ERROR: No se encontraron las columnas necesarias.")
        print(f"   Título encontrado: {title_column}")
        print(f"   Artista encontrado: {artist_column}")
        print(f"   Columnas disponibles: {list(df.columns)}")
        return
    
    if not year_column:
        year_column = "AÑO DE LANZAMIENTO"
        df[year_column] = pd.NA
        print(f"✅ Creada columna de año: {year_column}")
    
    print(f"🎯 Usando columnas:")
    print(f"   Título: {title_column}")
    print(f"   Artista: {artist_column}")
    print(f"   Año: {year_column}")
    
    # Procesa en chunks para optimizar memoria
    chunk_size = 100
    total_processed = 0
    total_found = 0
    
    for start_idx in range(0, len(df), chunk_size):
        end_idx = min(start_idx + chunk_size, len(df))
        chunk = df.iloc[start_idx:end_idx].copy()
        
        print(f"\n📦 Procesando chunk {start_idx//chunk_size + 1}: filas {start_idx+1}-{end_idx}")
        
        for idx in chunk.index:
            # Verifica si ya tiene año
            current_year = chunk.at[idx, year_column]
            if not is_year_missing(current_year):
                continue
            
            title = str(chunk.at[idx, title_column]).strip()
            artist = str(chunk.at[idx, artist_column]).strip()
            
            if not title or not artist or title == "nan" or artist == "nan":
                continue
            
            print(f"\n🔍 Fila {idx+1}: Buscando '{title}' por '{artist}'")
            
            year = search_release_year(title, artist)
            
            if year:
                df.at[idx, year_column] = year
                chunk.at[idx, year_column] = year
                total_found += 1
                print(f"✅ Encontrado: {year}")
            else:
                print(f"❌ No encontrado")
            
            total_processed += 1
            
            # Pausa para respetar límites de API
            print(f"⏳ Esperando {batch_sleep} segundos...")
            time.sleep(batch_sleep)
    
    # Guarda el archivo final
    print(f"\n💾 Guardando archivo: {output_path}")
    df.to_csv(output_path, index=False)
    
    print(f"\n🎉 ¡Procesamiento completado!")
    print(f"   📊 Total procesado: {total_processed} canciones")
    print(f"   ✅ Años encontrados: {total_found}")
    print(f"   📈 Tasa de éxito: {(total_found/total_processed*100):.1f}%" if total_processed > 0 else "")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Añade el año de lanzamiento a un CSV de canciones usando MusicBrainz.")
    parser.add_argument("input", help="Ruta al CSV original")
    parser.add_argument("-o", "--output", help="CSV de salida (por defecto: agrega '_con_años' al nombre original)")
    parser.add_argument("--sleep", type=float, default=1.0, help="Segundos de espera entre llamadas (>=1 s recomendado)")
    parser.add_argument("--inplace", action="store_true", help="Sobrescribe el archivo de entrada")
    args = parser.parse_args()
    
    if args.inplace:
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
        temp_path = temp_file.name
        temp_file.close()
        output_path = temp_path
    else:
        if not args.output:
            base_name = os.path.splitext(args.input)[0]
            extension = os.path.splitext(args.input)[1]
            args.output = f"{base_name}_con_años{extension}"
        output_path = args.output

    print("🎵 Iniciando procesamiento de base musical...")
    print(f"📂 Archivo entrada: {args.input}")
    print(f"📂 Archivo salida: {output_path if not args.inplace else args.input}")
    print(f"⏱️  Pausa entre búsquedas: {args.sleep} segundos")

    process_file(args.input, output_path, args.sleep)

    if args.inplace:
        os.replace(output_path, args.input)
