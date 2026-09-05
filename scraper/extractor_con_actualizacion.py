#!/usr/bin/env python3
"""
Extractor con lógica de actualización por fecha
- Si SKU existe y catálogo es más nuevo → Actualizar precio
- Si SKU existe y catálogo es más viejo → No tocar
- Si SKU no existe → Insertar completo
"""
import json
import os
import re
import sqlite3
import subprocess
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = RAIZ / "templates" / "lc_2050.json"
DB_PATH = RAIZ / "proveedores" / "lc_2050" / "catalogo.db"
IMAGES_DIR = RAIZ / "proveedores" / "lc_2050" / "images"


def cargar_template():
    with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def extraer_texto_pdf(pdf_path: str, pagina: int) -> str:
    result = subprocess.run(
        ["pdftotext", "-layout", "-f", str(pagina), "-l", str(pagina), pdf_path, "-"],
        capture_output=True, text=True
    )
    return result.stdout


def parsear_productos(texto: str) -> list:
    productos = []
    lineas = texto.split('\n')
    patron_sku = re.compile(r'^([A-Z]{3}\d{3})\s+([A-Z]{3}\d{3})')
    
    i = 0
    while i < len(lineas):
        match = patron_sku.search(lineas[i])
        if match:
            sku1, sku2 = match.group(1), match.group(2)
            bloques_izq, bloques_der, precios = [], [], []
            
            j = i + 1
            while j < len(lineas):
                linea = lineas[j]
                if patron_sku.search(linea):
                    break
                COL_SPLIT = 30
                if len(linea) > COL_SPLIT:
                    izq, der = linea[:COL_SPLIT].strip(), linea[COL_SPLIT:].strip()
                else:
                    izq, der = linea.strip(), ''
                
                for lado, txt in [('izq', izq), ('der', der)]:
                    precio_match = re.search(r'(\d+[.,]\d+)\$', txt)
                    if precio_match:
                        precios.append((lado, precio_match.group(1)))
                    elif txt and not re.match(r'^[A-Z]{3}\d{3}', txt):
                        if lado == 'izq':
                            bloques_izq.append(txt)
                        else:
                            bloques_der.append(txt)
                j += 1
            
            nombre1 = re.sub(r'-\s+', '', ' '.join(bloques_izq))
            nombre1 = re.sub(r'\s+', ' ', nombre1).strip()
            nombre2 = re.sub(r'-\s+', '', ' '.join(bloques_der))
            nombre2 = re.sub(r'\s+', ' ', nombre2).strip()
            
            precio1 = next((p for l, p in precios if l == 'izq'), None)
            precio2 = next((p for l, p in precios if l == 'der'), None)
            
            if sku1 and nombre1:
                productos.append({'sku': sku1, 'nombre': nombre1, 'precio': precio1})
            if sku2 and nombre2:
                productos.append({'sku': sku2, 'nombre': nombre2, 'precio': precio2})
            i = j
        else:
            i += 1
    return productos


