#!/usr/bin/env python3
"""Versión de DEBUG para entender por qué no encuentra años.

Esta versión es más permisiva y muestra información detallada de los resultados.
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
musicbrainzngs.set_useragent("VibraMusicYearFiller", "2.0", "contacto@tusitio.com")

def similarity(a, b):
    """Calcula la similitud entre dos strings."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def normalize_text_basic(text):
    """Normalización básica sin eliminar demasiada información."""
    if pd.isna(text):
        return ""
    
    text = str(text).strip()
    if not text or text.lower() == 'nan':
        return ""
    
    # Solo elimina espacios extra
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
    variants.append(unidecode.unidecode(artist))
    
    # Solo el primer artista si hay colaboraciones
    parts = re.split(r'\s*(?:&|/|,|\band\b|\by\b|\bfeat\.?\b|\bft\.?\b)\s*', artist, maxsplit=1, flags=re.IGNORECASE)
    if len(parts) > 1:
        variants.append(parts[0].strip())
        variants.append(unidecode.unidecode(parts[0].strip()))
    
    return list(set(filter(None, variants)))

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

def search_release_year_debug(title, artist):
    """Versión DEBUG: más permisiva y con información detallada."""
    
    if not title or not artist:
        return None
    
    title_basic = normalize_text_basic(title)
    artist_variants = clean_artist_name(artist)
    
    print(f"   🎵 '{title_basic}' por '{artist_variants[0] if artist_variants else 'N/A'}'")
    print(f"   🔍 Variantes de artista: {artist_variants}")
    
    # Estrategias simplificadas y más permisivas
    strategies = []
    
    for artist_var in artist_variants[:2]:
        artist_basic = normalize_text_basic(artist_var)
        
        # Solo las estrategias más básicas
        strategies.append(('recording', f'"{title_basic}" AND artist:"{artist_basic}"'))
        strategies.append(('release', f'"{title_basic}" AND artist:"{artist_basic}"'))
    
    print(f"   📝 Estrategias a probar: {len(strategies)}")
    
    best_result = None
    all_candidates = []
    
    for i, (strategy_type, query) in enumerate(strategies):
        try:
            print(f"   🔍 {i+1}/{len(strategies)} - {strategy_type.upper()}: {query}")
            
            if strategy_type == 'release':
                result = musicbrainzngs.search_releases(query=query, limit=5)
                items = result.get("release-list", [])
                date_field = "date"
            else:
                result = musicbrainzngs.search_recordings(query=query, limit=5)
                items = result.get("recording-list", [])
                date_field = "first-release-date"
            
            print(f"      📊 Resultados encontrados: {len(items)}")
            
            for j, item in enumerate(items):
                date = item.get(date_field, "")
                found_title = item.get("title", "")
                
                # Obtener información del artista
                found_artist = ""
                artist_info = item.get("artist-credit", [])
                if artist_info:
                    found_artist = artist_info[0].get("artist", {}).get("name", "")
                
                print(f"      {j+1}. '{found_title}' por '{found_artist}' - Fecha: '{date}'")
                
                if date and len(date) >= 4:
                    try:
                        year = int(date[:4])
                        if 1900 <= year <= 2025:
                            # Calcular similitudes
                            title_sim = similarity(title_basic, found_title)
                            artist_sim = similarity(artist_variants[0], found_artist)
                            
                            candidate = {
                                'year': year,
                                'found_title': found_title,
                                'found_artist': found_artist,
                                'title_similarity': title_sim,
                                'artist_similarity': artist_sim,
                                'strategy': strategy_type,
                                'score': (title_sim + artist_sim) / 2
                            }
                            
                            all_candidates.append(candidate)
                            
                            print(f"         📈 Similitud título: {title_sim:.2f}, artista: {artist_sim:.2f}, score: {candidate['score']:.2f}")
                            
                            # Criterio MUY permisivo para aceptar
                            if (title_sim >= 0.5 and artist_sim >= 0.4) or candidate['score'] >= 0.6:
                                print(f"         ✅ CANDIDATO VÁLIDO!")
                                if not best_result or candidate['score'] > best_result['score']:
                                    best_result = candidate
                    
                    except (ValueError, TypeError):
                        continue
            
            time.sleep(0.5)  # Pausa entre estrategias
            
        except Exception as e:
            print(f"      ❌ Error: {e}")
            continue
    
    # Mostrar todos los candidatos encontrados
    if all_candidates:
        print(f"   📋 TODOS LOS CANDIDATOS ENCONTRADOS ({len(all_candidates)}):")
        for i, candidate in enumerate(sorted(all_candidates, key=lambda x: x['score'], reverse=True)):
            print(f"      {i+1}. {candidate['year']} - '{candidate['found_title']}' por '{candidate['found_artist']}'")
            print(f"         Score: {candidate['score']:.2f} (título: {candidate['title_similarity']:.2f}, artista: {candidate['artist_similarity']:.2f})")
    
    if best_result:
        print(f"   ✅ MEJOR RESULTADO: {best_result['year']} - '{best_result['found_title']}' por '{best_result['found_artist']}'")
        print(f"      Score final: {best_result['score']:.2f}")
        return best_result['year']
    else:
        print(f"   ❌ No se encontró ningún candidato válido")
        return None

