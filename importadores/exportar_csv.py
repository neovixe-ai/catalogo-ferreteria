#!/usr/bin/env python3
"""
Exportador de Catálogo → CSV
==============================
Exporta el catalogo.db a archivos CSV para Excel/Google Sheets.

Uso:
  python exportar_csv.py --proveedor mi_proveedor
  python exportar_csv.py --proveedor mi_proveedor --output mi_catalogo.csv
"""

import argparse
import csv
import sqlite3
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PROVEEDORES_DIR = RAIZ / "proveedores"


def exportar(proveedor: str, output: str = None):
    db_path = PROVEEDORES_DIR / proveedor / "catalogo.db"
    if not db_path.exists():
        print(f"Error: No se encontró {db_path}")
        sys.exit(1)

    db = sqlite3.connect(str(db_path))
    db.row_factory = sqlite3.Row

    out_dir = PROVEEDORES_DIR / proveedor
    if output:
        out_path = Path(output)
    else:
        out_path = out_dir / "catalogo.csv"

    # Consulta principal
    rows = db.execute("""
        SELECT
            p.sku,
            p.nombre,
            p.descripcion,
            p.marca,
            c.nombre AS categoria,
            p.precio_texto,
            p.imagen_principal,
            p.url_original
        FROM productos p
        LEFT JOIN categorias c ON p.categoria_id = c.id
        ORDER BY c.nombre, p.nombre
    """).fetchall()

    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["SKU", "Nombre", "Descripción", "Marca", "Categoría", "Precio", "Imagen", "URL"])
        for row in rows:
            writer.writerow([
                row["sku"], row["nombre"], row["descripcion"],
                row["marca"], row["categoria"], row["precio_texto"],
                row["imagen_principal"], row["url_original"],
            ])

    print(f"✓ Exportado: {out_path} ({len(rows)} productos)")
    db.close()


def main():
    parser = argparse.ArgumentParser(description="Exportar catálogo a CSV")
    parser.add_argument("--proveedor", "-p", required=True, help="Nombre del proveedor")
    parser.add_argument("--output", "-o", help="Archivo de salida (opcional)")
    args = parser.parse_args()
    exportar(args.proveedor, args.output)


if __name__ == "__main__":
    main()
