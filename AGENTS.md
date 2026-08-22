# AGENTS.md — Instrucciones para IA que continúe este proyecto

## Contexto

Este es un scraper genérico de catálogos de ferretería. El primer objetivo es completar el scrape del proveedor **Barbosa** (Refrigeración Barbosa, ~5,131 productos). Actualmente hay **904 productos** en la base de datos.

## Qué hacer

1. **Continuar el scrape de Barbosa:**
   ```bash
   pip install -r scraper/requirements.txt
   python scraper/scraper.py --proveedor barbosa
   ```
   El scraper es idempotente: retoma donde se quedó, no duplica productos ni imágenes.

2. **Cuando termine (5,131 productos):**
   ```bash
   git add -A
   git commit -m "feat: scrape barbosa completado - 5131 productos"
   git push origin master
   ```

3. **Verificar integridad:**
   ```bash
   python3 -c "
   import sqlite3
   db = sqlite3.connect('proveedores/barbosa/catalogo.db')
   prods = db.execute('SELECT COUNT(*) FROM productos').fetchone()[0]
   cats = db.execute('SELECT COUNT(*) FROM categorias').fetchone()[0]
   imgs = db.execute('SELECT COUNT(*) FROM imagenes').fetchone()[0]
   print(f'Productos: {prods}/5131 | Categorías: {cats} | Imágenes: {imgs}')
   db.close()
   "
   ```

## Reglas importantes

- **NO duplicar productos**: El scraper usa SKU como identificador único. Si un SKU ya existe, actualiza en vez de insertar.
- **NO descargar imágenes duplicadas**: Verifica si el archivo local ya existe antes de descargar.
- **Respetar rate limits**: 0.3s entre requests. No aumentar.
- **No modificar config.json**: Los datos del proveedor ya están configurados.
- **No borrar catalogo.db**: El progreso acumulado es valioso.

## Estructura del proyecto

```
catalogo-ferreteria/
├── scraper/
│   ├── scraper.py              # Script principal (Python 3)
│   ├── requirements.txt        # requests, beautifulsoup4, lxml
│   └── config_example.json     # Template para nuevos proveedores
├── proveedores/
│   └── barbosa/
│       ├── config.json         # Config de Barbosa (6 sitemaps)
│       ├── catalogo.db         # SQLite con ~904 productos
│       └── images/             # ~934 imágenes descargadas
├── importadores/
│   ├── ferrepunto.js           # Importador para FerrePunto POS
│   └── exportar_csv.py         # Exportador CSV
└── README.md
```

## Base de datos SQLite

- `categorias`: id, nombre, slug, parent_id, total_productos
- `productos`: id, sku, nombre, descripcion, marca, categoria_id, url_original, imagen_principal, precio_texto
- `producto_meta`: id, producto_id, clave, valor
- `imagenes`: id, producto_id, url_original, local_path, es_principal

## Errores conocidos y soluciones

- **Foreign key constraint failed**: Si ocurre, el scraper lo ignora y continúa.
- **Timeout en imágenes**: Se reintentan automáticamente, las que fallan se saltan.
- **Productos con precio $0.00**: Es normal, los precios del sitio se cargan por JavaScript.

## Futuros proveedores

Para agregar un nuevo proveedor:
1. Crear `proveedores/nuevo_proveedor/config.json` basado en `scraper/config_example.json`
2. Ejecutar `python scraper/scraper.py --proveedor nuevo_proveedor`
3. El scraper crea la DB y descarga todo automáticamente
