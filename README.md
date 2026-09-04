# Catálogo de Ferretería

Scraper genérico y reutilizable para descargar catálogos de productos de proveedores de ferretería. Cada proveedor tiene su propia carpeta con base de datos SQLite e imágenes descargadas.

## Estructura

```
catalogo-ferreteria/
├── scraper/
│   ├── scraper.py              # Script genérico reutilizable
│   ├── requirements.txt        # Dependencias Python
│   └── config_example.json     # Ejemplo de configuración
│
├── importadores/
│   └── exportar_csv.py         # Exportador → CSV para Excel
│
├── proveedores/
│   └── mi_proveedor/
│       ├── config.json         # Configuración del proveedor
│       ├── catalogo.db         # SQLite con productos
│       └── images/             # Imágenes descargadas
│       ├── config.json
│       ├── catalogo.db
│       └── images/
│
└── README.md
```

## Instalación

```bash
pip install -r scraper/requirements.txt
```

## Uso

### Scraping de un proveedor

```bash
# Modo piloto (20 productos de prueba)
python scraper/scraper.py --proveedor mi_proveedor --piloto

# Catálogo completo
python scraper/scraper.py --proveedor mi_proveedor
```

### Nuevo proveedor

1. Crear carpeta: `mkdir -p proveedores/mi_proveedor/images`
2. Copiar config: `cp scraper/config_example.json proveedores/mi_proveedor/config.json`
3. Editar config.json con los datos del proveedor
4. Ejecutar: `python scraper/scraper.py --proveedor mi_proveedor`

### Exportar a CSV

```bash
python importadores/exportar_csv.py --proveedor mi_proveedor
```

## Base de Datos SQLite

El catálogo se guarda en `proveedores/{nombre}/catalogo.db` con este esquema:

- **categorias**: id, nombre, slug, parent_id, total_productos
- **productos**: id, sku, nombre, descripcion, marca, categoria_id, url_original, imagen_principal, precio_texto
- **producto_meta**: id, producto_id, clave, valor (datos flexibles: stock, dimensiones, etc.)
- **imagenes**: id, producto_id, url_original, local_path, es_principal

### Consultas útiles

```sql
-- Productos por categoría
SELECT c.nombre, COUNT(*) FROM productos p
JOIN categorias c ON p.categoria_id = c.id
GROUP BY c.nombre ORDER BY COUNT(*) DESC;

-- Buscar producto
SELECT * FROM productos WHERE nombre LIKE '%compresor%';

-- Productos con imagen
SELECT sku, nombre, imagen_principal FROM productos
WHERE imagen_principal IS NOT NULL AND imagen_principal != '';
```
