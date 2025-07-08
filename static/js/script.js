// Elementos del DOM
const generarBtn = document.getElementById('generar-btn');
const generarLoteBtn = document.getElementById('generar-lote-btn');
const copiarTodosBtn = document.getElementById('copiar-todos-btn');
const descargarBtn = document.getElementById('descargar-btn');
const limpiarBtn = document.getElementById('limpiar-btn');
const temperaturaSlider = document.getElementById('temperatura');
const tempValue = document.getElementById('temp-value');
const textosContainer = document.getElementById('textos-container');
const loadingElement = document.getElementById('loading');
const statsContent = document.getElementById('stats-content');
const cargarMasBtn = document.getElementById('cargar-mas-btn');
const cargaInfo = document.getElementById('carga-info');
const btnBuscarSimilares = document.getElementById('btnBuscarSimilares');
const textoConsulta = document.getElementById('textoConsulta');

// Contador para IDs únicos
let textoCounter = 0;

// Actualizar el valor mostrado del slider de temperatura
temperaturaSlider.addEventListener('input', function() {
    tempValue.textContent = this.value;
});

// Función para mostrar un error
function mostrarError(mensaje) {
    const errorModal = new bootstrap.Modal(document.getElementById('errorModal'));
    document.getElementById('error-message').textContent = mensaje;
    errorModal.show();
}

// Función para mostrar una notificación
function mostrarNotificacion(mensaje, tipo) {
    // Crear el elemento de notificación
    const notificacion = document.createElement('div');
    notificacion.className = `alert alert-${tipo} alert-dismissible fade show notification-toast`;
    notificacion.innerHTML = `
        ${mensaje}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    // Añadir al contenedor de notificaciones
    const notificacionesContainer = document.getElementById('notificaciones-container');
    if (!notificacionesContainer) {
        // Si no existe el contenedor, crearlo
        const container = document.createElement('div');
        container.id = 'notificaciones-container';
        container.className = 'position-fixed bottom-0 end-0 p-3';
        container.style.zIndex = '5000';
        document.body.appendChild(container);
        container.appendChild(notificacion);
    } else {
        notificacionesContainer.appendChild(notificacion);
    }
    
    // Auto-cerrar después de 5 segundos
    setTimeout(() => {
        notificacion.classList.remove('show');
        setTimeout(() => {
            notificacion.remove();
        }, 300);
    }, 5000);
}

// Función para mostrar el indicador de carga
function mostrarCarga(mostrar) {
    if (mostrar) {
        loadingElement.classList.remove('d-none');
    } else {
        loadingElement.classList.add('d-none');
    }
}

// Función para obtener los valores del formulario
function obtenerValoresFormulario() {
    return {
        categoria: document.getElementById('categoria').value,
        estilo: document.getElementById('estilo').value,
        tema: document.getElementById('tema').value,
        temperatura: document.getElementById('temperatura').value,
        modelo: document.getElementById('modelo').value,
        cantidad: document.getElementById('cantidad').value
    };
}

// Función para crear una tarjeta de texto
function crearTarjetaTexto(texto, index = null) {
    const id = `texto-${textoCounter++}`;
    const timestamp = new Date().toLocaleTimeString();
    const categoriaSeleccionada = document.getElementById('categoria').value;
    
    // Eliminar el mensaje de bienvenida si existe
    const welcomeMessage = document.querySelector('.welcome-message');
    if (welcomeMessage) {
        welcomeMessage.remove();
    }
    
    const tarjeta = document.createElement('div');
    tarjeta.className = 'texto-card';
    tarjeta.id = id;
    tarjeta.dataset.categoria = categoriaSeleccionada;
    
    // Crear clase CSS para la categoría
    const categoriaClass = `categoria-${categoriaSeleccionada.replace(/\s+/g, '_').toLowerCase()}`;
    
    tarjeta.innerHTML = `
        <div class="texto-header">
            <span>${index !== null ? `Texto #${index + 1}` : 'Texto generado'} <small class="text-muted">${timestamp}</small></span>
            <div class="header-actions">
                <span class="categoria-badge ${categoriaClass}">${categoriaSeleccionada !== 'ninguna' ? categoriaSeleccionada : 'general'}</span>
            </div>
        </div>
        <div class="texto-body">${texto}</div>
        <div class="texto-footer">
            <button class="btn btn-sm btn-outline-primary copiar-btn" data-id="${id}">
                <i class="fas fa-copy"></i> Copiar
            </button>
            <button class="btn btn-sm btn-outline-success buscar-similares-btn" data-id="${id}">
                <i class="fas fa-search"></i> Buscar similares
            </button>
            <button class="btn btn-sm btn-outline-danger eliminar-btn" data-id="${id}">
                <i class="fas fa-trash"></i> Eliminar
            </button>
        </div>
    `;
    
    // Agregar al principio del contenedor
    textosContainer.insertBefore(tarjeta, textosContainer.firstChild);
    
    // Agregar event listeners
    tarjeta.querySelector('.copiar-btn').addEventListener('click', function() {
        const textoBody = document.querySelector(`#${id} .texto-body`).textContent;
        navigator.clipboard.writeText(textoBody)
            .then(() => {
                const btn = this;
                const originalText = btn.innerHTML;
                btn.innerHTML = '<i class="fas fa-check"></i> Copiado';
                setTimeout(() => {
                    btn.innerHTML = originalText;
                }, 2000);
            })
            .catch(err => mostrarError('Error al copiar: ' + err));
    });
    
    tarjeta.querySelector('.eliminar-btn').addEventListener('click', function() {
        document.getElementById(id).remove();
        
        // Mostrar mensaje de bienvenida si no hay textos
        if (textosContainer.children.length === 0) {
            mostrarMensajeBienvenida();
        }
    });
    
    return tarjeta;
}

