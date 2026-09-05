# AGENTS.md — Guía para IA: Cómo agregar un nuevo proveedor

## Modelo Operacional

### Cómo funciona el sistema

```
┌─────────────────────────────────────────────────────────────┐
│  USUARIO                                                   │
│  "Quiero agregar el proveedor X con este catálogo PDF"     │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  IA - ACCIONES                                              │
│  1. git pull (obtener repo actualizado)                    │
│  2. Analizar PDF con visión                                │
│  3. Crear template                                         │
│  4. Extraer productos                                      │
│  5. Guardar en DB + imágenes                               │
│  6. git commit + push (subir cambios)                      │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  GITHUB                                                    │
│  - Repo actualizado                                        │
│  - DB sincronizada                                         │
│  - Imágenes del proveedor                                  │
│  - Template del proveedor                                  │
└─────────────────────────────────────────────────────────────┘
```

### Entornos soportados

| Entorno | Comando inicial |
|---------|-----------------|
| **Termux** | `cd ~/catalogo-ferreteria && git pull` |
| **Linux** | `cd ~/catalogo-ferreteria && git pull` |
| **Windows** | `cd %USERPROFILE%\catalogo-ferreteria && git pull` |

### Flujo de trabajo estándar

```bash
# 1. Actualizar repositorio
git pull

# 2. Ejecutar operación (ej: agregar catálogo)
python scraper/extractor.py --pdf "nuevo_catalogo.pdf"

# 3. Subir cambios
git add .
git commit -m "feat: agregar catálogo [Proveedor] [Fecha]"
git push
```

### Reglas de sincronización

- **SIEMPRE** hacer `git pull` antes de trabajar
- **SIEMPRE** hacer `git push` después de cambios
- La DB en GitHub es la fuente de verdad
- No trabajar sin conexión (offline)

---

## Flujo de trabajo cuando llega un catálogo PDF

```
┌─────────────────────────────────────────────────────────────┐
│  1. RECIBIR PDF                                             │
│     ├─→ git pull (asegurar repo actualizado)               │
│     └─→ Convertir primeras 3 páginas a imágenes (visión)   │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  2. EXTRAER DATOS CON VISIÓN                                │
│     ├─→ Nombre del proveedor                                │
│     ├─→ RIF                                                 │
│     ├─→ Fecha/período del catálogo                          │
│     └─→ Estructura visual (columnas, filas, formatos)       │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  3. VERIFICAR SI EL PROVEEDOR EXISTE EN LA BASE DE DATOS   │
│     │                                                       │
│     ├─→ NO EXISTE → Ir a PASO A                             │
│     └─→ EXISTE    → Ir a PASO B                             │
└─────────────────────────────────────────────────────────────┘
```

---

## PASO A: Proveedor NUEVO (no existe en DB)

```
┌─────────────────────────────────────────────────────────────┐
│  A1. CREAR TEMPLATE                                         │
│     ├─→ Analizar 5-10 páginas con visión                   │
│     ├─→ Identificar: formato SKU, posición nombre, precio  │
│     └─→ Crear templates/{proveedor}.json                    │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  A2. EXTRAER MUESTRA (5-10 páginas)                        │
│     ├─→ Ejecutar extractor con template                    │
│     └─→ Guardar en proveedores/{proveedor}/catalogo.db     │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  A3. VERIFICAR CON VISIÓN                                   │
│     ├─→ Comparar productos extraídos vs imagen del PDF     │
│     ├─→ ¿SKUs correctos? ¿Nombres completos? ¿Precios?   │
│     └─→ ¿Imágenes vinculadas correctamente?                │
└─────────────────────────────────────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
┌──────────────────────────┐  ┌──────────────────────────┐
│  A3a. VERIFICACIÓN OK    │  │  A3b. HAY ERRORES         │
│  → Preguntar si hay      │  │  → Corregir template      │
│    otro catálogo para    │  │  → Repetir desde A2       │
│    mejorar resultados    │  │                            │
└──────────────────────────┘  └──────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│  A4. SI HAY OTRO CATÁLOGO → Repetir desde A2 con nuevo PDF │
│     SI NO HAY → git commit + push                           │
└─────────────────────────────────────────────────────────────┘
```

