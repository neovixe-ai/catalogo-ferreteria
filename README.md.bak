# Catálogo de Ferretería

Sistema de extracción de catálogos de ferretería desde PDFs.

## Arquitectura

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   PDF Catálogo  │ ──→ │  IA con Visión   │ ──→ │ template.json   │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                       │
┌─────────────────┐     ┌──────────────────┐           │
│  Nuevo PDF      │ ──→ │  Extractor       │ ←─────────┘
└─────────────────┘     └──────────────────┘
                               │
                               ▼
                        ┌──────────────────┐
                        │  SQLite + Images │
                        └──────────────────┘
```

## Uso rápido

### Agregar un nuevo proveedor

1. **Analizar con IA** (ver `AGENTS.md`):
   - Convertir PDF a imágenes
   - Identificar patrones (SKU, precio, layout)
   - Crear template JSON

2. **Extraer catálogo**:
   ```bash
   python scraper/extractor.py --pdf "catalogo.pdf"
   ```

3. **Verificar resultados**:
   ```bash
   sqlite3 proveedores/{proveedor}/catalogo.db "SELECT COUNT(*) FROM productos"
   ls proveedores/{proveedor}/images/
   ```

### Agregar catálogo de proveedor existente

```bash
python scraper/extractor_con_actualizacion.py --pdf "nuevo_catalogo.pdf"
```

La lógica de fechas asegura:
- Precios de catálogos más nuevos prevalecen
- Productos nuevos se agregan
- No se duplican SKUs existentes

## Estructura

```
catalogo-ferreteria/
├── scraper/
│   ├── extractor_con_posiciones.py    # Extracción con imágenes
│   ├── extractor_con_actualizacion.py # Lógica de fechas
│   └── test_template.py              # Pruebas
├── templates/
│   └── lc_2050.json                   # Template del proveedor
├── proveedores/
│   └── lc_2050/
│       ├── catalogo.db                # SQLite (1,725+ productos)
│       └── images/                    # Imágenes extraídas
├── AGENTS.md                          # Guía para IA
└── README.md                          # Este archivo
```

## Template JSON

El template define las reglas de extracción. Ejemplo:

```json
{
  "proveedor": { "nombre": "...", "rif": "..." },
  "layout": { "columnas": 2, "filas": 5 },
  "producto": {
    "sku": { "formato": "[A-Z]{3}[0-9]{3}" },
    "precio": { "formato": "[0-9]+,[0-9]+\\$" }
  }
}
```

Ver `templates/lc_2050.json` como ejemplo completo.

## Base de Datos

**Esquema:**
- `sku`: Código único del producto
- `nombre`: Descripción del producto
- `precio_texto`: Precio con formato original
- `imagen_path`: Ruta a la imagen
- `fecha_catalogo`: Fecha del catálogo de origen

**Consultas útiles:**
```sql
-- Productos con precio
SELECT sku, nombre, precio_texto 
FROM productos 
WHERE precio_texto IS NOT NULL;

-- Buscar producto
SELECT * FROM productos 
WHERE nombre LIKE '%compresor%';

-- Productos por fecha de catálogo
SELECT fecha_catalogo, COUNT(*) 
FROM productos 
GROUP BY fecha_catalogo;
```

## Herramientas

| Herramienta | Uso |
|-------------|-----|
| `pdftotext -layout` | Extraer texto manteniendo posiciones |
| `PyMuPDF (fitz)` | Extraer imágenes con coordenadas |
| `sqlite3` | Consultar base de datos |

## Proveedor actual

**LC 2050** (DISTRIBUIDORA 2050 LC):
- RIF: J-50799044-3
- Template: `templates/lc_2050.json`
- Catálogos: Sep 2026, Ago 2026
- Productos: ~1,725
