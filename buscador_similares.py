#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Buscador de textos similares usando embeddings de sentence-transformers

Este script permite buscar textos similares a uno dado utilizando
embeddings vectoriales y similitud coseno, sin depender de APIs de pago.
"""

import os
import json
import logging
import argparse
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from tqdm import tqdm
from sentence_transformers import SentenceTransformer

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("buscador_log.txt"),
        logging.StreamHandler()
    ]
)

# Configuración
CSV_PATH = "texto_extraido_categorizado.csv"
EMBEDDINGS_CACHE_FILE = "embeddings_cache.json"
MODELO_EMBEDDINGS = "paraphrase-multilingual-MiniLM-L12-v2"  # Modelo más económico para embeddings

class BuscadorTextosSimilares:
    """Clase para buscar textos similares usando embeddings de sentence-transformers"""
    
    def __init__(self, csv_path: str, model_name: str = MODELO_EMBEDDINGS, cache_file: str = EMBEDDINGS_CACHE_FILE):
        """Inicializa el buscador de textos similares
        
        Args:
            csv_path: Ruta al archivo CSV con los textos
            model_name: Nombre del modelo de sentence-transformers a utilizar
            cache_file: Archivo para cachear embeddings
        """
        self.csv_path = csv_path
        self.model_name = model_name
        
        # Usar la ruta de caché de Render si está disponible
        render_cache_dir = "/opt/render/project/src/cache"
        if os.path.exists(render_cache_dir):
            self.cache_file = os.path.join(render_cache_dir, cache_file)
            logging.info(f"Usando ruta de caché en Render: {self.cache_file}")
        else:
            self.cache_file = cache_file
            logging.info(f"Usando ruta de caché local: {self.cache_file}")
        
        self.model = SentenceTransformer(model_name)
        self.df = None
        self.embeddings_cache = {}
        self.load_cache()
        
    def load_cache(self):
        """Carga el caché de embeddings calculados previamente"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.embeddings_cache = json.load(f)
            except Exception as e:
                logging.error(f"Error al cargar caché de embeddings: {e}")
    
    def save_cache(self):
        """Guarda el caché de embeddings"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.embeddings_cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"Error al guardar caché de embeddings: {e}")
    
    def cargar_datos(self, limit: int = None, precalcular_embeddings: bool = True):
        """Carga los datos del CSV y opcionalmente precalcula todos los embeddings
        
        Args:
            limit: Límite de textos a cargar
            precalcular_embeddings: Si True, precalcula los embeddings de todos los textos
        """
        logging.info(f"Cargando datos desde {self.csv_path}...")
        
        try:
            self.df = pd.read_csv(self.csv_path)
            if limit:
                self.df = self.df.head(limit)
            logging.info(f"Datos cargados: {len(self.df)} textos")
            
            # Precalcular embeddings para mejorar rendimiento
            if precalcular_embeddings:
                self.precalcular_embeddings()
                
        except Exception as e:
            logging.error(f"Error al cargar CSV: {e}")
            raise
            
    def precalcular_embeddings(self):
        """Precalcula los embeddings de todos los textos en el dataframe"""
        textos_sin_embedding = []
        total_textos = len(self.df)
        
        # Identificar textos que no tienen embedding en caché
        for texto in self.df['texto'].unique():
            if texto not in self.embeddings_cache:
                textos_sin_embedding.append(texto)
        
        if not textos_sin_embedding:
            logging.info("Todos los embeddings ya están en caché")
            return
            
        logging.info(f"Precalculando {len(textos_sin_embedding)} embeddings de {total_textos} textos...")
        
        # Calcular embeddings en lotes para mayor eficiencia
        batch_size = 32  # Ajustar según memoria disponible
        for i in range(0, len(textos_sin_embedding), batch_size):
            batch = textos_sin_embedding[i:i+batch_size]
            
            # Mostrar progreso
            progress = min(100, int((i / len(textos_sin_embedding)) * 100))
            logging.info(f"Progreso: {progress}% ({i}/{len(textos_sin_embedding)})")
            
            # Calcular embeddings en lote
            embeddings = self.model.encode(batch).tolist()
            
            # Guardar en caché
            for j, texto in enumerate(batch):
                self.embeddings_cache[texto] = embeddings[j]
            
            # Guardar caché periódicamente
            if i % 100 == 0 and i > 0:
                self.save_cache()
        
        # Guardar caché final
        self.save_cache()
        logging.info("Embeddings precalculados y guardados en caché")
    
    def get_embedding(self, text: str) -> List[float]:
        """Obtiene el embedding de un texto usando sentence-transformers
        
        Args:
            text: Texto para obtener el embedding
            
        Returns:
            Lista de valores float que representan el embedding
        """
        if text in self.embeddings_cache:
            return self.embeddings_cache[text]
        
        try:
            # Usar el modelo de sentence-transformers para generar embeddings
            embedding = self.model.encode(text).tolist()
            
            # Guardar en caché
            self.embeddings_cache[text] = embedding
            self.save_cache()
            
            return embedding
        except Exception as e:
            logging.error(f"Error al obtener embedding: {str(e)}")
            return []
    
    def calcular_similitud_coseno(self, vec1: List[float], vec2: List[float]) -> float:
        """
        Calcula la similitud del coseno entre dos vectores
        
        Args:
            vec1: Primer vector
            vec2: Segundo vector
            
        Returns:
            Similitud del coseno (0-1)
        """
        if not vec1 or not vec2:
            return 0.0
            
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        
        # Calcular similitud del coseno: cos(θ) = (A·B)/(||A||·||B||)
        dot_product = np.dot(vec1, vec2)
        norm_a = np.linalg.norm(vec1)
        norm_b = np.linalg.norm(vec2)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
            
        return dot_product / (norm_a * norm_b)
    
    def buscar_textos_similares(self, texto_consulta: str, top_n: int = 5) -> List[Dict]:
        """
        Busca los textos más similares a uno dado
        
        Args:
            texto_consulta: Texto para buscar similares
            top_n: Número de resultados a devolver
            
        Returns:
            Lista de diccionarios con textos similares y su porcentaje de similitud
        """
        if self.df is None:
            logging.error("No hay datos cargados. Llama a cargar_datos() primero.")
            return []
        
        # Obtener embedding del texto de consulta
        logging.info(f"Obteniendo embedding para texto de consulta: {texto_consulta[:50]}...")
        embedding_consulta = self.get_embedding(texto_consulta)
        if not embedding_consulta:
            logging.error("No se pudo obtener embedding para el texto de consulta")
            return []
        
        # Calcular similitud con todos los textos de manera más eficiente
        logging.info("Calculando similitudes con todos los textos...")
        similitudes = []
        
        # Usar un conjunto único de textos para evitar cálculos duplicados
        textos_unicos = self.df.drop_duplicates(subset=['texto'])
        total_textos = len(textos_unicos)
        
        # Crear un diccionario para mapear textos a categorías
        texto_categoria_map = dict(zip(self.df['texto'], self.df['categoria']))
        
        # Procesar en lotes más pequeños para mostrar progreso
        batch_size = 500
        for i in range(0, total_textos, batch_size):
            end_idx = min(i + batch_size, total_textos)
            batch = textos_unicos.iloc[i:end_idx]
            
            # Mostrar progreso
            logging.info(f"Procesando textos {i} a {end_idx} de {total_textos}")
            
            for _, row in batch.iterrows():
                texto = row["texto"]
                
                # Obtener embedding del texto (ya debería estar en caché)
                embedding_texto = self.get_embedding(texto)
                
                # Calcular similitud
                similitud = self.calcular_similitud_coseno(embedding_consulta, embedding_texto)
                
                # Guardar resultado
                similitudes.append({
                    "texto": texto,
                    "similitud": similitud,
                    "similitud_porcentaje": round(similitud * 100, 2),
                    "categoria": texto_categoria_map.get(texto, "sin_categoria")
                })
        
        # Ordenar por similitud descendente
        logging.info("Ordenando resultados por similitud...")
        similitudes_ordenadas = sorted(similitudes, key=lambda x: x["similitud"], reverse=True)
        
        # Devolver los top_n resultados
        logging.info(f"Devolviendo los {top_n} resultados más similares")
        return similitudes_ordenadas[:top_n]


def buscar_similares(texto_consulta: str, top_n: int = 5, limit: int = None) -> List[Dict]:
    """
    Función de conveniencia para buscar textos similares
    
    Args:
        texto_consulta: Texto para buscar similares
        top_n: Número de resultados a devolver
        limit: Límite de textos a cargar del CSV
        
    Returns:
        Lista de diccionarios con textos similares y su porcentaje de similitud
    """
    buscador = BuscadorTextosSimilares(
        csv_path=CSV_PATH,
        cache_file=EMBEDDINGS_CACHE_FILE
    )
    
    # Cargar datos
    buscador.cargar_datos(limit=limit)
    
    # Buscar similares
    resultados = buscador.buscar_textos_similares(texto_consulta, top_n=top_n)
    
    # Mostrar resultados
    logging.info(f"Resultados para: '{texto_consulta}'")
    for i, res in enumerate(resultados, 1):
        logging.info(f"{i}. [{res['similitud_porcentaje']}%] {res['texto']} (Categoría: {res['categoria']})")
    
    return resultados


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Buscar textos similares en el CSV")
    parser.add_argument("texto", type=str, help="Texto para buscar similares")
    parser.add_argument("--top", type=int, default=5, help="Número de resultados a mostrar")
    parser.add_argument("--limit", type=int, default=None, help="Límite de textos a cargar del CSV")
    
    args = parser.parse_args()
    
    buscar_similares(args.texto, top_n=args.top, limit=args.limit)
