#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Clasificador de textos de Instagram usando la API de OpenAI
Este script analiza cada texto del CSV y le asigna una categoría usando GPT
"""

import os
import sys
import pandas as pd
import time
import argparse
from openai import OpenAI
from tqdm import tqdm
import json
import logging
from typing import List, Dict, Any, Optional, Union

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("clasificador_log.txt"),
        logging.StreamHandler()
    ]
)

# Configuración
API_KEY = os.environ.get("OPENAI_API_KEY", "")
if not API_KEY:
    logging.warning("No se ha configurado la clave API de OpenAI. La clasificación de textos no funcionará.")
    logging.warning("Configura la variable de entorno OPENAI_API_KEY para usar esta funcionalidad.")

CSV_PATH = "texto_extraido.csv"
OUTPUT_CSV = "texto_extraido_categorizado.csv"
CACHE_FILE = "categorias_cache.json"

# Categorías predefinidas (puedes modificar esta lista)
CATEGORIAS = [
    "amor_relaciones", 
    "motivacional_superacion", 
    "humor_entretenimiento", 
    "vida_cotidiana",
    "critica_social", 
    "autoestima_autoayuda", 
    "reflexion_filosofica",
    "anuncio_evento",
    "cita_literaria",
    "minimalista",
    "otro"
]

class ClasificadorTextos:
    """Clase para clasificar textos de Instagram usando la API de OpenAI"""
    
    def __init__(self, api_key: str, csv_path: str, output_csv: str, cache_file: str):
        """Inicializa el clasificador de textos"""
        self.api_key = api_key
        self.csv_path = csv_path
        self.output_csv = output_csv
        self.cache_file = cache_file
        self.client = OpenAI(api_key=api_key)
        self.cache = self._cargar_cache()
        self.df = None
        self.textos_procesados = 0
        self.costo_estimado = 0.0
        
    def _cargar_cache(self) -> Dict:
        """Carga el caché de categorías asignadas previamente"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"Error al cargar caché: {e}")
                return {}
        return {}
    
    def _guardar_cache(self):
        """Guarda el caché de categorías asignadas"""
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
        
        # Verificar si ya existe un CSV procesado previamente
        if os.path.exists(self.output_csv):
            try:
                self.df = pd.read_csv(self.output_csv)
                textos_pendientes = self.df[self.df["categoria"].isna()]
                textos_procesados = self.df[~self.df["categoria"].isna()]
                logging.info(f"Cargado CSV previamente procesado con {len(self.df)} filas")
                logging.info(f"Textos ya procesados: {len(textos_procesados)} ({len(textos_procesados)/len(self.df)*100:.1f}%)")
                logging.info(f"Textos pendientes: {len(textos_pendientes)} ({len(textos_pendientes)/len(self.df)*100:.1f}%)")
                
                # Actualizar contador de textos procesados para el cálculo de costos
                self.textos_procesados = len(textos_procesados)
                return
            except Exception as e:
                logging.warning(f"Error al cargar CSV previo: {e}. Procesando desde cero.")
        
        # Procesar el CSV en chunks para manejar archivos grandes
        chunks = []
        total_rows = 0
        
        for chunk in tqdm(pd.read_csv(
            self.csv_path, 
            names=["ruta", "carpeta", "texto"],
            header=None,
            chunksize=chunk_size
        ), desc="Procesando chunks"):
            
            # Filtrar textos válidos
            chunk = chunk[~chunk["texto"].isna()]
            chunk = chunk[~chunk["texto"].str.contains("SIN_TEXTO|ERROR:|Lo siento", na=False)]
            
            chunks.append(chunk)
            total_rows += len(chunk)
            
            # Si hay un límite y ya lo alcanzamos, salimos
            if limit and total_rows >= limit:
                break
        
        # Concatenar todos los chunks
        if chunks:
            self.df = pd.concat(chunks)
            if limit:
                self.df = self.df.head(limit)
            
            # Añadir columna para categorías
            self.df["categoria"] = None
            
            logging.info(f"Datos cargados: {len(self.df)} textos válidos")
        else:
            logging.error("No se encontraron textos válidos en el CSV")
            self.df = pd.DataFrame(columns=["ruta", "carpeta", "texto", "categoria"])
    
    def clasificar_texto(self, texto: str, modelo: str = "gpt-3.5-turbo") -> str:
        """
        Clasifica un texto usando la API de OpenAI
        
        Args:
            texto: Texto a clasificar
            modelo: Modelo de OpenAI a usar
            
        Returns:
            Categoría asignada
        """
        # Verificar si ya está en caché
        if texto in self.cache:
            return self.cache[texto]
        
        # Construir prompt
        categorias_str = ", ".join(CATEGORIAS)
        prompt = f"""Clasifica el siguiente texto de Instagram en una de estas categorías: {categorias_str}.
        
Texto: "{texto}"

Responde ÚNICAMENTE con el nombre de la categoría que mejor se ajuste al texto, sin explicaciones ni puntuación adicional."""
        
        # Intentar clasificar el texto
        max_retries = 3
        for intento in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=modelo,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=20,
                    temperature=0.2
                )
                
                # Calcular costo aproximado (para GPT-3.5-turbo)
                tokens_entrada = len(prompt) / 4  # Aproximación
                tokens_salida = 10  # Aproximación
                costo_por_1k_entrada = 0.0005  # $0.0005 por 1K tokens de entrada
                costo_por_1k_salida = 0.0015   # $0.0015 por 1K tokens de salida
                costo = (tokens_entrada / 1000 * costo_por_1k_entrada) + (tokens_salida / 1000 * costo_por_1k_salida)
                self.costo_estimado += costo
                
                categoria = response.choices[0].message.content.strip().lower()
                
                # Normalizar la categoría
                categoria_normalizada = None
                for cat in CATEGORIAS:
                    if cat.lower() in categoria:
                        categoria_normalizada = cat
                        break
                
                if not categoria_normalizada:
                    categoria_normalizada = "otro"
                
                # Guardar en caché
                self.cache[texto] = categoria_normalizada
                
                # Guardar caché periódicamente
                self.textos_procesados += 1
                if self.textos_procesados % 10 == 0:
                    self._guardar_cache()
                
                return categoria_normalizada
                
            except Exception as e:
                logging.error(f"Error en intento {intento+1}/{max_retries}: {e}")
                if intento < max_retries - 1:
                    time.sleep(5)  # Esperar antes de reintentar
        
        return "otro"  # Categoría por defecto si falla
    
    def procesar_lote(self, 
                     batch_size: int = 50,
                     modelo: str = "gpt-3.5-turbo",
                     guardar_cada: int = 50):
        """
        Procesa un lote de textos para clasificarlos
        
        Args:
            batch_size: Tamaño del lote a procesar cada vez
            modelo: Modelo de OpenAI a usar
            guardar_cada: Cada cuántos textos guardar el progreso
        """
        if self.df is None or len(self.df) == 0:
            logging.error("No hay datos cargados para procesar")
            return
        
        # Verificar si hay textos sin categoría
        textos_pendientes = self.df[self.df["categoria"].isna()]
        if len(textos_pendientes) == 0:
            logging.info("Todos los textos ya están categorizados")
            return
        
        logging.info(f"Procesando {len(textos_pendientes)} textos pendientes...")
        
        # Procesar textos en lotes
        for i, (idx, row) in enumerate(tqdm(textos_pendientes.iterrows(), total=len(textos_pendientes))):
            texto = row["texto"]
            
            # Clasificar texto
            categoria = self.clasificar_texto(texto, modelo=modelo)
            
            # Actualizar DataFrame
            self.df.at[idx, "categoria"] = categoria
            
            # Guardar progreso periódicamente
            if (i + 1) % guardar_cada == 0:
                self.guardar_resultados()
                logging.info(f"Progreso: {i + 1}/{len(textos_pendientes)} textos procesados. Costo estimado: ${self.costo_estimado:.4f}")
                
            # Pausa para evitar límites de tasa
            if (i + 1) % batch_size == 0:
                time.sleep(1)
        
        # Guardar resultados finales
        self._guardar_cache()
        self.guardar_resultados()
        
        logging.info(f"Clasificación completada. {len(textos_pendientes)} textos procesados.")
        logging.info(f"Costo total estimado: ${self.costo_estimado:.4f}")
    
    def guardar_resultados(self):
        """Guarda los resultados en un CSV"""
        if self.df is not None:
            self.df.to_csv(self.output_csv, index=False)
            logging.info(f"Resultados guardados en {self.output_csv}")
    
    def generar_estadisticas(self):
        """Genera estadísticas de las categorías"""
        if self.df is None or "categoria" not in self.df.columns:
            logging.error("No hay datos categorizados para generar estadísticas")
            return {}
        
        # Contar categorías
        stats = self.df["categoria"].value_counts().to_dict()
        
        # Mostrar estadísticas
        logging.info("Estadísticas de categorías:")
        for categoria, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):
            logging.info(f"  {categoria}: {count} textos ({count/len(self.df)*100:.1f}%)")
        
        return stats