def process_file_debug(input_path, output_path, batch_sleep=2.0, limit=5):
    """Versión DEBUG: procesa solo unas pocas canciones con información detallada."""
    
    print(f"🎵 [DEBUG] Leyendo archivo: {input_path}")
    
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
        if len(rows_to_process) >= limit:
            break
            
        if is_year_missing(row[year_column]):
            title = normalize_text_basic(row[title_column])
            artist = normalize_text_basic(row[artist_column])
            
            if title and artist:
                rows_to_process.append((idx, title, artist))
    
    print(f"\n📈 [DEBUG] Procesando solo {len(rows_to_process)} canciones para diagnóstico")
    
    total_processed = 0
    total_found = 0
    
    for i, (idx, title, artist) in enumerate(rows_to_process):
        print(f"\n" + "="*60)
        print(f"🔄 CANCIÓN {i+1}/{len(rows_to_process)} - Fila {idx+1}")
        print(f"🎵 Título original: '{df.at[idx, title_column]}'")
        print(f"🎤 Artista original: '{df.at[idx, artist_column]}'")
        print(f"🔧 Título normalizado: '{title}'")
        print(f"🔧 Artista normalizado: '{artist}'")
        print("="*60)
        
        year = search_release_year_debug(title, artist)
        
        if year:
            df.at[idx, year_column] = year
            total_found += 1
            print(f"✅ AÑO ENCONTRADO Y GUARDADO: {year}")
        else:
            print(f"❌ NO SE ENCONTRÓ AÑO")
        
        total_processed += 1
        print(f"⏳ Esperando {batch_sleep} segundos antes de la siguiente...")
        time.sleep(batch_sleep)
    
    # Guarda el archivo
    df.to_csv(output_path, index=False)
    
    print(f"\n" + "="*60)
    print(f"🎉 [DEBUG] ¡Procesamiento completado!")
    print(f"   📊 Total procesado: {total_processed} canciones")
    print(f"   ✅ Años encontrados: {total_found}")
    print(f"   📈 Tasa de éxito: {(total_found/total_processed*100):.1f}%" if total_processed > 0 else "")
    print(f"💾 Archivo guardado: {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Versión DEBUG para diagnosticar problemas de búsqueda.")
    parser.add_argument("input", help="Ruta al CSV original")
    parser.add_argument("-o", "--output", help="CSV de salida")
    parser.add_argument("--sleep", type=float, default=2.0, help="Segundos de espera entre llamadas")
    parser.add_argument("--limit", type=int, default=5, help="Número de canciones a procesar en modo debug")
    args = parser.parse_args()
    
    if not args.output:
        base_name = os.path.splitext(args.input)[0]
        extension = os.path.splitext(args.input)[1]
        args.output = f"{base_name}_debug{extension}"

    print("🔍 MODO DEBUG - Procesamiento detallado de base musical")
    print(f"📂 Archivo entrada: {args.input}")
    print(f"📂 Archivo salida: {args.output}")
    print(f"⏱️  Pausa entre búsquedas: {args.sleep} segundos")
    print(f"🎯 Límite de canciones: {args.limit}")

    process_file_debug(args.input, args.output, args.sleep, args.limit)