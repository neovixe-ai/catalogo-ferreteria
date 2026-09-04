#!/usr/bin/env python3
"""
Extractor de Catálogo PDF
=========================
Analiza un PDF de catálogo de ferretería, extrae productos y los guarda en SQLite.
Detecta automáticamente el nombre del proveedor y el período del catálogo.

Uso:
  python extraccion_pdf.py --archivo "catalogo.pdf"
  python extraccion_pdf.py --archivo "catalogo.pdf" --muestra  # Solo muestra primeras páginas
"""

import argparse
import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path
from datetime import datetime


RAIZ = Path(__file__).resolve().parent.parent
PROVEEDORES_DIR = RAIZ / "proveedores"


def extraer_texto_pdf(pdf_path: str, pagina_inicio: int = None, pagina_fin: int = None) -> str:
    """Extrae texto del PDF usando pdftotext con layout."""
    cmd = ["pdftotext", "-layout"]
    if pagina_inicio:
        cmd.extend(["-f", str(pagina_inicio)])
    if pagina_fin:
        cmd.extend(["-l", str(pagina_fin)])
    cmd.extend([pdf_path, "-"])
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error ejecutando pdftotext: {result.stderr}")
        sys.exit(1)
    return result.stdout


def detectar_proveedor(texto: str, archivo_path: str) -> str:
    """Detecta el nombre del proveedor del PDF o del nombre de archivo."""
    # Primero intentar del nombre de archivo
    nombre_archivo = Path(archivo_path).stem.upper()
    
    # Buscar patrones en el nombre de archivo
    patrones_archivo = [
        r'LC\s*(\d{2,})',  # LC 2050, LC2024, etc.
        r'([A-Z]{2,})\s*\d{2,}',  # ABC 123, XYZ 456, etc.
    ]
    
    for patron in patrones_archivo:
        match = re.search(patron, nombre_archivo)
        if match:
            if match.lastindex:
                proveedor = match.group(0).strip()
            else:
                proveedor = match.group(1).strip()
            
            # Limpiar y normalizar
            proveedor = re.sub(r'\s+', '_', proveedor)
            proveedor = proveedor.lower()
            proveedor = re.sub(r'[^a-z0-9_]', '', proveedor)
            return proveedor
    
    # Si no se encuentra en el nombre, buscar en el contenido
    patrones_contenido = [
        r'CATALOGO\s+([A-Z0-9\s]+?)(?:\s+\d{2})',
        r'PROVEEDOR[:\s]+([A-Z0-9\s]+)',
        r'DISTRIBUIDORA[:\s]+([A-Z0-9\s]+)',
    ]
    
    for patron in patrones_contenido:
        match = re.search(patron, texto, re.IGNORECASE)
        if match:
            proveedor = match.group(1).strip()
            proveedor = re.sub(r'\s+', '_', proveedor)
            proveedor = proveedor.lower()
            proveedor = re.sub(r'[^a-z0-9_]', '', proveedor)
            
            # Evitar nombres genéricos
            if proveedor not in ['el', 'la', 'los', 'las', 'de', 'del', 'general', 'catalogo']:
                return proveedor
    
    return "ferreteria"


def detectar_periodo(texto: str) -> str:
    """Detecta el período del catálogo (fechas)."""
    # Buscar patrones de fechas
    patrones = [
        r'(?:DESDE|VIGENTE\s+DESDE)\s+(\d{2}[-/]\d{2}[-/]\d{4})\s+(?:HASTA|AL)\s+(\d{2}[-/]\d{2}[-/]\d{4})',
        r'(\d{2}[-/]\d{2})\s+(?:AL|-)\s+(\d{2}[-/]\d{2})',
        r'(\d{1,2}[-/]\d{1,2})\s+(?:AL|-)\s+(\d{1,2}[-/]\d{1,2})',
    ]
    
    for patron in patrones:
        match = re.search(patron, texto, re.IGNORECASE)
        if match:
            fecha_inicio = match.group(1)
            fecha_fin = match.group(2)
            # Formatear para nombre de archivo
            periodo = f"{fecha_inicio.replace('/', '-')}_al_{fecha_fin.replace('/', '-')}"
            return periodo
    
    # Si no detecta fechas, usar fecha actual
    return datetime.now().strftime("%d-%m-%Y")


