#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Aplicación web para el generador de textos estilo Instagram
"""

import os
import json
import random
import logging
import pandas as pd
from flask import Flask, render_template, request, jsonify
from generador_textos import GeneradorTextos, CATEGORIAS
from buscador_similares import BuscadorTextosSimilares

# Configuración
API_KEY = os.environ.get("OPENAI_API_KEY", "")
if not API_KEY:
    logging.warning("No se ha configurado la clave API de OpenAI. Algunas funcionalidades pueden no estar disponibles.")
    logging.warning("Configura la variable de entorno OPENAI_API_KEY para usar todas las funcionalidades.")
    logging.warning("La búsqueda de textos similares seguirá funcionando ya que usa un modelo local.")

CSV_PATH = "texto_extraido_categorizado.csv"  # CSV con categorías
CSV_PATH_ORIGINAL = "texto_extraido.csv"  # CSV original sin categorías
OUTPUT_DIR = "textos_generados"
CACHE_FILE = "cache_generador.json"

# Asegurarse de que el directorio de salida existe
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Inicializar Flask
app = Flask(__name__)

# Inicializar el generador de textos
generador = None

def obtener_categorias_disponibles():
    """Obtiene las categorías disponibles en el CSV categorizado"""
    try:
        # Intentar cargar el CSV categorizado
        if os.path.exists(CSV_PATH):
            # Verificar si tiene columna de categoría
            df = pd.read_csv(CSV_PATH, nrows=5)
            if 'categoria' in df.columns:
                # Obtener todas las categorías únicas
                df_completo = pd.read_csv(CSV_PATH)
                categorias = df_completo['categoria'].dropna().unique().tolist()
                if categorias:
                    categorias.sort()
                    return categorias
    except Exception as e:
        print(f"Error al obtener categorías: {e}")
    
    # Si no se pueden obtener categorías del CSV, devolver las predefinidas
    return list(CATEGORIAS.keys()) + ["otros"]

def inicializar_generador(limit=None):
    """Inicializa el generador de textos con todos los textos disponibles"""
    global generador
    # Verificar si existe el CSV categorizado
    csv_a_usar = CSV_PATH if os.path.exists(CSV_PATH) else CSV_PATH_ORIGINAL
    
    generador = GeneradorTextos(
        api_key=API_KEY,
        csv_path=csv_a_usar,
        output_dir=OUTPUT_DIR,
        cache_file=CACHE_FILE
    )
    generador.cargar_datos(limit=limit)  # None cargará todos los textos
    return generador

@app.route('/')
def index():
    """Página principal"""
    # Obtener categorías disponibles dinámicamente
    categorias = obtener_categorias_disponibles()
    
    return render_template(
        'index.html',
        categorias=categorias
    )

@app.route('/generar', methods=['POST'])
def generar():
    """Endpoint para generar texto"""
    # Obtener parámetros
    categoria = request.form.get('categoria')
    estilo = request.form.get('estilo')
    tema = request.form.get('tema')
    temperatura = float(request.form.get('temperatura', 0.7))
    modelo = request.form.get('modelo', 'gpt-3.5-turbo')
    
    # Generar texto
    try:
        texto = generador.generar_texto(
            categoria=categoria if categoria != "ninguna" else None,
            estilo=estilo if estilo else None,
            tema=tema if tema else None,
            temperatura=temperatura,
            modelo=modelo
        )
        return jsonify({'success': True, 'texto': texto})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/generar-lote', methods=['POST'])
def generar_lote():
    """Endpoint para generar un lote de textos"""
    # Obtener parámetros
    categoria = request.form.get('categoria')
    estilo = request.form.get('estilo')
    tema = request.form.get('tema')
    temperatura = float(request.form.get('temperatura', 0.7))
    modelo = request.form.get('modelo', 'gpt-3.5-turbo')
    cantidad = int(request.form.get('cantidad', 5))
    
    # Generar textos
    try:
        textos = generador.generar_lote(
            cantidad=cantidad,
            categoria=categoria if categoria != "ninguna" else None,
            estilo=estilo if estilo else None,
            tema=tema if tema else None,
            temperatura=temperatura,
            modelo=modelo
        )
        
        # Guardar textos en un archivo
        nombre_archivo = f"lote_{len(os.listdir(OUTPUT_DIR)) + 1}.txt"
        generador.guardar_lote(textos, nombre_archivo)
        
        return jsonify({
            'success': True, 
            'textos': textos,
            'archivo': os.path.join(OUTPUT_DIR, nombre_archivo)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/estadisticas')
def estadisticas():
    """Endpoint para obtener estadísticas de los textos"""
    stats = {}
    
    # Contar textos por categoría
    for categoria, textos in generador.textos_por_categoria.items():
        stats[categoria] = len(textos)
    
    # Total de textos
    stats['total'] = len(generador.textos)
    
    return jsonify(stats)

@app.route('/generar_texto', methods=['POST'])
def generar_texto():
    """Genera un nuevo texto basado en la categoría seleccionada"""
    try:
        categoria = request.json.get('categoria', 'amor_relaciones')
        logging.info(f"Generando texto para categoría: {categoria}")
        
        texto_generado = generador.generar_texto(categoria=categoria)
        
        return jsonify({
            'texto': texto_generado,
            'categoria': categoria
        })
    except Exception as e:
        logging.error(f"Error al generar texto: {str(e)}")
        return jsonify({
            'error': str(e)
        }), 500

# Variable global para almacenar el buscador de textos similares
buscador_similares = None

@app.route('/inicializar_buscador', methods=['GET'])
def inicializar_buscador():
    """Inicializa el buscador de textos similares en segundo plano"""
    global buscador_similares
    
    try:
        if buscador_similares is None:
            logging.info("Inicializando buscador de textos similares...")
            
            # Inicializar buscador con modelo gratuito
            buscador_similares = BuscadorTextosSimilares(
                csv_path=CSV_PATH if os.path.exists(CSV_PATH) else CSV_PATH_ORIGINAL,
                model_name="paraphrase-multilingual-MiniLM-L12-v2",
                cache_file="embeddings_cache.json"
            )
            
            # Cargar datos y precalcular embeddings
            buscador_similares.cargar_datos(precalcular_embeddings=True)
            logging.info(f"Buscador inicializado con {len(buscador_similares.df)} textos")
            
            return jsonify({
                'status': 'success',
                'message': 'Buscador inicializado correctamente',
                'textos_cargados': len(buscador_similares.df)
            })
        else:
            return jsonify({
                'status': 'success',
                'message': 'Buscador ya inicializado',
                'textos_cargados': len(buscador_similares.df)
            })
    except Exception as e:
        logging.error(f"Error al inicializar buscador: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f"Error al inicializar buscador: {str(e)}"
        }), 500

@app.route('/buscar_similares', methods=['POST'])
def buscar_similares():
    """Busca textos similares a uno dado"""
    global buscador_similares
    
    try:
        logging.info(f"Recibida solicitud de búsqueda de textos similares: {request.json}")
        texto_consulta = request.json.get('texto', '')
        top_n = int(request.json.get('top_n', 5))
        
        if not texto_consulta:
            logging.warning("El texto de consulta está vacío")
            return jsonify({
                'error': 'El texto de consulta no puede estar vacío'
            }), 400
            
        logging.info(f"Buscando textos similares a: {texto_consulta}")
        
        # Verificar si el buscador ya está inicializado
        if buscador_similares is None:
            logging.info("Inicializando buscador por primera vez...")
            # Inicializar buscador con modelo gratuito
            buscador_similares = BuscadorTextosSimilares(
                csv_path=CSV_PATH if os.path.exists(CSV_PATH) else CSV_PATH_ORIGINAL,
                model_name="paraphrase-multilingual-MiniLM-L12-v2",
                cache_file="embeddings_cache.json"
            )
            
            # Cargar datos sin precalcular todos los embeddings para esta primera búsqueda
            # (solo se calcularán los necesarios)
            buscador_similares.cargar_datos(precalcular_embeddings=False)
            logging.info(f"Buscador inicializado con {len(buscador_similares.df)} textos")
        
        # Buscar similares
        resultados = buscador_similares.buscar_textos_similares(texto_consulta, top_n=top_n)
        logging.info(f"Resultados encontrados: {len(resultados)}")
        logging.info(f"Primer resultado: {resultados[0] if resultados else 'Ninguno'}")
        
        response_data = {'resultados': resultados}
        logging.info(f"Enviando respuesta con {len(resultados)} resultados")
        return jsonify(response_data)
    except Exception as e:
        logging.error(f"Error al buscar textos similares: {str(e)}")
        return jsonify({
            'error': str(e)
        }), 500

# Ruta para cargar más textos
@app.route('/cargar-mas-textos', methods=['POST'])
def cargar_mas_textos():
    """Carga más textos en el generador"""
    try:
        datos = request.json
        cantidad = datos.get('cantidad', 5000)  # Por defecto, cargar 5000 más
        
        # Reinicializar el generador con más textos
        global generador
        generador = GeneradorTextos(
            api_key=API_KEY,
            csv_path=CSV_PATH if os.path.exists(CSV_PATH) else CSV_PATH_ORIGINAL,
            output_dir=OUTPUT_DIR,
            cache_file=CACHE_FILE
        )
        generador.cargar_datos(limit=cantidad)
        
        return jsonify({
            'success': True,
            'mensaje': f'Se han cargado {len(generador.textos)} textos',
            'total_textos': len(generador.textos)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'mensaje': f'Error al cargar más textos: {str(e)}'
        }), 500

# Inicializar el generador al importar la aplicación
generador = None

# Inicializar el generador cuando se importa el módulo
print("Inicializando generador de textos...")
inicializar_generador()  # Sin límite para cargar todos los textos
print(f"Generador inicializado con {len(generador.textos) if generador else 0} textos.")

if __name__ == '__main__':
    import socket
    
    # Obtener la IP local para mostrarla
    def get_local_ip():
        try:
            # Crear un socket para determinar la IP local
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"
    
    # Obtener IP local
    local_ip = get_local_ip()
    port = int(os.environ.get("PORT", 5002))
    
    print("\n" + "="*50)
    print(f"Aplicación disponible en:")
    print(f"  * Local:            http://localhost:{port}")
    print(f"  * En tu red local:  http://{local_ip}:{port}")
    print("="*50 + "\n")
    
    # Iniciar servidor accesible desde la red
    app.run(debug=False, host='0.0.0.0', port=port, threaded=True)
