import os
import re
import csv
import time
import json
import base64
import requests
import openai
import pandas as pd
import io
import getpass
import sys
import random
from datetime import datetime, timedelta

# Deshabilitar la verificación SSL (útil si hay problemas de certificado)
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# === CONFIGURACIÓN ===
usuario_perfil = "thomaslelu"  # Perfil a analizar
carpeta_salida = "imagenes_instagram"
sessionfile = "insta_session"

# === CREDENCIALES ===
INSTAGRAM_USER = "gonzalezbrunaenrique"
INSTAGRAM_PASS = "tl1234567"

# === CONFIGURACIÓN DE REINTENTOS ===
MAX_ATTEMPTS = 3
DELAY_BETWEEN_ATTEMPTS = 300  # 5 minutos
REQUEST_TIMEOUT = 600  # 10 minutos

# User-Agents aleatorios
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
]

def setup_instaloader():
    """Configura y retorna una instancia de Instaloader con parámetros optimizados."""
    L = instaloader.Instaloader(
        download_videos=False,
        download_video_thumbnails=False,
        download_comments=False,
        save_metadata=False,
        post_metadata_txt_pattern='',
        max_connection_attempts=3,
        user_agent=random.choice(USER_AGENTS)
    )
    
    # Configuración del contexto
    L.context.raise_all_errors = True
    L.context.request_timeout = REQUEST_TIMEOUT
    L.context.sleep = True
    L.context.sleep_every = 10
    L.context.delay_after_request = 2  # 2 segundos entre peticiones
    
    return L

def login_instagram():
    """Maneja el inicio de sesión con reintentos y manejo de errores."""
    L = setup_instaloader()
    
    # Intento de cargar sesión guardada
    if os.path.exists(sessionfile):
        print("\n🔍 Intentando cargar sesión guardada...")
        try:
            L.load_session_from_file(INSTAGRAM_USER, sessionfile)
            print("✅ Sesión cargada correctamente.")
            return L
        except Exception as e:
            print(f"⚠️  No se pudo cargar la sesión: {str(e)}")
            print("Intentando iniciar sesión de nuevo...")
    
    # Si no hay sesión o falla, intentar login
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            print(f"\n🔐 Intento de inicio de sesión {attempt}/{MAX_ATTEMPTS}")
            L.login(INSTAGRAM_USER, INSTAGRAM_PASS)
            L.save_session_to_file(sessionfile)
            print("✅ Inicio de sesión exitoso.")
            return L
        except Exception as e:
            print(f"❌ Error en el intento {attempt}: {str(e)}")
            if attempt < MAX_ATTEMPTS:
                wait_time = DELAY_BETWEEN_ATTEMPTS * attempt
                print(f"⏳ Esperando {wait_time} segundos antes de reintentar...")
                time.sleep(wait_time)
    
    print("❌ No se pudo iniciar sesión después de varios intentos.")
    return None

# === INICIO DEL SCRIPT ===
print("🔐 Iniciando configuración de Instagram Downloader...")
print(f"📂 Directorio de salida: {os.path.abspath(carpeta_salida)}")

# Crear directorio de salida si no existe
os.makedirs(carpeta_salida, exist_ok=True)

# Iniciar sesión
L = login_instagram()
if not L:
    print("❌ No se pudo iniciar sesión. Saliendo...")
    exit(1)

# Verificar acceso al perfil
print(f"\n🔍 Intentando acceder al perfil @{usuario_perfil}...")
try:
    profile = instaloader.Profile.from_username(L.context, usuario_perfil)
    print(f"✅ Perfil @{usuario_perfil} accesible correctamente.")
    print(f"📊 {profile.followers} seguidores | {profile.mediacount} publicaciones")
except Exception as e:
    print(f"❌ Error al acceder al perfil: {str(e)}")
    print("Asegúrate de que el perfil existe y es público.")
    exit(1)

# === DESCARGA DE IMÁGENES ===
print(f"\n📥 Descargando imágenes del perfil @{usuario_perfil}...")