def parsear_productos(texto: str) -> list:
    """Parsea el texto del PDF y extrae productos de las 2 columnas."""
    productos = []
    
    # Patrón para detectar SKU al inicio de línea
    patron_sku = re.compile(r'^([A-Z]{2,}\d{2,})\s{2,}([A-Z]{2,}\d{2,})', re.MULTILINE)
    
    # Encontrar todas las líneas con SKUs
    lineas = texto.split('\n')
    
    i = 0
    while i < len(lineas):
        linea = lineas[i].strip()
        
        # Buscar línea con 2 SKUs (columna izquierda y derecha)
        match = patron_sku.search(linea)
        if match:
            sku1 = match.group(1)
            sku2 = match.group(2)
            
            # Determinar posición de cada SKU en la línea
            pos_sku1 = linea.find(sku1)
            pos_sku2 = linea.find(sku2)
            
            # Recopilar líneas siguientes para nombres y precios
            nombre1_parts = []
            nombre2_parts = []
            precio1 = ""
            precio2 = ""
            
            j = i + 1
            while j < len(lineas) and j < i + 8:  # Máximo 8 líneas por producto
                linea_actual = lineas[j].strip()
                
                if not linea_actual:
                    j += 1
                    continue
                
                # Detectar precios (número + $)
                precio_match = re.search(r'(\d+[.,]\d+)\s*\$', linea_actual)
                if precio_match:
                    precio = precio_match.group(1)
                    # Determinar si es precio izquierdo o derecho
                    pos_precio = linea_actual.find(precio_match.group(0))
                    if pos_precio < len(linea_actual) // 2:
                        precio1 = precio
                    else:
                        precio2 = precio
                else:
                    # Es parte del nombre - determinar columna
                    # Usar la posición relativa al centro de la línea
                    pos_texto = linea_actual.find(linea_actual.strip()) if linea_actual.strip() else 0
                    
                    # Analizar contenido de la línea
                    # Si la línea tiene contenido en la mitad derecha, es columna derecha
                    mitad = len(linea_actual) // 2
                    
                    # Buscar texto en cada mitad
                    izq_texto = linea_actual[:mitad].strip()
                    der_texto = linea_actual[mitad:].strip()
                    
                    if izq_texto and not re.match(r'^[A-Z]{2,}\d{2,}', izq_texto):
                        nombre1_parts.append(izq_texto)
                    if der_texto and not re.match(r'^[A-Z]{2,}\d{2,}', der_texto):
                        nombre2_parts.append(der_texto)
                
                # Si encontramos el siguiente SKU, parar
                if j > i + 1 and re.match(r'^[A-Z]{2,}\d{2,}', linea_actual):
                    break
                
                j += 1
            
            # Construir nombres completos
            nombre1 = ' '.join(nombre1_parts)
            nombre2 = ' '.join(nombre2_parts)
            
            # Limpiar nombres (unir palabras partidas por guiones)
            nombre1 = re.sub(r'-\s+', '', nombre1)
            nombre2 = re.sub(r'-\s+', '', nombre2)
            nombre1 = re.sub(r'\s+', ' ', nombre1).strip()
            nombre2 = re.sub(r'\s+', ' ', nombre2).strip()
            
            # Agregar productos si tienen datos válidos
            if sku1 and nombre1 and len(nombre1) > 3:
                productos.append({
                    'sku': sku1,
                    'nombre': nombre1,
                    'precio_texto': f"{precio1}$" if precio1 else ""
                })
            
            if sku2 and nombre2 and len(nombre2) > 3:
                productos.append({
                    'sku': sku2,
                    'nombre': nombre2,
                    'precio_texto': f"{precio2}$" if precio2 else ""
                })
            
            i = j
        else:
            i += 1
    
    return productos


