import os
import csv
import time
import base64
import sys
import pandas as pd
from openai import OpenAI
from pathlib import Path
from tqdm import tqdm

# Configuración
API_KEY = os.environ.get("OPENAI_API_KEY", "")
if not API_KEY:
    print("\n⚠️ ADVERTENCIA: No se ha configurado la clave API de OpenAI.")
    print("Por favor, configura la variable de entorno OPENAI_API_KEY.")
    print("Ejemplo: export OPENAI_API_KEY='tu-clave-api'\n")
    sys.exit(1)
CARPETA_IMAGENES = "todas_las_publicaciones"  # Carpeta raíz con las imágenes
SALIDA_CSV = "texto_extraido.csv"
LOTE_PROCESAMIENTO = 5  # Imágenes por lote
PAUSA_ENTRE_LOTES = 2  # Segundos entre lotes

# Costos aproximados por modelo (en USD)
# GPT-4o: $5 por millón de tokens de entrada, $15 por millón de tokens de salida
# Una imagen típica consume aproximadamente 170-255 tokens de entrada
# Asumiendo ~200 tokens por imagen y ~50 tokens de respuesta
COSTO_POR_IMAGEN = 0.002  # ($5/1M * 200 + $15/1M * 50) = $0.00175, redondeado a $0.002

# Inicializar cliente de OpenAI
client = OpenAI(api_key=API_KEY)

# Extensiones de imagen soportadas
EXTENSIONES_PERMITIDAS = {'.jpg', '.jpeg', '.png', '.webp'}

def procesar_imagen(ruta_imagen):
    """Envía una imagen a la API de OpenAI para extraer texto."""
    max_retries = 3
    retry_delay = 5  # segundos
    
    for attempt in range(max_retries):
        try:
            with open(ruta_imagen, "rb") as img_file:
                base64_image = base64.b64encode(img_file.read()).decode('utf-8')
            
            # Crear la URL de la imagen
            image_url = f"data:image/jpeg;base64,{base64_image}"
            
            # Crear el mensaje con la imagen
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Extrae TODO el texto que veas en esta imagen, incluyendo cualquier texto manuscrito. Si no hay texto, devuelve 'SIN_TEXTO'."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_url
                            }
                        }
                    ]
                }
            ]
            
            # Hacer la petición a la API
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                max_tokens=1000
            )
            
            # Extraer y devolver el texto
            texto_extraido = response.choices[0].message.content
            return texto_extraido.strip() if texto_extraido else "SIN_TEXTO"
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # Manejar límite de tasa (429) o errores de servidor (5xx)
            if "429" in error_msg or "rate limit" in error_msg:
                wait_time = retry_delay * (attempt + 1)  # Aumentar el tiempo de espera
                print(f"⚠️ Límite de tasa alcanzado. Esperando {wait_time} segundos...")
                time.sleep(wait_time)
                continue
                
            # Manejar otros errores
            print(f"Error en el intento {attempt + 1}/{max_retries} procesando {ruta_imagen}: {str(e)}")
            if attempt == max_retries - 1:  # Último intento
                return f"ERROR: {str(e)}"
            
            time.sleep(retry_delay)  # Esperar antes de reintentar
    
    return "ERROR: No se pudo procesar la imagen después de varios intentos"

def buscar_imagenes(carpeta):
    """Busca recursivamente todas las imágenes en la carpeta dada."""
    imagenes = []
    for ext in EXTENSIONES_PERMITIDAS:
        for img_path in Path(carpeta).rglob(f'*{ext}'):
            if img_path.is_file() and img_path.suffix.lower() in EXTENSIONES_PERMITIDAS:
                imagenes.append({
                    'ruta': str(img_path),
                    'carpeta': img_path.parent.name
                })
    return imagenes

