#!/usr/bin/env python3
"""
Extractor completo del catálogo LC 2050
Procesa TODAS las páginas, extrae SKUs, nombres, precios e imágenes.
"""
import fitz
import sqlite3
import re
import subprocess
import shutil
from pathlib import Path
from datetime import datetime

RAIZ = Path(__file__).resolve().parent.parent
PDF_PATH = RAIZ / "04-09 AL 10-09 CATALOGO LC 2050.pdf"
DB_PATH = RAIZ / "proveedores" / "lc_2050" / "catalogo.db"
IMG_DIR = RAIZ / "proveedores" / "lc_2050" / "images"
TEMPLATE_PATH = RAIZ / "templates" / "lc_2050.json"


def cargar_template():
    import json
    with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def extraer_texto_pagina(pdf_path, pagina):
    result = subprocess.run(
        ["pdftotext", "-layout", "-f", str(pagina), "-l", str(pagina), str(pdf_path), "-"],
        capture_output=True, text=True
    )
    return result.stdout


def parsear_productos_pagina(texto):
    """Extrae productos de una página con 2 columnas, 5 filas."""
    productos = []
    lineas = texto.split('\n')

    # Buscar SKU: 3 letras + 3-4 números al inicio de línea
    patron_sku = re.compile(r'^([A-Z]{3}\d{3,4})\b')

    # Agrupar líneas por bloques de producto
    i = 0
    while i < len(lineas):
        match = patron_sku.search(lineas[i])
        if not match:
            i += 1
            continue

        sku_izq = match.group(1)

        # Buscar SKU de la columna derecha en la misma línea
        resto = lineas[i][match.end():].strip()
        match_der = patron_sku.search(resto)
        sku_der = match_der.group(1) if match_der else None

        # Recoger líneas hasta el siguiente SKU
        bloques = {'izq': [], 'der': []}
        precios = {'izq': None, 'der': None}

        j = i + 1
        while j < len(lineas):
            if patron_sku.search(lineas[j]):
                break

            linea = lineas[j]

            # Dividir en columnas (aprox mitad)
            if len(linea) > 30:
                izq = linea[:30].strip()
                der = linea[30:].strip()
            else:
                izq = linea.strip()
                der = ""

            # Buscar precio (termina en $)
            for lado, txt in [('izq', izq), ('der', der)]:
                precio_match = re.search(r'(\d+[.,]\d+)\$', txt)
                if precio_match:
                    precios[lado] = precio_match.group(1)
                elif txt and not patron_sku.match(txt):
                    if txt.strip():
                        bloques[lado].append(txt.strip())

            j += 1

        # Construir nombres
        nombre_izq = ' '.join(bloques['izq']).strip()
        nombre_izq = re.sub(r'\s+', ' ', nombre_izq)
        nombre_izq = re.sub(r'-\s*', '', nombre_izq)  # Quitar guiones de salto

        nombre_der = ' '.join(bloques['der']).strip()
        nombre_der = re.sub(r'\s+', ' ', nombre_der)
        nombre_der = re.sub(r'-\s*', '', nombre_der)

        if sku_izq and nombre_izq:
            productos.append({
                'sku': sku_izq,
                'nombre': nombre_izq,
                'precio': precios['izq']
            })

        if sku_der and nombre_der:
            productos.append({
                'sku': sku_der,
                'nombre': nombre_der,
                'precio': precios['der']
            })

        i = j

    return productos


def extraer_imagenes_pagina(doc, pagina_idx, sku_izq, sku_der):
    """Extrae imágenes de una página y las guarda con nombre SKU."""
    page = doc[pagina_idx]
    images = page.get_images(full=True)

    items = []
    for img in images:
        xref = img[0]
        rects = page.get_image_rects(xref)
        if rects:
            rect = rects[0]
            # Filtrar imágenes muy grandes (fondos)
            if rect.width < 300 and rect.height < 300:
                items.append({
                    'xref': xref,
                    'x': rect.x0,
                    'y': rect.y0,
                    'w': rect.width,
                    'h': rect.height
                })

    # Ordenar por posición visual: primero fila (Y), luego columna (X)
    items.sort(key=lambda p: (round(p['y'] / 100), p['x']))

    rutas = {}
    for idx, item in enumerate(items):
        try:
            pix = fitz.Pixmap(doc, item['xref'])
            if pix.n - pix.alpha > 3:
                pix = fitz.Pixmap(fitz.csRGB, pix)
            elif pix.alpha:
                pix = fitz.Pixmap(pix, 0)

            # Asignar SKU según posición
            if idx == 0 and sku_izq:
                nombre = f"{sku_izq}.jpg"
            elif idx == 1 and sku_der:
                nombre = f"{sku_der}.jpg"
            elif idx == 0 and sku_izq:
                nombre = f"{sku_izq}.jpg"
            else:
                continue

            out_path = IMG_DIR / nombre
            pix.save(str(out_path))
            rutas[nombre.replace('.jpg', '')] = str(out_path)
        except Exception as e:
            pass

    return rutas