// Función para mostrar el mensaje de bienvenida
function mostrarMensajeBienvenida() {
    textosContainer.innerHTML = `
        <div class="welcome-message text-center">
            <i class="fas fa-pen-fancy display-1 text-muted mb-3"></i>
            <h3>Bienvenido al Generador de Textos</h3>
            <p>Usa el panel lateral para configurar y generar textos estilo Instagram.</p>
        </div>
    `;
}

// Función para generar un texto
function generarTexto() {
    mostrarCarga(true);
    
    const formData = new FormData();
    const valores = obtenerValoresFormulario();
    
    Object.keys(valores).forEach(key => {
        formData.append(key, valores[key]);
    });
    
    fetch('/generar', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        mostrarCarga(false);
        
        if (data.success) {
            crearTarjetaTexto(data.texto);
        } else {
            mostrarError('Error al generar texto: ' + data.error);
        }
    })
    .catch(error => {
        mostrarCarga(false);
        mostrarError('Error de conexión: ' + error);
    });
}

// Función para generar un lote de textos
function generarLote() {
    mostrarCarga(true);
    
    const formData = new FormData();
    const valores = obtenerValoresFormulario();
    
    Object.keys(valores).forEach(key => {
        formData.append(key, valores[key]);
    });
    
    fetch('/generar-lote', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        mostrarCarga(false);
        
        if (data.success) {
            // Crear tarjetas para cada texto
            data.textos.forEach((texto, index) => {
                crearTarjetaTexto(texto, index);
            });
            
            // Mostrar notificación de archivo guardado
            const toast = document.createElement('div');
            toast.className = 'position-fixed bottom-0 end-0 p-3';
            toast.style.zIndex = '5';
            toast.innerHTML = `
                <div class="toast show" role="alert" aria-live="assertive" aria-atomic="true">
                    <div class="toast-header">
                        <strong class="me-auto">Textos guardados</strong>
                        <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
                    </div>
                    <div class="toast-body">
                        Lote guardado en: ${data.archivo}
                    </div>
                </div>
            `;
            document.body.appendChild(toast);
            
            // Eliminar la notificación después de 5 segundos
            setTimeout(() => {
                toast.remove();
            }, 5000);
        } else {
            mostrarError('Error al generar lote: ' + data.error);
        }
    })
    .catch(error => {
        mostrarCarga(false);
        mostrarError('Error de conexión: ' + error);
    });
}

