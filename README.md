# Generador de Textos Instagram

Aplicación web para generar y clasificar textos en estilo Instagram usando IA, con búsqueda de textos similares mediante embeddings locales.

## Características

- Generación de textos en estilo Instagram usando OpenAI GPT
- Clasificación automática de textos en categorías usando IA
- Búsqueda de textos similares mediante embeddings locales (sentence-transformers)
- Interfaz web para visualizar y filtrar textos por categoría
- Estadísticas de distribución de categorías
- Carga completa de todos los textos disponibles

## Requisitos

- Python 3.9+
- Dependencias listadas en `requirements.txt`

## Instalación Local

1. Clona este repositorio o descárgalo como ZIP
2. Crea un entorno virtual e instala las dependencias:

```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Asegúrate de tener una clave API válida de OpenAI en una variable de entorno:

```bash
export OPENAI_API_KEY="tu-clave-api"  # En Windows: set OPENAI_API_KEY=tu-clave-api
```

## Uso Local

### Iniciar la aplicación web

```bash
python app.py
```

La aplicación estará disponible en:
- Local: http://localhost:5002
- Red local: http://[tu-ip-local]:5002

## Despliegue para Equipo

Existen varias opciones para desplegar esta aplicación y permitir que tu equipo la utilice:

### Opción 1: Despliegue en Heroku

1. Crea una cuenta en [Heroku](https://www.heroku.com/) si aún no tienes una
2. Instala la [CLI de Heroku](https://devcenter.heroku.com/articles/heroku-cli)
3. Inicia sesión en Heroku desde la terminal:

```bash
heroku login
```

4. Crea una nueva aplicación en Heroku:

```bash
heroku create nombre-de-tu-app
```

5. Configura la variable de entorno para la API de OpenAI:

```bash
heroku config:set OPENAI_API_KEY="tu-clave-api"
```

6. Despliega la aplicación:

```bash
git add .
git commit -m "Preparar para despliegue"
git push heroku main
```

7. Abre la aplicación:

```bash
heroku open
```

### Opción 2: Despliegue en Render

1. Crea una cuenta en [Render](https://render.com/)
2. Conecta tu repositorio de GitHub o sube el código directamente
3. Crea un nuevo servicio web
4. Configura el servicio:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn wsgi:app`
5. Añade la variable de entorno `OPENAI_API_KEY`
6. Despliega la aplicación

### Opción 3: Despliegue en servidor propio

Si tienes acceso a un servidor:

1. Clona el repositorio en el servidor
2. Instala las dependencias
3. Configura un servidor WSGI como Gunicorn:

```bash
gunicorn --bind 0.0.0.0:5002 wsgi:app
```

4. Configura un proxy inverso como Nginx para servir la aplicación

## Notas importantes para el despliegue

- La aplicación utiliza modelos de sentence-transformers para la búsqueda de textos similares, lo que requiere suficiente memoria RAM (al menos 2GB)
- Los archivos de caché de embeddings se guardan localmente, asegúrate de que la plataforma de despliegue permita almacenamiento persistente
- Para equipos grandes, considera aumentar el número de workers de Gunicorn

Cualquier miembro del equipo en la misma red podrá acceder usando la URL de red local.

### Clasificar textos

Para clasificar textos o reanudar una clasificación interrumpida:

```bash
# Reanudar la clasificación desde donde se quedó
python clasificador_textos_ai.py --reanudar

# Usar GPT-4 para mayor precisión (más costoso)
python clasificador_textos_ai.py --reanudar --modelo gpt-4

# Ajustar parámetros de procesamiento
python clasificador_textos_ai.py --reanudar --batch 20 --guardar_cada 10
```

### Generar textos

La generación de textos se realiza desde la interfaz web. Selecciona una categoría y haz clic en "Generar".

## Estructura del proyecto

- `app.py`: Aplicación web Flask
- `generador_textos.py`: Script para generar textos usando OpenAI
- `clasificador_textos_ai.py`: Script para clasificar textos en categorías
- `templates/`: Plantillas HTML
- `static/`: Archivos estáticos (CSS, JS, imágenes)

## Notas

- La aplicación carga automáticamente todos los textos disponibles al iniciar
- Los textos generados se guardan en la carpeta `textos_generados`
- El caché de categorías se guarda en `categorias_cache.json`