---

## PASO B: Proveedor EXISTENTE (ya tiene template y DB)

```
┌─────────────────────────────────────────────────────────────┐
│  B1. LEER TEMPLATE EXISTENTE                                │
│     └─→ templates/{proveedor}.json                          │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  B2. EXTRAER MUESTRA (5-10 páginas) con template           │
│     └─→ Usar extractor_con_posiciones.py                   │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  B3. VERIFICAR CON VISIÓN                                   │
│     ├─→ Comparar muestra extraída vs PDF original          │
│     ├─→ ¿El template funciona correctamente?              │
│     └─→ ¿Hay productos nuevos o precios diferentes?       │
└─────────────────────────────────────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
┌──────────────────────────┐  ┌──────────────────────────┐
│  B3a. TEMPLATE OK        │  │  B3b. TEMPLATE FALLA     │
│  → Proceder a extracción │  │  → Actualizar template   │
│    completa              │  │  → Repetir desde B2      │
└──────────────────────────┘  └──────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│  B4. EXTRACCIÓN COMPLETA                                    │
│     ├─→ Ejecutar extractor con lógica de fechas            │
│     ├─→ Productos nuevos se insertan                        │
│     ├─→ Precios de catálogo más nuevo prevalecen           │
│     ├─→ git commit + push                                   │
│     └─→ Generar reporte de cambios                          │
└─────────────────────────────────────────────────────────────┘
```

---

## Requisitos para la IA

### Capacidades necesarias:
- **Visión**: Para analizar imágenes del PDF y verificar extracción
- **Terminal**: Para ejecutar scripts Python y comandos git
- **Archivos**: Para leer/escribir templates y scripts

### Herramientas del sistema:
```bash
# Git
git pull
git add .
git commit -m "mensaje"
git push

# Conversión PDF → imágenes
pdftoppm -jpeg -r 150 -f 1 -l 3 "catalogo.pdf" temp/page

# Extracción de texto
pdftotext -layout -f 1 -l 1 "catalogo.pdf" -

# PyMuPDF (imágenes con posiciones)
python3 -c "import fitz; doc=fitz.open('catalogo.pdf')..."

# SQLite
sqlite3 proveedores/{proveedor}/catalogo.db "SELECT..."
```

---

## Lógica de Negocio: Catálogo Semilla

### ¿Qué es el catálogo semilla?
El catálogo semilla es el **catálogo más nuevo** del proveedor. Es la **única referencia válida** para hacer pedidos.

### Reglas fundamentales:

| Regla | Descripción |
|-------|-------------|
| **Solo el nuevo vale** | Solo se puede pedir productos que estén en el catálogo nuevo |
| **Sin precio = no disponible** | Si un producto no tiene precio en el catálogo nuevo, no se puede pedir |
| **No está = descontinuado** | Si un producto no está en el catálogo nuevo, no se puede pedir |
| **Nunca borrar** | Los productos viejos quedan en DB como histórico, no se eliminan |
| **Precio nuevo prevalece** | El precio del catálogo nuevo es el único válido |

### Ejemplo práctico:

```
Catálogo Ago 2026 (viejo):  Productos A, B, C, D, E, F
Catálogo Sep 2026 (nuevo):  Productos A, B, C, D, G

DB resultante:
├─ A (de Sep) → Disponible, precio de Sep
├─ B (de Sep) → Disponible, precio de Sep
├─ C (de Sep) → Disponible, precio de Sep
├─ D (de Sep) → Disponible, precio de Sep
├─ E (de Ago) → NO disponible (no está en Sep)
├─ F (de Ago) → NO disponible (no está en Sep)
└─ G (de Sep) → Disponible, precio de Sep
```