def main():
    """Función principal"""
    parser = argparse.ArgumentParser(description="Clasificador de textos de Instagram usando OpenAI")
    
    parser.add_argument("--limit", type=int, default=None,
                        help="Límite de textos a procesar (None para todos)")
    parser.add_argument("--batch", type=int, default=50,
                        help="Tamaño del lote para procesar")
    parser.add_argument("--modelo", type=str, default="gpt-3.5-turbo",
                        choices=["gpt-3.5-turbo", "gpt-4"],
                        help="Modelo de OpenAI a usar")
    parser.add_argument("--guardar_cada", type=int, default=50,
                        help="Cada cuántos textos guardar el progreso")
    parser.add_argument("--reanudar", action="store_true",
                        help="Reanudar el proceso desde donde se quedó")
    
    args = parser.parse_args()
    
    # Inicializar clasificador
    clasificador = ClasificadorTextos(
        api_key=API_KEY,
        csv_path=CSV_PATH,
        output_csv=OUTPUT_CSV,
        cache_file=CACHE_FILE
    )
    
    # Cargar datos
    clasificador.cargar_datos(limit=args.limit)
    
    # Si se especifica reanudar, mostrar resumen y confirmar
    if args.reanudar and clasificador.df is not None:
        textos_pendientes = clasificador.df[clasificador.df["categoria"].isna()]
        if len(textos_pendientes) == 0:
            logging.info("No hay textos pendientes de clasificar. El proceso ya está completo.")
            return
            
        logging.info(f"Se reanudará la clasificación de {len(textos_pendientes)} textos pendientes.")
        logging.info(f"Usando modelo: {args.modelo}, tamaño de lote: {args.batch}, guardando cada: {args.guardar_cada} textos")
        
        # Preguntar confirmación
        try:
            confirmacion = input("\n¿Desea continuar? (s/n): ").lower().strip()
            if confirmacion != 's' and confirmacion != 'si':
                logging.info("Operación cancelada por el usuario.")
                return
        except KeyboardInterrupt:
            logging.info("\nOperación cancelada por el usuario.")
            return
    
    # Procesar textos
    clasificador.procesar_lote(
        batch_size=args.batch,
        modelo=args.modelo,
        guardar_cada=args.guardar_cada
    )
    
    # Generar estadísticas
    clasificador.generar_estadisticas()


if __name__ == "__main__":
    main()