// Función para copiar todos los textos
function copiarTodos() {
    const textos = Array.from(document.querySelectorAll('.texto-body'))
        .map(el => el.textContent)
        .join('\n\n---\n\n');
    
    if (textos.length === 0) {
        mostrarError('No hay textos para copiar');
        return;
    }
    
    navigator.clipboard.writeText(textos)
        .then(() => {
            const originalText = copiarTodosBtn.innerHTML;
            copiarTodosBtn.innerHTML = '<i class="fas fa-check"></i> Copiado';
            setTimeout(() => {
                copiarTodosBtn.innerHTML = originalText;
            }, 2000);
        })
        .catch(err => mostrarError('Error al copiar: ' + err));
}

// Función para descargar todos los textos
function descargarTextos() {
    const textos = Array.from(document.querySelectorAll('.texto-body'))
        .map(el => el.textContent)
        .join('\n\n---\n\n');
    
    if (textos.length === 0) {
        mostrarError('No hay textos para descargar');
        return;
    }
    
    const blob = new Blob([textos], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    
    a.href = url;
    a.download = `textos_instagram_${new Date().toISOString().slice(0, 10)}.txt`;
    document.body.appendChild(a);
    a.click();
    
    setTimeout(() => {
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    }, 0);
}

// Función para limpiar todos los textos
function limpiarTextos() {
    textosContainer.innerHTML = '';
    mostrarMensajeBienvenida();
}

// Función para cargar estadísticas
function cargarEstadisticas() {
    fetch('/estadisticas')
        .then(response => response.json())
        .then(data => {
            let html = '<div class="stats-list">';
            
            // Mostrar total primero
            html += `<div class="stats-item">
                <strong>Total textos:</strong>
                <span>${data.total || 0}</span>
            </div>`;
            
            // Mostrar categorías ordenadas por cantidad
            const categorias = Object.keys(data)
                .filter(key => key !== 'total')
                .sort((a, b) => data[b] - data[a]);
            
            // Crear filtros de categoría
            let filtrosHtml = '<div class="categoria-filters mb-3"><h6 class="w-100">Filtrar por categoría:</h6>';
            
            // Añadir filtro para todas las categorías
            filtrosHtml += `<span class="categoria-badge categoria-filter active" data-categoria="todas">Todas</span>`;
            
            categorias.forEach(categoria => {
                // Crear clase CSS para la categoría
                const categoriaClass = `categoria-${categoria.replace(/\s+/g, '_').toLowerCase()}`;
                filtrosHtml += `<span class="categoria-badge ${categoriaClass} categoria-filter" data-categoria="${categoria}">${categoria}</span>`;
            });
            
            filtrosHtml += '</div>';
            
            // Añadir filtros antes de las estadísticas
            html = filtrosHtml + html;
            
            // Añadir estadísticas por categoría
            categorias.forEach(categoria => {
                // Crear clase CSS para la categoría
                const categoriaClass = `categoria-${categoria.replace(/\s+/g, '_').toLowerCase()}`;
                html += `<div class="stats-item">
                    <span><span class="categoria-badge ${categoriaClass}">${categoria}</span></span>
                    <span>${data[categoria]}</span>
                </div>`;
            });
            
            html += '</div>';
            statsContent.innerHTML = html;
            
            // Añadir event listeners a los filtros
            document.querySelectorAll('.categoria-filter').forEach(filtro => {
                filtro.addEventListener('click', function() {
                    const categoria = this.dataset.categoria;
                    
                    // Actualizar estado activo
                    document.querySelectorAll('.categoria-filter').forEach(f => f.classList.remove('active'));
                    this.classList.add('active');
                    
                    // Filtrar tarjetas
                    filtrarTarjetasPorCategoria(categoria);
                });
            });
        })
        .catch(error => {
            statsContent.innerHTML = '<p class="text-danger">Error al cargar estadísticas</p>';
            console.error('Error al cargar estadísticas:', error);
        });
}

// Función para filtrar tarjetas por categoría
function filtrarTarjetasPorCategoria(categoria) {
    const tarjetas = document.querySelectorAll('.texto-card');
    
    if (categoria === 'todas') {
        // Mostrar todas las tarjetas
        tarjetas.forEach(tarjeta => {
            tarjeta.style.display = 'block';
        });
    } else {
        // Mostrar solo las tarjetas de la categoría seleccionada
        tarjetas.forEach(tarjeta => {
            if (tarjeta.dataset.categoria === categoria) {
                tarjeta.style.display = 'block';
            } else {
                tarjeta.style.display = 'none';
            }
        });
    }
}

// Función para cargar más textos
function cargarMasTextos() {
    // Mostrar indicador de carga
    cargarMasBtn.disabled = true;
    cargarMasBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Cargando...';
    cargaInfo.textContent = 'Cargando textos adicionales...';
    
    // Cantidad a cargar (puedes ajustar esto o hacer que sea configurable)
    const cantidad = 5000;
    
    // Llamar al endpoint
    fetch('/cargar-mas-textos', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ cantidad: cantidad })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Actualizar información
            cargaInfo.textContent = data.mensaje;
            
            // Recargar estadísticas
            cargarEstadisticas();
            
            // Mostrar notificación
            mostrarNotificacion('Textos cargados correctamente', 'success');
        } else {
            cargaInfo.textContent = data.mensaje;
            mostrarNotificacion('Error al cargar textos', 'danger');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        cargaInfo.textContent = 'Error al cargar textos adicionales';
        mostrarNotificacion('Error al cargar textos', 'danger');
    })
    .finally(() => {
        // Restaurar botón
    });
}

