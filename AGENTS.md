# AGENTS.md — Instrucciones para IA que continúe este proyecto

## Contexto

Este es un scraper genérico de catálogos de ferretería. Descarga productos, imágenes y categorías desde sitios web de proveedores y los guarda en SQLite. Diseñado para ser reutilizable con cualquier proveedor.

## Cómo usar

### 1. Agregar un nuevo proveedor

```bash
# Crear carpeta del proveedor
mkdir -p proveedores/mi_proveedor/images

# Copiar config de ejemplo
cp scraper/config_example.json proveedores/mi_proveedor/config.json

# Editar config.json con los datos del proveedor
# (base_url, sitemap_urls, rate_limit, etc.)
```

### 2. Ejecutar el scraper

```bash
pip install -r scraper/requirements.txt

# Modo piloto (20 productos de prueba)
python scraper/scraper.py --proveedor mi_proveedor --piloto

# Catálogo completo
python scraper/scraper.py --proveedor mi_proveedor
```

El scraper es idempotente: retoma donde se quedó, no duplica productos ni imágenes.

### 3. Exportar datos

```bash
# A CSV para Excel
python importadores/exportar_csv.py --proveedor mi_proveedor
```

## Reglas importantes

- **NO duplicar productos**: El scraper usa SKU como identificador único. Si un SKU ya existe, actualiza en vez de insertar.
- **NO descargar imágenes duplicadas**: Verifica si el archivo local ya existe antes de descargar.
- **Respetar rate limits**: Configurar `rate_limit_segundos` en config.json. No abusar.
- **No borrar catalogo.db**: El progreso acumulado es valioso.

## Estructura del proyecto

```
catalogo-ferreteria/
├── scraper/
│   ├── scraper.py              # Script principal (Python 3)
│   ├── requirements.txt        # requests, beautifulsoup4, lxml
│   └── config_example.json     # Template para nuevos proveedores
├── proveedores/
│   └── mi_proveedor/
│       ├── config.json         # Configuración del proveedor
│       ├── catalogo.db         # SQLite con productos
│       └── images/             # Imágenes descargadas
├── importadores/
│   └── exportar_csv.py         # Exportador CSV
└── README.md
```

## Base de datos SQLite

- `categorias`: id, nombre, slug, parent_id, total_productos
- `productos`: id, sku, nombre, descripcion, marca, categoria_id, url_original, imagen_principal, precio_texto
- `producto_meta`: id, producto_id, clave, valor
- `imagenes`: id, producto_id, url_original, local_path, es_principal

## Errores conocidos

- **Foreign key constraint failed**: Si ocurre, el scraper lo ignora y continúa.
- **Timeout en imágenes**: Se reintentan automáticamente, las que fallan se saltan.
- **Productos con precio $0.00**: Es normal, los precios del sitio se cargan por JavaScript.
