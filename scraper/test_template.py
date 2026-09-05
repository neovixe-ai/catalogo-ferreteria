#!/usr/bin/env python3
"""
Extractor basado en template - Prueba v3 (split por posición fija)
"""
import json
import re
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = RAIZ / "templates" / "lc_2050.json"
PDF_PATH = RAIZ / "04-09 AL 10-09 CATALOGO LC 2050.pdf"
COL_SPLIT = 30  # Posición donde se divide columnas


def cargar_template(path: str) -> dict:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def extraer_texto(pdf_path: str, pagina: int) -> str:
    result = subprocess.run(
        ["pdftotext", "-layout", "-f", str(pagina), "-l", str(pagina), pdf_path, "-"],
        capture_output=True, text=True
    )
    return result.stdout


def parsear_pagina(texto: str) -> list:
    productos = []
    lineas = texto.split('\n')
    
    # Encontrar líneas con SKUs
    patron_sku = re.compile(r'^([A-Z]{3}\d{3})\s+([A-Z]{3}\d{3})')
    
    i = 0
    while i < len(lineas):
        match = patron_sku.search(lineas[i])
        if match:
            sku1 = match.group(1)
            sku2 = match.group(2)
            
            # Recopilar bloque hasta siguiente SKU
            bloques_izq = []
            bloques_der = []
            precios = []
            
            j = i + 1
            while j < len(lineas):
                linea = lineas[j]
                
                # Si encontramos otro SKU, parar
                if patron_sku.search(linea):
                    break
                
                # Dividir línea en columnas
                if len(linea) > COL_SPLIT:
                    izq = linea[:COL_SPLIT].strip()
                    der = linea[COL_SPLIT:].strip()
                else:
                    izq = linea.strip()
                    der = ""
                
                # Detectar precios
                precio_izq = re.search(r'(\d+[.,]\d+)\$', izq)
                precio_der = re.search(r'(\d+[.,]\d+)\$', der)
                
                if precio_izq:
                    precios.append(('izq', precio_izq.group(1)))
                if precio_der:
                    precios.append(('der', precio_der.group(1)))
                
                # Acumular nombre (ignorar líneas vacías y precios)
                if izq and not re.match(r'^[A-Z]{3}\d{3}', izq) and not precio_izq:
                    bloques_izq.append(izq)
                if der and not re.match(r'^[A-Z]{3}\d{3}', der) and not precio_der:
                    bloques_der.append(der)
                
                j += 1
            
            # Construir nombres
            nombre1 = construir_nombre(bloques_izq)
            nombre2 = construir_nombre(bloques_der)
            
            # Obtener precios
            precio1 = next((p for lado, p in precios if lado == 'izq'), None)
            precio2 = next((p for lado, p in precios if lado == 'der'), None)
            
            if sku1 and nombre1:
                productos.append({
                    "sku": sku1,
                    "nombre": nombre1,
                    "precio": precio1.replace(',', '.') if precio1 else None
                })
            
            if sku2 and nombre2:
                productos.append({
                    "sku": sku2,
                    "nombre": nombre2,
                    "precio": precio2.replace(',', '.') if precio2 else None
                })
            
            i = j
        else:
            i += 1
    
    return productos


def construir_nombre(partes: list) -> str:
    """Construye nombre limpio desde líneas parciales."""
    # Unir y quitar guiones de partición
    nombre = ' '.join(partes)
    nombre = re.sub(r'-\s+', '', nombre)
    nombre = re.sub(r'\s+', ' ', nombre).strip()
    return nombre


def main():
    template = cargar_template(TEMPLATE_PATH)
    print(f"Template: {template['proveedor']['nombre']}\n")
    
    paginas_prueba = [3, 31, 76, 141, 165]
    todos_productos = []
    
    for pagina in paginas_prueba:
        print(f"--- Página {pagina} ---")
        texto = extraer_texto(str(PDF_PATH), pagina)
        productos = parsear_pagina(texto)
        
        for p in productos:
            precio_fmt = f"${p['precio']}" if p['precio'] else "Sin precio"
            print(f"  {p['sku']:8} | {p['nombre'][:45]:45} | {precio_fmt}")
        
        print(f"  Total: {len(productos)} productos\n")
        todos_productos.extend(productos)
    
    # Guardar
    resultado = {
        "template": "lc_2050",
        "paginas_analizadas": paginas_prueba,
        "total_productos": len(todos_productos),
        "productos": todos_productos
    }
    
    output_path = RAIZ / "test_extraction.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(resultado, f, indent=2, ensure_ascii=False)
    
    print(f"Guardado: {output_path}")


if __name__ == "__main__":
    main()
