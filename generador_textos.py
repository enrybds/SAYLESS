#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Generador de textos estilo Instagram basado en ejemplos extraídos
Utiliza la API de OpenAI para generar textos similares a los ejemplos
"""

import os
import pandas as pd
import random
import time
import argparse
from openai import OpenAI
from tqdm import tqdm
import json
from typing import List, Dict, Any, Optional, Union
import logging

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("generador_log.txt"),
        logging.StreamHandler()
    ]
)

# Configuración
API_KEY = os.environ.get("OPENAI_API_KEY", "")
if not API_KEY:
    logging.warning("No se ha configurado la clave API de OpenAI. La generación de textos no funcionará.")
    logging.warning("Configura la variable de entorno OPENAI_API_KEY para usar esta funcionalidad.")

CSV_PATH = "texto_extraido_categorizado.csv"  # Usar el CSV con categorías
OUTPUT_DIR = "textos_generados"
CACHE_FILE = "textos_cache.json"

# Categorías predefinidas para clasificar textos
CATEGORIAS = {
    "amor": ["love", "kiss", "heart", "amor", "beso", "corazón", "relationship", "pareja"],
    "motivacional": ["success", "dream", "believe", "éxito", "sueño", "creer", "motivación", "motivation"],
    "humor": ["joke", "funny", "laugh", "chiste", "gracioso", "reír", "humor"],
    "vida": ["life", "live", "alive", "vida", "vivir", "existencia", "existence"],
    "crítica_social": ["society", "social", "crítica", "criticism", "instagram", "media", "fake"],
    "autoestima": ["self", "love", "myself", "confidence", "autoestima", "confianza"],
    "sueño": ["sleep", "dream", "bed", "dormir", "sueño", "cama", "tired", "cansado"]
}

class GeneradorTextos:
    """Clase para generar textos estilo Instagram basados en ejemplos"""
    
    def __init__(self, api_key: str, csv_path: str, output_dir: str, cache_file: str):
        """Inicializa el generador de textos"""
        self.api_key = api_key
        self.csv_path = csv_path
        self.output_dir = output_dir
        self.cache_file = cache_file
        self.client = OpenAI(api_key=api_key)
        self.textos = []
        self.textos_por_categoria = {}
        self.cache = self._cargar_cache()
        
        # Crear directorio de salida si no existe
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
    
    def _cargar_cache(self) -> Dict:
        """Carga el caché de textos generados previamente"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"Error al cargar caché: {e}")
                return {}
        return {}
    
    def _guardar_cache(self):
        """Guarda el caché de textos generados"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"Error al guardar caché: {e}")
    
    def cargar_datos(self, limit: Optional[int] = None, chunk_size: int = 10000):
        """
        Carga los datos del CSV de manera eficiente usando chunks
        
        Args:
            limit: Límite opcional de filas a cargar
            chunk_size: Tamaño de cada chunk para procesar el CSV
        """
        logging.info(f"Cargando datos desde {self.csv_path}...")
        
        # Inicializar listas
        self.textos = []
        self.categorias_texto = {}  # Diccionario para mapear texto -> categoría
        
        try:
            # Procesar el CSV en chunks para manejar archivos grandes
            chunks = pd.read_csv(
                self.csv_path, 
                chunksize=chunk_size
            )
            
            total_rows = 0
            valid_rows = 0
            
            for chunk in tqdm(chunks, desc="Procesando chunks"):
                # Determinar nombres de columnas
                if 'texto' not in chunk.columns:
                    # Formato antiguo sin encabezados
                    chunk.columns = ["ruta", "carpeta", "texto"]
                
                # Filtrar textos válidos
                valid_chunk = chunk.dropna(subset=["texto"])
                valid_chunk = valid_chunk[~valid_chunk["texto"].astype(str).str.contains(
                    "SIN_TEXTO|ERROR:|Lo siento", na=False)]
                valid_chunk = valid_chunk[valid_chunk["texto"].astype(str).str.strip().str.len() > 0]
                
                # Extraer textos y categorías
                for _, row in valid_chunk.iterrows():
                    texto = str(row["texto"]).strip()
                    # Guardar la categoría si existe en el CSV
                    if "categoria" in row and pd.notna(row["categoria"]):
                        self.categorias_texto[texto] = row["categoria"]
                    
                    self.textos.append(texto)
                
                total_rows += len(chunk)
                valid_rows += len(valid_chunk)
                
                # Si hay un límite y ya lo alcanzamos, salimos
                if limit and valid_rows >= limit:
                    self.textos = self.textos[:limit]
                    break
            
            logging.info(f"Datos cargados: {len(self.textos)} textos válidos de {total_rows} filas totales")
            logging.info(f"Textos con categoría asignada: {len(self.categorias_texto)}")
            
            # Clasificar textos por categoría
            self._clasificar_textos()
            
        except Exception as e:
            logging.error(f"Error al cargar datos: {e}")
            raise
    
    def _clasificar_textos(self):
        """Clasifica los textos en categorías basadas en categorías asignadas o palabras clave"""
        logging.info("Clasificando textos por categorías...")
        
        # Inicializar diccionario de categorías
        self.textos_por_categoria = {}
        
        # Primero, usar las categorías del CSV si están disponibles
        if self.categorias_texto:
            # Identificar todas las categorías únicas
            categorias_unicas = set(self.categorias_texto.values())
            
            # Inicializar listas para cada categoría
            for categoria in categorias_unicas:
                self.textos_por_categoria[categoria] = []
            
            # Categoría para textos sin categoría asignada
            self.textos_por_categoria["sin_categoria"] = []
            
            # Clasificar cada texto según la categoría del CSV
            for texto in self.textos:
                if texto in self.categorias_texto:
                    categoria = self.categorias_texto[texto]
                    self.textos_por_categoria[categoria].append(texto)
                else:
                    self.textos_por_categoria["sin_categoria"].append(texto)
        
        # Si no hay categorías en el CSV, usar el método de palabras clave
        else:
            for categoria in CATEGORIAS:
                self.textos_por_categoria[categoria] = []
            
            # Categoría para textos que no encajan en ninguna otra
            self.textos_por_categoria["otros"] = []
            
            # Clasificar cada texto
            for texto in self.textos:
                texto_lower = texto.lower()
                categorizado = False
                
                for categoria, palabras_clave in CATEGORIAS.items():
                    if any(palabra in texto_lower for palabra in palabras_clave):
                        self.textos_por_categoria[categoria].append(texto)
                        categorizado = True
                        break
                
                if not categorizado:
                    self.textos_por_categoria["otros"].append(texto)
        
        # Mostrar estadísticas
        for categoria, textos in self.textos_por_categoria.items():
            logging.info(f"Categoría '{categoria}': {len(textos)} textos")
    
    def generar_texto(self, 
                      categoria: Optional[str] = None, 
                      estilo: Optional[str] = None, 
                      tema: Optional[str] = None, 
                      num_ejemplos: int = 20,
                      temperatura: float = 0.7,
                      modelo: str = "gpt-3.5-turbo") -> str:
        """
        Genera un texto basado en ejemplos
        
        Args:
            categoria: Categoría de textos a usar como ejemplos
            estilo: Estilo deseado para el texto
            tema: Tema específico para el texto
            num_ejemplos: Número de ejemplos a incluir
            temperatura: Temperatura para la generación (0.0-1.0)
            modelo: Modelo de OpenAI a usar
            
        Returns:
            Texto generado
        """
        # Crear clave de caché
        cache_key = f"{categoria}_{estilo}_{tema}_{num_ejemplos}_{temperatura}_{modelo}"
        
        # Verificar si ya está en caché
        if cache_key in self.cache:
            return random.choice(self.cache[cache_key])
        
        # Seleccionar ejemplos según la categoría
        if categoria and categoria in self.textos_por_categoria:
            pool_textos = self.textos_por_categoria[categoria]
            if len(pool_textos) < num_ejemplos:
                logging.warning(f"No hay suficientes textos en la categoría '{categoria}'. Usando textos generales.")
                pool_textos = self.textos
        else:
            pool_textos = self.textos
        
        # Seleccionar ejemplos aleatorios
        ejemplos = random.sample(pool_textos, min(num_ejemplos, len(pool_textos)))
        ejemplos_texto = "\n".join([f"- {e}" for e in ejemplos])
        
        # Construir prompt
        prompt = f"""Genera un texto corto en el estilo de los siguientes ejemplos de Instagram:

{ejemplos_texto}

El texto debe ser breve, impactante y con el mismo tono que los ejemplos."""

        if estilo:
            prompt += f"\nEstilo deseado: {estilo}"
        
        if tema:
            prompt += f"\nTema: {tema}"
        
        # Intentar generar el texto
        max_retries = 3
        for intento in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=modelo,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=100,
                    temperature=temperatura
                )
                
                texto_generado = response.choices[0].message.content.strip()
                
                # Guardar en caché
                if cache_key not in self.cache:
                    self.cache[cache_key] = []
                
                self.cache[cache_key].append(texto_generado)
                self._guardar_cache()
                
                return texto_generado
                
            except Exception as e:
                logging.error(f"Error en intento {intento+1}/{max_retries}: {e}")
                if intento < max_retries - 1:
                    time.sleep(5)  # Esperar antes de reintentar
        
        return "Error: No se pudo generar el texto después de varios intentos."
    
    def generar_lote(self, 
                    cantidad: int, 
                    categoria: Optional[str] = None,
                    estilo: Optional[str] = None,
                    tema: Optional[str] = None,
                    temperatura: float = 0.7,
                    modelo: str = "gpt-3.5-turbo") -> List[str]:
        """
        Genera un lote de textos
        
        Args:
            cantidad: Número de textos a generar
            categoria: Categoría de textos a usar como ejemplos
            estilo: Estilo deseado para el texto
            tema: Tema específico para el texto
            temperatura: Temperatura para la generación
            modelo: Modelo de OpenAI a usar
            
        Returns:
            Lista de textos generados
        """
        textos_generados = []
        
        for i in tqdm(range(cantidad), desc="Generando textos"):
            texto = self.generar_texto(
                categoria=categoria,
                estilo=estilo,
                tema=tema,
                temperatura=temperatura,
                modelo=modelo
            )
            textos_generados.append(texto)
            
            # Pausa para evitar límites de tasa
            if i < cantidad - 1:
                time.sleep(0.5)
        
        return textos_generados
    
    def guardar_lote(self, textos: List[str], nombre_archivo: str):
        """
        Guarda un lote de textos en un archivo
        
        Args:
            textos: Lista de textos a guardar
            nombre_archivo: Nombre del archivo de salida
        """
        ruta_completa = os.path.join(self.output_dir, nombre_archivo)
        
        try:
            with open(ruta_completa, 'w', encoding='utf-8') as f:
                for texto in textos:
                    f.write(f"{texto}\n\n---\n\n")
            
            logging.info(f"Textos guardados en {ruta_completa}")
            
        except Exception as e:
            logging.error(f"Error al guardar textos: {e}")


def main():
    """Función principal"""
    parser = argparse.ArgumentParser(description="Generador de textos estilo Instagram")
    
    parser.add_argument("--cantidad", type=int, default=10,
                        help="Cantidad de textos a generar")
    parser.add_argument("--categoria", type=str, default=None, 
                        choices=list(CATEGORIAS.keys()) + ["otros", "todos"],
                        help="Categoría de textos a usar como ejemplos")
    parser.add_argument("--estilo", type=str, default=None,
                        help="Estilo deseado para el texto")
    parser.add_argument("--tema", type=str, default=None,
                        help="Tema específico para el texto")
    parser.add_argument("--temperatura", type=float, default=0.7,
                        help="Temperatura para la generación (0.0-1.0)")
    parser.add_argument("--modelo", type=str, default="gpt-3.5-turbo",
                        choices=["gpt-3.5-turbo", "gpt-4"],
                        help="Modelo de OpenAI a usar")
    parser.add_argument("--salida", type=str, default="textos_generados.txt",
                        help="Nombre del archivo de salida")
    parser.add_argument("--limit", type=int, default=None,
                        help="Límite de textos a cargar del CSV")
    
    args = parser.parse_args()
    
    # Inicializar generador
    generador = GeneradorTextos(
        api_key=API_KEY,
        csv_path=CSV_PATH,
        output_dir=OUTPUT_DIR,
        cache_file=CACHE_FILE
    )
    
    # Cargar datos
    generador.cargar_datos(limit=args.limit)
    
    # Generar textos
    textos_generados = generador.generar_lote(
        cantidad=args.cantidad,
        categoria=args.categoria,
        estilo=args.estilo,
        tema=args.tema,
        temperatura=args.temperatura,
        modelo=args.modelo
    )
    
    # Guardar textos
    generador.guardar_lote(textos_generados, args.salida)
    
    # Mostrar algunos ejemplos
    print("\nEjemplos de textos generados:")
    for i, texto in enumerate(textos_generados[:3], 1):
        print(f"\n{i}. {texto}")
    
    print(f"\nSe generaron {len(textos_generados)} textos en total.")
    print(f"Todos los textos están guardados en: {os.path.join(OUTPUT_DIR, args.salida)}")


if __name__ == "__main__":
    main()