### Para hacer pedidos:
```sql
-- Solo productos del catálogo nuevo con precio
SELECT sku, nombre, precio_texto 
FROM productos 
WHERE fecha_catalogo = '2026-09-04'  -- Fecha del catálogo nuevo
  AND precio_texto IS NOT NULL 
  AND precio_texto != '';
```

---

## Formato del Template JSON

Cada proveedor tiene su propio template. El template define:

```json
{
  "version": "1.0",
  "proveedor": {
    "nombre": "NOMBRE PROVEEDOR",
    "rif": "J-XXXXXXXX-X"
  },
  "catalogo": {
    "titulo": "Catálogo General",
    "periodo_formato": "DD/MM/YYYY"
  },
  "layout": {
    "productos_por_pagina": 10,
    "columnas": 2,
    "filas": 5
  },
  "producto": {
    "sku": {
      "formato": "[A-Z]{3}[0-9]{3}",
      "posicion": "superior_izquierda"
    },
    "nombre": {
      "case": "MAYUSCULAS",
      "max_lineas": 3,
      "posicion": "derecha_imagen"
    },
    "precio": {
      "formato": "[0-9]+,[0-9]+\\$",
      "posicion": "inferior"
    }
  },
  "extraccion": {
    "split_columna": 30,
    "filtrar_fondos_px": 200
  }
}
```

### Campos a definir por cada proveedor:

| Campo | Qué es | Ejemplos |
|-------|--------|----------|
| `productos_por_pagina` | Cuántos productos caben en una página | 5, 10, 15, 20 |
| `columnas` | Número de columnas | 1, 2, 3 |
| `filas` | Número de filas por columna | 3, 4, 5 |
| `sku.formato` | Patrón regex del SKU | `[A-Z]{3}[0-9]{3}`, `[0-9]{6}`, `XX-[0-9]{4}` |
| `sku.posicion` | Dónde está el SKU | `superior_izquierda`, `inferior`, `centro` |
| `nombre.case` | Mayúsculas o minúsculas | `MAYUSCULAS`, `Title Case` |
| `nombre.posicion` | Dónde está el nombre | `derecha_imagen`, `debajo_sku` |
| `precio.formato` | Patrón del precio | `[0-9]+,[0-9]+\\$`, `\\$[0-9]+\\.[0-9]+` |
| `precio.separador_decimal` | Qué usa como decimal | `coma`, `punto` |
| `split_columna` | Posición X para dividir columnas | Variable según ancho de página |

---

## Comandos de extracción

### Proveedor nuevo (primera vez):
```bash
# 1. Crear directorio
mkdir -p proveedores/{proveedor}/images

# 2. Extraer muestra
python3 scraper/extractor_con_posiciones.py --pdf "catalogo.pdf" --muestra 5

# 3. Verificar
sqlite3 proveedores/{proveedor}/catalogo.db "SELECT COUNT(*) FROM productos"
ls proveedores/{proveedor}/images/
```

### Proveedor existente:
```bash
# 1. Extraer con lógica de fechas
python3 scraper/extractor_con_actualizacion.py --pdf "nuevo_catalogo.pdf" --muestra 5

# 2. Verificar cambios
sqlite3 proveedores/{proveedor}/catalogo.db "SELECT COUNT(*) FROM productos WHERE fecha_catalogo = '2026-XX-XX'"
```

---

## Lógica de extracción por fechas

| Condición del SKU | Fecha catálogo | Acción |
|-------------------|----------------|--------|
| No existe | Cualquiera | INSERTAR |
| Existe | Más nueva que DB | ACTUALIZAR precio |
| Existe | Más vieja que DB | NO TOCAR |
| Existe | Igual que DB | NO TOCAR |

**Importante:** NUNCA eliminar productos. Solo insertar o actualizar.

---

## Verificación con visión

Al verificar la muestra, la IA debe:

1. **Comparar SKUs**: ¿Los códigos coinciden con el PDF?
2. **Comparar nombres**: ¿Están completos o truncados?
3. **Comparar precios**: ¿Son correctos?
4. **Comparar imágenes**: ¿Corresponden al producto?
5. **Contar productos**: ¿Cuántos por página como esperado?

