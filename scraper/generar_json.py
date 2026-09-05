#!/usr/bin/env python3
"""
Genera productos.json desde la base de datos.
Ejecutar despues de extraer un catalogo nuevo.

Uso:
  python3 generar_json.py                    # Genera para lc_2050
  python3 generar_json.py lc_2050            # Genera para un proveedor especifico
  python3 generar_json.py --all              # Genera para todos los proveedores
"""
import sys
import os
import json
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PROVEEDORES_DIR = BASE_DIR / "proveedores"
APP_DIR = BASE_DIR / "app"


def generar_json(proveedor_slug):
    db_path = PROVEEDORES_DIR / proveedor_slug / "catalogo.db"
    if not db_path.exists():
        print(f"  DB no encontrada: {db_path}")
        return False

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT sku, nombre, precio_texto FROM productos ORDER BY sku")
    productos = [dict(row) for row in c.fetchall()]
    conn.close()

    # Guardar en app/data/
    out_dir = APP_DIR / "data"
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / "productos.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(productos, f, ensure_ascii=False)

    print(f"  {proveedor_slug}: {len(productos)} productos -> {out_file}")

    # También guardar una copia en el directorio del proveedor
    prov_out = PROVEEDORES_DIR / proveedor_slug / "productos.json"
    with open(prov_out, "w", encoding="utf-8") as f:
        json.dump(productos, f, ensure_ascii=True)

    return True


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--all":
        proveedores = [d.name for d in PROVEEDORES_DIR.iterdir()
                       if d.is_dir() and (d / "catalogo.db").exists()]
        for slug in sorted(proveedores):
            generar_json(slug)
    elif len(sys.argv) > 1:
        generar_json(sys.argv[1])
    else:
        # Default: lc_2050
        generar_json("lc_2050")


if __name__ == "__main__":
    main()
