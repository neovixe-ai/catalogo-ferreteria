#!/usr/bin/env python3
"""
Extractor de imágenes con posiciones usando PyMuPDF
Ordena por posición visual (fila, columna)
"""
import fitz
import json
import re
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PDF_PATH = RAIZ / "04-09 AL 10-09 CATALOGO LC 2050.pdf"
TEMPLATE_PATH = RAIZ / "templates" / "lc_2050.json"


def cargar_template():
    with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def extraer_texto(pagina: int) -> str:
    result = subprocess.run(
        ["pdftotext", "-layout", "-f", str(pagina), "-l", str(pagina), str(PDF_PATH), "-"],
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
                    izq, der = linea.strip(), ""
                
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
                productos.append({"sku": sku1, "nombre": nombre1, "precio": precio1})
            if sku2 and nombre2:
                productos.append({"sku": sku2, "nombre": nombre2, "precio": precio2})
            
            i = j
        else:
            i += 1
    
    return productos


def extraer_imagenes_orden(doc, pagina_idx: int) -> list:
    """Extrae imágenes ordenadas por posición visual."""
    page = doc[pagina_idx]
    images = page.get_images(full=True)
    
    # Obtener posiciones
    items = []
    for img in images:
        xref = img[0]
        rects = page.get_image_rects(xref)
        if rects:
            rect = rects[0]
            # Filtrar fondos (>200px)
            if rect.width < 200 and rect.height < 200:
                items.append({
                    'xref': xref,
                    'x': rect.x0,
                    'y': rect.y0,
                    'w': rect.width,
                    'h': rect.height
                })
    
    # Ordenar: fila (Y/100), columna (X)
    items.sort(key=lambda p: (p['y'] // 100, p['x']))
    
    return items


def extraer_imagenes(doc, pagina_idx: int, output_dir: Path, items: list) -> list:
    """Guarda imágenes en orden."""
    page = doc[pagina_idx]
    rutas = []
    
    for i, item in enumerate(items):
        pix = fitz.Pixmap(doc, item['xref'])
        if pix.n - pix.alpha > 3:
            pix = fitz.Pixmap(fitz.csRGB, pix)
        elif pix.alpha:
            pix = fitz.Pixmap(pix, 0)
        
        out_path = output_dir / f"img_{i:02d}.jpg"
        pix.save(str(out_path))
        rutas.append(str(out_path))
    
    return rutas


def main():
    template = cargar_template()
    print(f"Template: {template['proveedor']['nombre']}")
    print()
    
    doc = fitz.open(str(PDF_PATH))
    
    # Probar con 5 páginas
    paginas_prueba = [3, 31, 76, 141, 165]
    todos_productos = []
    
    for pagina in paginas_prueba:
        print(f"=== Página {pagina} ===")
        
        # Extraer productos del texto
        texto = extraer_texto(pagina)
        productos = parsear_productos(texto)
        
        # Extraer imágenes ordenadas
        output_dir = Path(f"/data/data/com.termux/files/home/catalogo-ferreteria/temp_images_p{pagina}")
        output_dir.mkdir(exist_ok=True)
        
        items = extraer_imagenes_orden(doc, pagina - 1)
        rutas = extraer_imagenes(doc, pagina - 1, output_dir, items)
        
        # Vincular imágenes a productos
        for i, prod in enumerate(productos):
            if i < len(rutas):
                prod['imagen'] = rutas[i]
            else:
                prod['imagen'] = None
            todos_productos.append(prod)
            precio = f"${prod['precio']}" if prod['precio'] else "Sin precio"
            img = Path(prod['imagen']).name if prod['imagen'] else "Sin imagen"
            print(f"  {prod['sku']:8} | {prod['nombre'][:40]:40} | {precio:8} | {img}")
        
        print()
    
    doc.close()
    
    # Guardar resultado
    resultado = {
        "template": "lc_2050",
        "paginas_analizadas": paginas_prueba,
        "total_productos": len(todos_productos),
        "productos": todos_productos
    }
    
    output_file = RAIZ / "test_extraction_ordered.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(resultado, f, indent=2, ensure_ascii=False)
    
    print(f"Total: {len(todos_productos)} productos con imágenes")
    print(f"Guardado: {output_file}")


if __name__ == "__main__":
    main()