def extraer_imagenes_orden(pdf_path: str, pagina: int) -> list:
    """Extrae imágenes ordenadas por posición visual."""
    import fitz
    
    doc = fitz.open(pdf_path)
    page = doc[pagina - 1]
    images = page.get_images(full=True)
    
    items = []
    for img in images:
        xref = img[0]
        rects = page.get_image_rects(xref)
        if rects:
            rect = rects[0]
            if rect.width < 200 and rect.height < 200:
                items.append({
                    'xref': xref,
                    'x': rect.x0,
                    'y': rect.y0,
                    'w': rect.width,
                    'h': rect.height
                })
    
    items.sort(key=lambda p: (p['y'] // 100, p['x']))
    
    # Guardar imágenes
    rutas = []
    for i, item in enumerate(items):
        pix = fitz.Pixmap(doc, item['xref'])
        if pix.n - pix.alpha > 3:
            pix = fitz.Pixmap(fitz.csRGB, pix)
        elif pix.alpha:
            pix = fitz.Pixmap(pix, 0)
        
        out_path = IMAGES_DIR / f"temp_{pagina}_{i:02d}.jpg"
        pix.save(str(out_path))
        rutas.append(str(out_path))
    
    doc.close()
    return rutas


def crear_base_datos():
    """Crea la base de datos si no existe."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    
    db = sqlite3.connect(str(DB_PATH))
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA foreign_keys=ON")
    
    db.executescript("""
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT UNIQUE,
            nombre TEXT NOT NULL,
            precio_texto TEXT,
            imagen_path TEXT,
            fecha_catalogo TEXT,
            creado_en TEXT DEFAULT (datetime('now')),
            actualizado_en TEXT DEFAULT (datetime('now'))
        );
        
        CREATE INDEX IF NOT EXISTS idx_productos_sku ON productos(sku);
    """)
    db.commit()
    return db


def parsear_fecha(fecha_str: str) -> str:
    """Convierte DD/MM/YYYY a YYYY-MM-DD para comparación."""
    try:
        parts = fecha_str.split('/')
        if len(parts) == 3:
            return f"{parts[2]}-{parts[1]}-{parts[0]}"
    except:
        pass
    return fecha_str


def extraer_fecha_catalogo(pdf_path: str) -> str:
    """Extrae la fecha del catálogo (período vigente)."""
    texto = extraer_texto_pdf(pdf_path, 2)  # Página 2 tiene la fecha
    
    # Buscar patrón: Desde el DD/MM/YYYY
    match = re.search(r'Desde el (\d{2}/\d{2}/\d{4})', texto)
    if match:
        return parsear_fecha(match.group(1))
    
    return datetime.now().strftime("%Y-%m-%d")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Extractor con actualización por fecha")
    parser.add_argument("--pdf", required=True, help="Ruta al PDF del catálogo")
    parser.add_argument("--muestra", type=int, default=0, 
                        help="Número de páginas a procesar (0 = todas)")
    args = parser.parse_args()
    
    if not os.path.exists(args.pdf):
        print(f"Error: No se encontró {args.pdf}")
        return
    
    print("=" * 60)
    print("EXTRACTOR CON ACTUALIZACIÓN POR FECHA")
    print("=" * 60)
    
    # Extraer fecha del catálogo
    fecha_catalogo = extraer_fecha_catalogo(args.pdf)
    print(f"\nFecha del catálogo: {fecha_catalogo}")
    
    # Crear base de datos
    db = crear_base_datos()
    
    # Obtener total de páginas
    result = subprocess.run(["pdfinfo", args.pdf], capture_output=True, text=True)
    total_match = re.search(r'Pages:\s+(\d+)', result.stdout)
    total_paginas = int(total_match.group(1)) if total_match else 100
    
    if args.muestra > 0:
        total_paginas = min(args.muestra, total_paginas)
    
    print(f"Páginas a procesar: {total_paginas}")
    print()
    
    # Contadores
    nuevos = 0
    actualizados = 0
    sin_cambio = 0
    errores = 0
    
    # Procesar páginas
    for pagina in range(1, total_paginas + 1):
        print(f"\rProcesando página {pagina}/{total_paginas}...", end="", flush=True)
        
        # Extraer productos
        texto = extraer_texto_pdf(args.pdf, pagina)
        productos = parsear_productos(texto)
        
        # Extraer imágenes ordenadas
        try:
            imagenes = extraer_imagenes_orden(args.pdf, pagina)
        except:
            imagenes = []
        
        # Procesar cada producto
        for i, prod in enumerate(productos):
            sku = prod['sku']
            nombre = prod['nombre']
            precio = prod['precio']
            
            # Buscar en DB
            existente = db.execute(
                "SELECT id, precio_texto, fecha_catalogo FROM productos WHERE sku = ?",
                (sku,)
            ).fetchone()
            
            # Asignar imagen si existe
            imagen_path = None
            if i < len(imagenes):
                # Renombrar imagen final
                imagen_final = IMAGES_DIR / f"{sku}.jpg"
                if os.path.exists(imagenes[i]):
                    os.rename(imagenes[i], str(imagen_final))
                    imagen_path = str(imagen_final)
            
            if existente:
                # SKU existe - comparar fechas
                db_id, db_precio, db_fecha = existente
                
                if fecha_catalogo > (db_fecha or ''):
                    # Catálogo es más nuevo - actualizar precio
                    if precio and precio != db_precio:
                        db.execute(
                            "UPDATE productos SET precio_texto = ?, fecha_catalogo = ?, actualizado_en = datetime('now') WHERE id = ?",
                            (precio, fecha_catalogo, db_id)
                        )
                        actualizados += 1
                    else:
                        sin_cambio += 1
                else:
                    # Catálogo es más viejo - no tocar
                    sin_cambio += 1
            else:
                # SKU nuevo - insertar completo
                db.execute(
                    "INSERT INTO productos (sku, nombre, precio_texto, imagen_path, fecha_catalogo) VALUES (?, ?, ?, ?, ?)",
                    (sku, nombre, precio, imagen_path, fecha_catalogo)
                )
                nuevos += 1
        
        db.commit()
    
    print()  # Nueva línea después del progreso
    
    # Limpiar imágenes temporales
    for archivo in IMAGES_DIR.glob("temp_*.jpg"):
        archivo.unlink()
    
    # Resumen
    print("\n" + "=" * 60)
    print("RESUMEN")
    print("=" * 60)
    print(f"Fecha catálogo: {fecha_catalogo}")
    print(f"Páginas procesadas: {total_paginas}")
    print(f"Productos nuevos: {nuevos}")
    print(f"Productos actualizados: {actualizados}")
    print(f"Sin cambio: {sin_cambio}")
    print(f"Total en DB: {db.execute('SELECT COUNT(*) FROM productos').fetchone()[0]}")
    print("=" * 60)
    
    db.close()


if __name__ == "__main__":
    main()