// Variable para controlar si el buscador ya ha sido inicializado
let buscadorInicializado = false;

// Función para inicializar el buscador de textos similares
async function inicializarBuscador() {
    if (buscadorInicializado) {
        return;
    }
    
    // Mostrar mensaje de inicialización
    const loadingElement = document.getElementById('loading-similares');
    loadingElement.style.display = 'block';
    loadingElement.innerHTML = '<div class="spinner-border text-primary" role="status"></div><p>Inicializando buscador de textos similares por primera vez...</p><p class="text-muted">Esto puede tardar unos momentos pero solo ocurre una vez.</p>';
    
    try {
        // Enviar solicitud al servidor
        const response = await fetch('/inicializar_buscador');
        
        if (!response.ok) {
            throw new Error('Error al inicializar el buscador');
        }
        
        const data = await response.json();
        buscadorInicializado = true;
        
        // Mostrar notificación de éxito
        mostrarNotificacion(`Buscador inicializado con ${data.textos_cargados} textos`, 'success');
    } catch (error) {
        console.error('Error:', error);
        mostrarError('Error al inicializar el buscador: ' + error.message);
        throw error;
    }
}

// Función para buscar textos similares
async function buscarTextosSimilares(texto) {
    if (!texto || texto.trim() === '') {
        mostrarError('Por favor, introduce un texto para buscar similares.');
        return;
    }
    
    // Mostrar indicador de carga
    const loadingElement = document.getElementById('loading-similares');
    loadingElement.style.display = 'block';
    loadingElement.innerHTML = '<div class="spinner-border text-primary" role="status"></div><p>Buscando textos similares...</p>';
    
    try {
        // Primero inicializar el buscador si es necesario
        await inicializarBuscador();
        
        // Enviar solicitud al servidor
        const response = await fetch('/buscar_similares', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                texto: texto.trim(),
                top_n: 5
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            // Ocultar indicador de carga
            loadingElement.style.display = 'none';
            
            // Mostrar resultados
            mostrarResultadosSimilares(texto, data.resultados);
            
            // Mostrar notificación de éxito
            mostrarNotificacion(`Se encontraron ${data.resultados.length} textos similares`, 'success');
        } else {
            // Ocultar indicador de carga
            loadingElement.style.display = 'none';
            
            // Mostrar error
            mostrarError(`Error: ${data.error || 'No se pudieron encontrar textos similares'}`);
        }
    } catch (error) {
        console.error('Error:', error);
        loadingElement.style.display = 'none';
        mostrarError(`Error: ${error.message}`);
    }
}