try:
    # Obtener el perfil
    try:
        posts_gen = profile.get_posts()
        posts = list(posts_gen)
        print(f"\n🔍 Encontradas {len(posts)} publicaciones en total.")
    except Exception as e:
        print(f"❌ Error al obtener las publicaciones: {e}")
        exit(1)
    
    # Contador de publicaciones descargadas
    descargadas = 0
    max_publicaciones = 30  # Número máximo de publicaciones a descargar
    reintentos_maximos = 3  # Número máximo de reintentos por publicación
    errores_consecutivos = 0
    max_errores_consecutivos = 5  # Número máximo de errores consecutivos permitidos

    LOTE_INSTAGRAM = 10  # Tamaño del lote de descarga
    PAUSA_INSTAGRAM = 180  # Pausa en segundos entre lotes (3 minutos)

    progreso_path = os.path.join(carpeta_salida, 'progreso_instagram.txt')
    def guardar_progreso_instagram(indice):
        with open(progreso_path, 'w') as f:
            f.write(str(indice))
    def cargar_progreso_instagram():
        if os.path.exists(progreso_path):
            with open(progreso_path, 'r') as f:
                try:
                    return int(f.read().strip())
                except:
                    return 0
        return 0

    inicio = cargar_progreso_instagram()
    print(f"\n🔁 Reanudando descarga desde la publicación {inicio+1}...")

    total_posts = len(list(posts))
    for i, post in enumerate(posts):
        if i < inicio:
            continue
        if descargadas >= max_publicaciones:
            print(f"\n✅ Se alcanzó el límite de {max_publicaciones} publicaciones.")
            break
        if errores_consecutivos >= max_errores_consecutivos:
            print("\n⚠️  Demasiados errores consecutivos. Deteniendo la descarga.")
            break
        # Configurar el nombre del archivo para esta publicación
        fecha = post.date_utc.strftime('%Y-%m-%d_%H-%M-%S_UTC')
        print(f"\n📌 Procesando publicación {i+1}/{total_posts} - {fecha}")
        # Reintentar la descarga en caso de error
        for intento in range(reintentos_maximos):
            try:
                post_dir = os.path.join(carpeta_salida, f"post_{i+1:04d}_{fecha}")
                os.makedirs(post_dir, exist_ok=True)
                archivos = [f for f in os.listdir(post_dir) if f.endswith(('.jpg', '.jpeg', '.png'))]
                if archivos:
                    print(f"✓ Ya descargada ({len(archivos)} archivos)")
                    descargadas += 1
                    break
                L.download_post(post, target=post_dir)
                archivos = [f for f in os.listdir(post_dir) if f.endswith(('.jpg', '.jpeg', '.png'))]
                if archivos:
                    print(f"✅ {len(archivos)} imágenes encontradas en: {post_dir}")
                    descargadas += 1
                else:
                    print("⚠️  No se encontraron archivos de imagen en la publicación")
                break
                
            except Exception as e:
                if intento < reintentos_maximos - 1:
                    print(f"⚠️  Error (intento {intento + 1}/{reintentos_maximos}): {str(e)}")
                    print("🔄 Reintentando...")
                    time.sleep(5)  # Esperar antes de reintentar
                else:
                    print(f"❌ No se pudo descargar la publicación después de {reintentos_maximos} intentos")
                    print(f"    Error: {str(e)}")
    
    print(f"\n✅ Descarga completada. Se descargaron {descargadas} publicaciones.")
    
except KeyboardInterrupt:
    print("\n⚠️  Descarga interrumpida por el usuario.")
    print(f"Se descargaron {descargadas} publicaciones en total.")
except Exception as e:
    print(f"\n❌ Error inesperado: {str(e)}")
    print(f"Se descargaron {descargadas} publicaciones antes del error.")

# === PARTE 2: OCR manuscrito con OpenAI Vision (GPT-4V) ===

import openai
from PIL import Image
import base64
import io
import getpass