def main():
    print("🔍 Buscando imágenes...")
    imagenes = buscar_imagenes(CARPETA_IMAGENES)
    print(f"✅ Encontradas {len(imagenes)} imágenes para procesar.")
    
    # Cargar progreso previo si existe
    if os.path.exists(SALIDA_CSV):
        try:
            # Definir nombres de columnas explícitamente ya que el CSV podría no tener encabezados
            df_existente = pd.read_csv(SALIDA_CSV, names=['ruta', 'carpeta', 'texto'], header=None)
            # Si la primera fila parece ser un encabezado, eliminarlo para evitar duplicados
            if isinstance(df_existente.iloc[0, 0], str) and 'ruta' in df_existente.iloc[0, 0].lower():
                df_existente = df_existente.iloc[1:]
            procesadas = set(df_existente.iloc[:, 0].tolist())  # Primera columna = rutas
            print(f"📊 Se encontró un archivo previo con {len(procesadas)} imágenes ya procesadas.")
        except Exception as e:
            print(f"⚠️ Error al leer el archivo CSV existente: {str(e)}")
            procesadas = set()
    else:
        procesadas = set()
    
    # Filtrar solo las no procesadas
    imagenes = [img for img in imagenes if img['ruta'] not in procesadas]
    print(f"🚀 Imágenes por procesar: {len(imagenes)}")
    
    if not imagenes:
        print("No hay imágenes nuevas para procesar.")
        return
    
    # Calcular costo estimado total
    costo_estimado_total = len(imagenes) * COSTO_POR_IMAGEN
    print(f"💰 Costo estimado total: ${costo_estimado_total:.2f} USD")
    
    # Procesar imágenes
    resultados = []
    imagenes_procesadas = 0
    costo_acumulado = 0
    
    for i, img in enumerate(tqdm(imagenes, desc="Procesando imágenes")):
        try:
            texto = procesar_imagen(img['ruta'])
            print(f"\n✅ {img['ruta']}")
            print(f"   📝 {texto[:150]}..." if len(texto) > 150 else f"   📝 {texto}")
            
            # Actualizar contador y costo solo si no hubo error
            if not texto.startswith("ERROR:"):
                imagenes_procesadas += 1
                costo_acumulado += COSTO_POR_IMAGEN
                print(f"   💰 Costo acumulado: ${costo_acumulado:.2f} USD ({imagenes_procesadas} imágenes procesadas)")
            
            resultados.append({
                'ruta': img['ruta'],
                'carpeta': img['carpeta'],
                'texto': texto
            })
            
            # Guardar cada LOTE_PROCESAMIENTO imágenes
            if (i + 1) % LOTE_PROCESAMIENTO == 0:
                df_nuevo = pd.DataFrame(resultados)
                df_nuevo.to_csv(SALIDA_CSV, mode='a', header=not os.path.exists(SALIDA_CSV), index=False)
                resultados = []
                print(f"\n💾 Progreso guardado. Total procesadas: {i+1}/{len(imagenes)}")
                print(f"💰 Costo acumulado hasta ahora: ${costo_acumulado:.2f} USD")
                if i + 1 < len(imagenes):
                    print(f"⏳ Pausa de {PAUSA_ENTRE_LOTES} segundos...")
                    time.sleep(PAUSA_ENTRE_LOTES)
                    
        except KeyboardInterrupt:
            print("\n🚫 Proceso interrumpido por el usuario.")
            break
            
        except Exception as e:
            print(f"\n❌ Error procesando {img['ruta']}: {str(e)}")
            continue
    
    # Guardar resultados finales
    if resultados:
        df_nuevo = pd.DataFrame(resultados)
        df_nuevo.to_csv(SALIDA_CSV, mode='a', header=not os.path.exists(SALIDA_CSV), index=False)
    
    print(f"\n✨ Proceso completado. Resultados guardados en {SALIDA_CSV}")
    print(f"💰 Costo total final: ${costo_acumulado:.2f} USD ({imagenes_procesadas} imágenes procesadas correctamente)")
    if costo_estimado_total > costo_acumulado:
        print(f"💰 Ahorro estimado: ${costo_estimado_total - costo_acumulado:.2f} USD")

if __name__ == "__main__":
    main()