Si hay más de 2-3 errores → actualizar template y reintentar.

---

## Tipos de layouts comunes

### Layout A: 2 columnas × 5 filas (10 productos/página)
```
┌─────────────┬─────────────┐
│  Producto1  │  Producto2  │
├─────────────┼─────────────┤
│  Producto3  │  Producto4  │
├─────────────┼─────────────┤
│  Producto5  │  Producto6  │
├─────────────┼─────────────┤
│  Producto7  │  Producto8  │
├─────────────┼─────────────┤
│  Producto9  │  Producto10 │
└─────────────┴─────────────┘
```

### Layout B: 1 columna (5-10 productos/página)
```
┌─────────────────────────┐
│      Producto1         │
├─────────────────────────┤
│      Producto2         │
├─────────────────────────┤
│      Producto3         │
└─────────────────────────┘
```

### Layout C: 3 columnas (15 productos/página)
```
┌───────────┬───────────┬───────────┤
│  Prod1    │  Prod2    │  Prod3    │
├───────────┼───────────┼───────────┤
│  Prod4    │  Prod5    │  Prod6    │
└───────────┴───────────┴───────────┘
```

### Layout D: Tabla/lista (productos continuos)
```
┌─────────────────────────────────────┐
│ SKU  │ Nombre           │ Precio   │
├─────────────────────────────────────┤
│ 001  │ Producto A       │ $10.00   │
│ 002  │ Producto B       │ $15.00   │
│ 003  │ Producto C       │ $20.00   │
└─────────────────────────────────────┘
```

---

## Errores comunes y soluciones

| Error | Causa | Solución |
|-------|-------|----------|
| Precios no se extraen | Formato incorrecto | Ajustar regex en template |
| Nombres truncados | Split en posición incorrecta | Modificar `split_columna` |
| Imágenes desordenadas | PyMuPDF no respeta orden | Usar `get_image_rects()` |
| SKU duplicado | Producto repetido en PDF | Verificar antes de insertar |
| Columnas mezcladas | Layout diferente al esperado | Re-analizar con visión |
| Precio en nombre | Regex no detecta precio | Ajustar patrón de precio |
| Página sin productos | Es página de publicidad | Omitir en el template |

---

## Métricas de calidad

### Extracción aceptable (90%+):
- SKUs correctos: 95%+
- Nombres completos: 90%+
- Precios correctos: 95%+
- Imágenes correctas: 85%+

### Necesita ajuste (menos del 90%):
- Actualizar template
- Re-extraer muestra
- Verificar nuevamente

---

## Tipos de SKU comunes

| Formato | Ejemplo | Proveedor típico |
|---------|---------|------------------|
| 3 letras + 3 números | COC378 | Ferretería general |
| 6 números | 123456 | Electrónica |
| 2 letras + guión + 4 números | AB-1234 | Repuestos |
| 4 letras + 4 números | ABCD1234 | Industrial |
| Alfanumérico mixto | A1B2C3 | Varios |

---

## Tipos de precio comunes

| Formato | Ejemplo | Región |
|---------|---------|--------|
| Coma decimal + $ | 1,23$ | Venezuela |
| Punto decimal + $ | $1.23 | Internacional |
| Solo número | 1.23 | Algunos catálogos |
| Con separador de miles | 1,234.56 | Formato largo |

---

## Archivos del proyecto

```
catalogo-ferreteria/
├── AGENTS.md                           # Este archivo
├── README.md                           # Documentación general
├── scraper/
│   ├── extractor_con_posiciones.py     # Extracción con imágenes
│   ├── extractor_con_actualizacion.py  # Lógica de fechas
│   └── test_template.py               # Pruebas
├── templates/
│   └── {proveedor}.json                # Template por proveedor
└── proveedores/
    └── {proveedor}/
        ├── catalogo.db                 # Base de datos
        └── images/                     # Imágenes
```