# Configurar la clave API de OpenAI desde variables de entorno
openai.api_key = os.environ.get("OPENAI_API_KEY", "")
if not openai.api_key:
    print("\n⚠️ ADVERTENCIA: No se ha configurado la clave API de OpenAI.")
    print("Por favor, configura la variable de entorno OPENAI_API_KEY.")
    print("Ejemplo: export OPENAI_API_KEY='tu-clave-api'\n")
    sys.exit(1)

# Prompt para OCR manuscrito en inglés
PROMPT = "Transcribe exactly the handwritten English text in this image. Only output the text, no explanation."

resultados = []
procesadas = 0

print("🔍 Procesando imágenes con OpenAI Vision (GPT-4V)...")
LOTE_OCR = 10  # Tamaño del lote de OCR
PAUSA_OCR = 60  # Pausa en segundos entre lotes de OCR
COSTO_POR_IMAGEN = 0.02  # Estimación en USD (ajusta según tu experiencia)

imagenes = []
for root, dirs, files in os.walk(carpeta_salida):
    for archivo in sorted(files):
        if archivo.lower().endswith((".jpg", ".jpeg", ".png")):
            ruta = os.path.join(root, archivo)
            imagenes.append((archivo, ruta, os.path.basename(root)))

print(f"🔍 Procesando {len(imagenes)} imágenes con OpenAI Vision (GPT-4V)...")
for idx, (archivo, ruta, carpeta) in enumerate(imagenes, 1):
    try:
        print(f"Procesando {archivo} ({idx}/{len(imagenes)})...")
        with open(ruta, "rb") as img_file:
            img_bytes = img_file.read()
            img_b64 = base64.b64encode(img_bytes).decode('utf-8')
        for reintento in range(5):
            try:
                # Workaround: eliminar proxies si están presentes en kwargs (bug de entorno)
                import inspect
                kwargs = dict()
                if 'proxies' in inspect.signature(openai.chat.completions.create).parameters:
                    kwargs.pop('proxies', None)
                response = openai.chat.completions.create(
                    model="gpt-4-vision-preview",
                    messages=[
                        {"role": "system", "content": "You are an OCR assistant."},
                        {"role": "user", "content": [
                            {"type": "text", "text": PROMPT},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
                        ]}
                    ],
                    max_tokens=512,
                    **kwargs
                )
                texto = response.choices[0].message.content.strip()
                break
            except Exception as e:
                if 'rate limit' in str(e).lower() or '429' in str(e):
                    print('⏳ Rate limit de OpenAI, esperando 2 minutos...')
                    time.sleep(120)
                else:
                    print(f"❌ Error procesando {archivo}: {str(e)}")
                    texto = ''
                    break
        if texto:
            resultados.append({
                'archivo': archivo,
                'ruta': ruta,
                'texto': texto,
                'carpeta': carpeta
            })
            print(f"✅ Texto extraído: {texto[:50]}..." if len(texto) > 50 else f"✅ Texto extraído: {texto}")
        else:
            print(f"ℹ️  No se detectó texto en {archivo}")
        procesadas += 1
        # Guardar progreso y mostrar coste cada lote
        if idx % LOTE_OCR == 0 or idx == len(imagenes):
            pd.DataFrame(resultados).to_csv("frases_extraidas_parcial.csv", index=False)
            print(f"💰 Imágenes procesadas: {idx} | Coste estimado: ${(idx*COSTO_POR_IMAGEN):.2f} USD")
            print(f"⏸️  Pausa de {PAUSA_OCR} segundos para evitar rate limit de OpenAI...")
            time.sleep(PAUSA_OCR)
    except Exception as e:
        print(f"❌ Error procesando {archivo}: {str(e)}")
        continue


# === PARTE 3: Guardar CSV ===

df = pd.DataFrame(resultados)
df.to_csv("frases_extraidas.csv", index=False)
print("📄 Archivo 'frases_extraidas.csv' creado con éxito.")