def init_db():
    """Inicializa la base de datos."""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT UNIQUE,
            nombre TEXT NOT NULL,
            descripcion TEXT,
            marca TEXT,
            categoria_id INTEGER,
            url_original TEXT,
            imagen_principal TEXT,
            precio_texto TEXT,
            creado_en TEXT DEFAULT (datetime('now')),
            fecha_catalogo TEXT,
            actualizado_en TEXT,
            imagen_path TEXT
        )
    """)
    conn.commit()
    return conn


def upsert_producto(conn, sku, nombre, precio, imagen_path, fecha_catalogo):
    """Inserta o actualiza un producto."""
    c = conn.cursor()

    # Verificar si existe
    c.execute("SELECT id, fecha_catalogo FROM productos WHERE sku = ?", (sku,))
    row = c.fetchone()

    if row:
        # Actualizar si el catálogo nuevo es igual o más reciente
        existente_fecha = row[1] or ""
        if fecha_catalogo >= existente_fecha:
            c.execute("""
                UPDATE productos
                SET nombre = ?, precio_texto = ?, imagen_path = ?,
                    fecha_catalogo = ?, actualizado_en = datetime('now')
                WHERE sku = ?
            """, (nombre, precio or '', imagen_path, fecha_catalogo, sku))
    else:
        c.execute("""
            INSERT INTO productos (sku, nombre, precio_texto, imagen_path, fecha_catalogo)
            VALUES (?, ?, ?, ?, ?)
        """, (sku, nombre, precio or '', imagen_path, fecha_catalogo))


def main():
    print("=" * 60)
    print("EXTRACCIÓN COMPLETA - LC 2050")
    print("=" * 60)
    print()

    template = cargar_template()
    print(f"Proveedor: {template['proveedor']['nombre']}")
    print(f"RIF: {template['proveedor']['rif']}")
    print(f"PDF: {PDF_PATH.name}")
    print()

    # Crear directorio de imágenes
    IMG_DIR.mkdir(parents=True, exist_ok=True)

    # Abrir PDF
    doc = fitz.open(str(PDF_PATH))
    total_paginas = len(doc)
    print(f"Total páginas: {total_paginas}")
    print()

    # Conectar DB
    conn = init_db()
    fecha_catalogo = datetime.now().strftime('%Y-%m-%d')

    total_productos = 0
    total_con_precio = 0
    total_con_imagen = 0
    productos_por_pagina = []

    for pagina_num in range(1, total_paginas + 1):
        texto = extraer_texto_pagina(PDF_PATH, pagina_num)

        if not texto.strip():
            continue

        productos = parsear_productos_pagina(texto)

        if not productos:
            continue

        # Extraer imágenes de esta página
        sku_izq = productos[0]['sku'] if len(productos) > 0 else None
        sku_der = productos[1]['sku'] if len(productos) > 1 else None
        imagenes = extraer_imagenes_pagina(doc, pagina_num - 1, sku_izq, sku_der)

        for prod in productos:
            sku = prod['sku']
            nombre = prod['nombre']
            precio = prod['precio']
            imagen_path = imagenes.get(sku)

            upsert_producto(conn, sku, nombre, precio, imagen_path, fecha_catalogo)

            total_productos += 1
            if precio:
                total_con_precio += 1
            if imagen_path:
                total_con_imagen += 1

        productos_por_pagina.append({
            'pagina': pagina_num,
            'productos': len(productos),
            'con_precio': sum(1 for p in productos if p['precio']),
            'con_imagen': sum(1 for p in productos if p['sku'] in imagenes)
        })

        if pagina_num % 20 == 0:
            conn.commit()
            print(f"  Página {pagina_num}/{total_paginas} - "
                  f"Productos: {total_productos} - "
                  f"Con precio: {total_con_precio} - "
                  f"Con imagen: {total_con_imagen}")

    conn.commit()
    doc.close()

    print()
    print("=" * 60)
    print("RESUMEN")
    print("=" * 60)
    print(f"  Páginas procesadas: {len(productos_por_pagina)}")
    print(f"  Total productos: {total_productos}")
    print(f"  Con precio: {total_con_precio}")
    print(f"  Con imagen: {total_con_imagen}")
    print()

    # Verificar imágenes
    imgs_en_carpeta = len(list(IMG_DIR.glob("*.jpg")))
    print(f"  Imágenes en carpeta: {imgs_en_carpeta}")
    print()

    conn.close()

    print("Listo. Extracción completada.")


if __name__ == "__main__":
    main()