def extraer_imagenes_pdf(pdf_path: str, output_dir: str, pagina_inicio: int = None, pagina_fin: int = None):
    """Extrae imágenes del PDF usando pdfimages."""
    os.makedirs(output_dir, exist_ok=True)
    
    cmd = ["pdfimages", "-j"]  # -j para JPEG
    if pagina_inicio:
        cmd.extend(["-f", str(pagina_inicio)])
    if pagina_fin:
        cmd.extend(["-l", str(pagina_fin)])
    
    cmd.extend([pdf_path, os.path.join(output_dir, "img")])
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Advertencia: pdfimages falló: {result.stderr}")
        return []
    
    # Listar imágenes extraídas
    imagenes = []
    for archivo in os.listdir(output_dir):
        if archivo.startswith("img.") or archivo.startswith("img-"):
            imagenes.append(os.path.join(output_dir, archivo))
    
    return imagenes


def crear_base_datos(db_path: str):
    """Crea la base de datos SQLite con el esquema estándar."""
    db = sqlite3.connect(db_path)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA foreign_keys=ON")
    
    db.executescript("""
        CREATE TABLE IF NOT EXISTS categorias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            slug TEXT UNIQUE NOT NULL,
            parent_id INTEGER REFERENCES categorias(id),
            total_productos INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT UNIQUE,
            nombre TEXT NOT NULL,
            descripcion TEXT,
            marca TEXT,
            categoria_id INTEGER REFERENCES categorias(id),
            url_original TEXT,
            imagen_principal TEXT,
            precio_texto TEXT,
            creado_en TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS producto_meta (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_id INTEGER REFERENCES productos(id) ON DELETE CASCADE,
            clave TEXT NOT NULL,
            valor TEXT,
            UNIQUE(producto_id, clave)
        );

        CREATE TABLE IF NOT EXISTS imagenes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_id INTEGER REFERENCES productos(id) ON DELETE CASCADE,
            url_original TEXT,
            local_path TEXT,
            es_principal INTEGER DEFAULT 0
        );

        CREATE INDEX IF NOT EXISTS idx_productos_sku ON productos(sku);
        CREATE INDEX IF NOT EXISTS idx_productos_categoria ON productos(categoria_id);
        CREATE INDEX IF NOT EXISTS idx_productos_nombre ON productos(nombre);
        CREATE INDEX IF NOT EXISTS idx_producto_meta_clave ON producto_meta(clave);
    """)
    db.commit()
    return db


def guardar_producto(db: sqlite3.Connection, producto: dict) -> int:
    """Guarda un producto en la base de datos."""
    existing = None
    if producto.get('sku'):
        existing = db.execute(
            "SELECT id FROM productos WHERE sku = ?", (producto['sku'],)
        ).fetchone()
    
    if existing:
        db.execute("""
            UPDATE productos
            SET nombre = ?, precio_texto = ?
            WHERE id = ?
        """, (producto['nombre'], producto.get('precio_texto'), existing[0]))
        db.commit()
        return existing[0]
    else:
        cur = db.execute("""
            INSERT INTO productos (sku, nombre, precio_texto)
            VALUES (?, ?, ?)
        """, (producto.get('sku'), producto['nombre'], producto.get('precio_texto')))
        db.commit()
        return cur.lastrowid


