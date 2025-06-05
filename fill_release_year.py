#!/usr/bin/env python3
"""Versión CORREGIDA que busca releases asociados para obtener fechas.

El problema era que los recordings no siempre tienen first-release-date,
pero sí tienen releases asociados con fechas específicas.
"""
import pandas as pd
import musicbrainzngs
import unidecode
import time
import argparse
import tempfile
import os
import re
from difflib import SequenceMatcher

# Identifícate para cumplir las políticas de MusicBrainz
musicbrainzngs.set_useragent("VibraMusicYearFiller", "3.0", "contacto@tusitio.com")

def similarity(a, b):
    """Calcula la similitud entre dos strings."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def normalize_text(text):
    """Normalización mejorada de texto."""
    if pd.isna(text):
        return ""
    
    text = str(text).strip()
    if not text or text.lower() == 'nan':
        return ""
    
    # Elimina espacios extra
    text = ' '.join(text.split())
    return text

def clean_artist_name(artist):
    """Limpia nombres de artistas con múltiples variantes."""
    if pd.isna(artist):
        return []
    
    artist = str(artist).strip()
    if not artist or artist.lower() == 'nan':
        return []
    
    variants = []
    
    # Variante original
    variants.append(artist)
    
    # Sin acentos
    no_accents = unidecode.unidecode(artist)
    variants.append(no_accents)
    
    # Variantes de capitalización
    variants.append(artist.title())  # "Charly Garcia" 
    variants.append(artist.lower())   # "charly garcia"
    variants.append(no_accents.title())  # "Charly Garcia"
    variants.append(no_accents.lower())  # "charly garcia"
    
    # Solo el primer artista si hay colaboraciones
    parts = re.split(r'\s*(?:&|/|,|\band\b|\by\b|\bfeat\.?\b|\bft\.?\b)\s*', artist, maxsplit=1, flags=re.IGNORECASE)
    if len(parts) > 1:
        main_artist = parts[0].strip()
        variants.append(main_artist)
        variants.append(unidecode.unidecode(main_artist))
        variants.append(main_artist.title())
        variants.append(main_artist.lower())
    
    return list(set(filter(None, variants)))

def get_year_from_releases(recording_id):
    """Obtiene el año más temprano de los releases asociados a una grabación."""
    try:
        print(f"      🔍 Buscando releases para recording ID: {recording_id}")
        
        # Busca releases que contengan esta grabación
        result = musicbrainzngs.search_releases(query=f'rid:{recording_id}', limit=10)
        releases = result.get("release-list", [])
        
        print(f"      📊 Releases encontrados: {len(releases)}")
        
        years = []
        for release in releases:
            date = release.get("date", "")
            title = release.get("title", "")
            print(f"         📅 '{title}' - Fecha: '{date}'")
            
            if date and len(date) >= 4:
                try:
                    year = int(date[:4])
                    if 1900 <= year <= 2025:
                        years.append(year)
                        print(f"         ✅ Año válido: {year}")
                except (ValueError, TypeError):
                    continue
        
        if years:
            earliest_year = min(years)
            print(f"      🎯 Año más temprano: {earliest_year}")
            return earliest_year
        
        return None
        
    except Exception as e:
        print(f"      ❌ Error buscando releases: {e}")
        return None

def search_release_year_fixed(title, artist):
    """Versión CORREGIDA que busca en recordings Y sus releases asociados."""
    
    if not title or not artist:
        return None
    
    title_clean = normalize_text(title)
    artist_variants = clean_artist_name(artist)
    
    print(f"   🎵 '{title_clean}' por '{artist_variants[0] if artist_variants else 'N/A'}'")
    print(f"   🔍 Variantes de artista ({len(artist_variants)}): {artist_variants[:3]}...")  # Muestra solo las primeras 3
    
    # Estrategia 1: Búsqueda directa de releases (más rápida)
    print(f"   📀 ESTRATEGIA 1: Búsqueda directa de releases")
    for artist_var in artist_variants[:3]:  # Solo las 3 primeras variantes
        try:
            query = f'release:"{title_clean}" AND artist:"{artist_var}"'
            print(f"      🔍 RELEASE: {query}")
            
            result = musicbrainzngs.search_releases(query=query, limit=5)
            releases = result.get("release-list", [])
            
            print(f"      📊 Releases encontrados: {len(releases)}")
            
            for release in releases:
                date = release.get("date", "")
                found_title = release.get("title", "")
                
                # Obtener artista
                found_artist = ""
                artist_info = release.get("artist-credit", [])
                if artist_info:
                    found_artist = artist_info[0].get("artist", {}).get("name", "")
                
                print(f"         📅 '{found_title}' por '{found_artist}' - Fecha: '{date}'")
                
                if date and len(date) >= 4:
                    try:
                        year = int(date[:4])
                        if 1900 <= year <= 2025:
                            # Validación permisiva
                            title_sim = similarity(title_clean, found_title)
                            artist_sim = similarity(artist_var, found_artist)
                            
                            print(f"         📈 Similitud título: {title_sim:.2f}, artista: {artist_sim:.2f}")
                            
                            if title_sim >= 0.6 and artist_sim >= 0.5:
                                print(f"         ✅ ENCONTRADO VÍA RELEASE: {year}")
                                return year
                    except (ValueError, TypeError):
                        continue
            
            time.sleep(0.5)
            
        except Exception as e:
            print(f"      ❌ Error en búsqueda de release: {e}")
            continue
    
    # Estrategia 2: Búsqueda de recordings y luego sus releases
    print(f"   🎤 ESTRATEGIA 2: Recordings + releases asociados")
    for artist_var in artist_variants[:2]:  # Solo las 2 primeras para no ser demasiado lento
        try:
            query = f'recording:"{title_clean}" AND artist:"{artist_var}"'
            print(f"      🔍 RECORDING: {query}")
            
            result = musicbrainzngs.search_recordings(query=query, limit=3)
            recordings = result.get("recording-list", [])
            
            print(f"      📊 Recordings encontrados: {len(recordings)}")
            
            for recording in recordings:
                recording_id = recording.get("id", "")
                found_title = recording.get("title", "")
                
                # Obtener artista
                found_artist = ""
                artist_info = recording.get("artist-credit", [])
                if artist_info:
                    found_artist = artist_info[0].get("artist", {}).get("name", "")
                
                print(f"         🎵 '{found_title}' por '{found_artist}' - ID: {recording_id}")
                
                if recording_id:
                    # Validación antes de buscar releases
                    title_sim = similarity(title_clean, found_title)
                    artist_sim = similarity(artist_var, found_artist)
                    
                    print(f"         📈 Similitud título: {title_sim:.2f}, artista: {artist_sim:.2f}")
                    
                    if title_sim >= 0.6 and artist_sim >= 0.5:
                        year = get_year_from_releases(recording_id)
                        if year:
                            print(f"         ✅ ENCONTRADO VÍA RECORDING: {year}")
                            return year
                    else:
                        print(f"         ⚠️ Similitud insuficiente, saltando...")
            
            time.sleep(0.5)
            
        except Exception as e:
            print(f"      ❌ Error en búsqueda de recording: {e}")
            continue
    
    # Estrategia 3: Búsqueda más simple sin comillas
    print(f"   🔍 ESTRATEGIA 3: Búsqueda simple")
    for artist_var in artist_variants[:2]:
        try:
            query = f'{title_clean} AND {artist_var}'
            print(f"      🔍 SIMPLE: {query}")
            
            result = musicbrainzngs.search_releases(query=query, limit=3)
            releases = result.get("release-list", [])
            
            for release in releases:
                date = release.get("date", "")
                found_title = release.get("title", "")
                
                if date and len(date) >= 4:
                    try:
                        year = int(date[:4])
                        if 1900 <= year <= 2025:
                            title_sim = similarity(title_clean, found_title)
                            print(f"         📈 '{found_title}' - {year} (sim: {title_sim:.2f})")
                            
                            if title_sim >= 0.7:  # Más estricto para búsqueda simple
                                print(f"         ✅ ENCONTRADO VÍA SIMPLE: {year}")
                                return year
                    except (ValueError, TypeError):
                        continue
            
            time.sleep(0.5)
            
        except Exception as e:
            print(f"      ❌ Error en búsqueda simple: {e}")
            continue
    
    print(f"   ❌ No encontrado después de 3 estrategias")
    return None

def is_year_missing(value):
    """Devuelve True si el valor de año es vacío o no válido."""
    if pd.isna(value):
        return True
    text = str(value).strip().lower()
    if text in ("", "nan"):
        return True
    try:
        year = int(float(text))
        return year < 1900 or year > 2025
    except (ValueError, TypeError):
        return True

def process_file_fixed(input_path, output_path, batch_sleep=2.0, limit=None):
    """Procesa el archivo con la lógica corregida."""
    
    print(f"🎵 Leyendo archivo: {input_path}")
    
    try:
        df = pd.read_csv(input_path, dtype=str)
        df.columns = df.columns.str.strip()
        print(f"📊 Archivo cargado: {len(df)} filas, {len(df.columns)} columnas")
        
    except Exception as e:
        print(f"❌ Error leyendo archivo: {e}")
        return
    
    # Mapeo de columnas
    title_column = None
    artist_column = None
    year_column = None
    
    for col in df.columns:
        if any(keyword in col.upper() for keyword in ['CANCION', 'CANCIÓN', 'TITULO', 'TÍTULO', 'SONG', 'TRACK', 'NOMBRE']):
            title_column = col
            break
    
    for col in df.columns:
        if any(keyword in col.upper() for keyword in ['ARTISTA', 'ARTIST', 'INTERPRETE', 'INTÉRPRETE']):
            artist_column = col
            break
    
    for col in df.columns:
        if any(keyword in col.upper() for keyword in ['AÑO', 'ANO', 'YEAR', 'FECHA', 'LANZAMIENTO']):
            year_column = col
            break
    
    if not title_column or not artist_column:
        print(f"❌ ERROR: No se encontraron las columnas necesarias.")
        return
    
    if not year_column:
        year_column = "AÑO DE LANZAMIENTO"
        df[year_column] = pd.NA
    
    print(f"🎯 Usando columnas: {title_column}, {artist_column}, {year_column}")
    
    # Filtra filas que necesitan procesamiento
    rows_to_process = []
    for idx, row in df.iterrows():
        if limit and len(rows_to_process) >= limit:
            break
            
        if is_year_missing(row[year_column]):
            title = normalize_text(row[title_column])
            artist = normalize_text(row[artist_column])
            
            if title and artist:
                rows_to_process.append((idx, title, artist))
    
    print(f"\n📈 Filas para procesar: {len(rows_to_process)}")
    
    total_processed = 0
    total_found = 0
    
    for i, (idx, title, artist) in enumerate(rows_to_process):
        print(f"\n" + "="*60)
        print(f"🔄 PROGRESO: {i+1}/{len(rows_to_process)} - Fila {idx+1}")
        print("="*60)
        
        year = search_release_year_fixed(title, artist)
        
        if year:
            df.at[idx, year_column] = year
            total_found += 1
            print(f"✅ AÑO ENCONTRADO Y GUARDADO: {year}")
            
            # Guarda progreso cada resultado encontrado
            df.to_csv(output_path, index=False)
            print(f"💾 Progreso guardado")
        else:
            print(f"❌ NO SE ENCONTRÓ AÑO")
        
        total_processed += 1
        print(f"⏳ Esperando {batch_sleep} segundos...")
        time.sleep(batch_sleep)
    
    # Guarda el archivo final
    df.to_csv(output_path, index=False)
    
    print(f"\n" + "="*60)
    print(f"🎉 ¡Procesamiento completado!")
    print(f"   📊 Total procesado: {total_processed} canciones")
    print(f"   ✅ Años encontrados: {total_found}")
    print(f"   📈 Tasa de éxito: {(total_found/total_processed*100):.1f}%" if total_processed > 0 else "")
    print(f"💾 Archivo final: {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Versión CORREGIDA que busca releases asociados.")
    parser.add_argument("input", help="Ruta al CSV original")
    parser.add_argument("-o", "--output", help="CSV de salida")
    parser.add_argument("--sleep", type=float, default=2.0, help="Segundos de espera entre llamadas")
    parser.add_argument("--limit", type=int, help="Número de canciones a procesar")
    args = parser.parse_args()
    
    if not args.output:
        base_name = os.path.splitext(args.input)[0]
        extension = os.path.splitext(args.input)[1]
        args.output = f"{base_name}_solucionado{extension}"

    print("🛠️ VERSIÓN CORREGIDA - Búsqueda de releases asociados")
    print(f"📂 Archivo entrada: {args.input}")
    print(f"📂 Archivo salida: {args.output}")
    print(f"⏱️  Pausa entre búsquedas: {args.sleep} segundos")

    process_file_fixed(args.input, args.output, args.sleep, args.limit)