// Función para obtener un color para cada categoría
function getCategoriaColor(categoria) {
    // Mapa de colores por categoría
    const coloresCategoria = {
        'amor_relaciones': '#FF6B81',
        'motivacional_superacion': '#4CAF50',
        'humor_entretenimiento': '#FF9800',
        'reflexion_filosofica': '#2196F3',
        'autoestima_autoayuda': '#9C27B0',
        'critica_social': '#F44336',
        'vida_cotidiana': '#795548',
        'anuncio_evento': '#607D8B',
        'cita_literaria': '#673AB7',
        'minimalista': '#009688',
        'otro': '#9E9E9E',
        'sin_categoria': '#9E9E9E'
    };
    
    // Si la categoría existe en el mapa, devolver su color, si no, un color por defecto
    return coloresCategoria[categoria] || '#9E9E9E';
}

// Función para mostrar los resultados de la búsqueda
function mostrarResultadosSimilares(textoConsulta, resultados) {
    // Obtener el contenedor de resultados
    const resultadosContainer = document.getElementById('resultados-similares');
    const resultadosContenido = document.getElementById('resultados-similares-contenido');
    
    // Limpiar el contenedor de resultados previos
    resultadosContenido.innerHTML = '';
    
    // Mostrar el contenedor de resultados
    resultadosContainer.style.display = 'block';
    
    // Añadir el texto de consulta
    const consultaDiv = document.createElement('div');
    consultaDiv.className = 'consulta-texto mb-3 p-3 bg-light rounded';
    consultaDiv.innerHTML = `
        <h5>Texto consultado:</h5>
        <p>${textoConsulta}</p>
    `;
    resultadosContenido.appendChild(consultaDiv);
    
    // Crear lista de resultados
    const listaResultados = document.createElement('div');
    listaResultados.className = 'lista-resultados';
    
    // Añadir cada resultado
    resultados.forEach((resultado, index) => {
        const resultadoItem = document.createElement('div');
        resultadoItem.className = 'resultado-item card mb-3';
        
        // Determinar el color de fondo según el porcentaje de similitud
        let bgClass = 'bg-light';
        if (resultado.similitud_porcentaje > 90) {
            bgClass = 'bg-success text-white';
        } else if (resultado.similitud_porcentaje > 75) {
            bgClass = 'bg-info text-white';
        } else if (resultado.similitud_porcentaje > 60) {
            bgClass = 'bg-primary text-white';
        } else if (resultado.similitud_porcentaje > 45) {
            bgClass = 'bg-warning';
        }
        
        resultadoItem.innerHTML = `
            <div class="card-header d-flex justify-content-between align-items-center ${bgClass}">
                <span>Similitud: ${resultado.similitud_porcentaje}%</span>
                <span class="badge categoria-badge" style="background-color: ${getCategoriaColor(resultado.categoria)}">
                    ${resultado.categoria}
                </span>
            </div>
            <div class="card-body">
                <p>${resultado.texto}</p>
            </div>
        `;
        
        listaResultados.appendChild(resultadoItem);
    });
    
    // Añadir la lista de resultados al contenedor
    resultadosContenido.appendChild(listaResultados);
}

// Event listeners
generarBtn.addEventListener('click', generarTexto);
generarLoteBtn.addEventListener('click', generarLote);
copiarTodosBtn.addEventListener('click', copiarTodos);
descargarBtn.addEventListener('click', descargarTextos);
limpiarBtn.addEventListener('click', limpiarTextos);
cargarMasBtn.addEventListener('click', cargarMasTextos);
btnBuscarSimilares.addEventListener('click', (event) => {
    event.preventDefault();
    buscarTextosSimilares(textoConsulta.value);
});

// Event listener para buscar similares desde un texto generado
document.addEventListener('click', function(event) {
    if (event.target.classList.contains('buscar-similares-btn') || 
        event.target.closest('.buscar-similares-btn')) {
        const textoCard = event.target.closest('.texto-card');
        if (textoCard) {
            const textoElement = textoCard.querySelector('.texto-body');
            if (textoElement) {
                const texto = textoElement.textContent;
                textoConsulta.value = texto;
                buscarTextosSimilares(texto);
            }
        }
    }
});

// Inicializar
document.addEventListener('DOMContentLoaded', function() {
    cargarEstadisticas();
});