def main():
    parser = argparse.ArgumentParser(description="Extractor de catálogos PDF")
    parser.add_argument("--archivo", "-a", required=True, help="Ruta al archivo PDF")
    parser.add_argument("--muestra", "-m", action="store_true", help="Modo muestra: solo analiza las primeras páginas")
    parser.add_argument("--paginas", "-p", type=int, default=10, help="Número de páginas a procesar en modo muestra (default: 10)")
    args = parser.parse_args()
    
    if not os.path.exists(args.archivo):
        print(f"Error: No se encontró el archivo {args.archivo}")
        sys.exit(1)
    
    print(f"\n{'='*60}")
    print("EXTRACTOR DE CATÁLOGO PDF")
    print(f"{'='*60}")
    print(f"Archivo: {args.archivo}")
    
    # Determinar páginas a procesar
    if args.muestra:
        paginas_a_procesar = args.paginas
        print(f"Modo MUESTRA: Analizando primeras {paginas_a_procesar} páginas")
    else:
        # Obtener total de páginas
        result = subprocess.run(["pdfinfo", args.archivo], capture_output=True, text=True)
        total_match = re.search(r'Pages:\s+(\d+)', result.stdout)
        paginas_a_procesar = int(total_match.group(1)) if total_match else 100
        print(f"Modo COMPLETO: {paginas_a_procesar} páginas")
    
    # Extraer texto de las primeras páginas para detectar metadatos
    print("\n1. Analizando estructura del PDF...")
    texto_muestra = extraer_texto_pdf(args.archivo, 1, min(5, paginas_a_procesar))
    
    # Detectar proveedor
    proveedor = detectar_proveedor(texto_muestra, args.archivo)
    print(f"   Proveedor detectado: {proveedor}")
    
    # Detectar período
    periodo = detectar_periodo(texto_muestra)
    print(f"   Período detectado: {periodo}")
    
    # Nombre del catálogo
    nombre_catalogo = f"catalogo_{periodo}"
    print(f"   Nombre del catálogo: {nombre_catalogo}")
    
    # Confirmar con el usuario
    print(f"\n2. Información detectada:")
    print(f"   - Proveedor: {proveedor}")
    print(f"   - Catálogo: {nombre_catalogo}")
    print(f"   - Período: {periodo}")
    
    respuesta = input("\n¿Continuar con la extracción? (s/n): ").strip().lower()
    if respuesta != 's':
        print("Extracción cancelada.")
        sys.exit(0)
    
    # Crear directorio del proveedor
    dir_proveedor = PROVEEDORES_DIR / proveedor
    dir_proveedor.mkdir(parents=True, exist_ok=True)
    dir_images = dir_proveedor / "images"
    dir_images.mkdir(exist_ok=True)
    
    # Crear base de datos
    db_path = dir_proveedor / "catalogo.db"
    db = crear_base_datos(db_path)
    
    # Procesar páginas
    print(f"\n3. Procesando {paginas_a_procesar} páginas...")
    productos_total = []
    
    for pagina in range(1, paginas_a_procesar + 1):
        print(f"   Página {pagina}/{paginas_a_procesar}...", end="\r")
        texto_pagina = extraer_texto_pdf(args.archivo, pagina, pagina)
        productos_pagina = parsear_productos(texto_pagina)
        productos_total.extend(productos_pagina)
    
    print(f"\n   Total de productos encontrados: {len(productos_total)}")
    
    # Guardar productos en la base de datos
    print("\n4. Guardando productos en base de datos...")
    for i, producto in enumerate(productos_total, 1):
        guardar_producto(db, producto)
        if i % 10 == 0:
            print(f"   Guardados {i}/{len(productos_total)}...", end="\r")
    
    print(f"\n   Productos guardados: {len(productos_total)}")
    
    # Extraer imágenes si no es modo muestra
    if not args.muestra:
        print("\n5. Extrayendo imágenes...")
        imagenes = extraer_imagenes_pdf(args.archivo, str(dir_images), 1, paginas_a_procesar)
        print(f"   Imágenes extraídas: {len(imagenes)}")
    else:
        print("\n5. Imágenes: omitidas en modo muestra")
    
    # Resumen final
    print(f"\n{'='*60}")
    print("EXTRACCIÓN COMPLETADA")
    print(f"{'='*60}")
    print(f"Proveedor: {proveedor}")
    print(f"Catálogo: {nombre_catalogo}")
    print(f"Período: {periodo}")
    print(f"Productos extraídos: {len(productos_total)}")
    print(f"Base de datos: {db_path}")
    print(f"Imágenes: {dir_images if not args.muestra else ' omitidas en modo muestra'}")
    print(f"{'='*60}")
    
    db.close()


if __name__ == "__main__":
    main()
