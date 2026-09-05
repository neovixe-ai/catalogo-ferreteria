#!/usr/bin/env python3
"""
App de pedidos - PWA
Abre en navegador: http://localhost:5000
"""
import os
import sys
import json
import sqlite3
import io
from datetime import datetime
from pathlib import Path

from flask import Flask, render_template, request, jsonify, send_file, send_from_directory

app = Flask(__name__)
app.secret_key = os.urandom(24)

BASE_DIR = Path(__file__).resolve().parent.parent
PROVEEDORES_DIR = BASE_DIR / "proveedores"


def get_db_path(proveedor_slug):
    db = PROVEEDORES_DIR / proveedor_slug / "catalogo.db"
    if db.exists():
        return str(db)
    return None


def get_proveedor_info(proveedor_slug):
    db_path = get_db_path(proveedor_slug)
    if not db_path:
        return None
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM productos LIMIT 1")
    row = c.fetchone()
    conn.close()
    if row:
        return {"slug": proveedor_slug, "db": db_path}
    return {"slug": proveedor_slug, "db": db_path}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/proveedores/<path:filename>")
def serve_proveedor_file(filename):
    return send_from_directory(str(PROVEEDORES_DIR), filename)


@app.route("/api/proveedores")
def api_proveedores():
    proveedores = []
    if PROVEEDORES_DIR.exists():
        for d in sorted(PROVEEDORES_DIR.iterdir()):
            if d.is_dir() and (d / "catalogo.db").exists():
                info = get_proveedor_info(d.name)
                if info:
                    conn = sqlite3.connect(info["db"])
                    c = conn.cursor()
                    c.execute("SELECT COUNT(*) FROM productos")
                    total = c.fetchone()[0]
                    c.execute("SELECT MAX(fecha_catalogo) FROM productos")
                    fecha = c.fetchone()[0]
                    conn.close()
                    proveedores.append({
                        "slug": d.name,
                        "nombre": d.name.upper().replace("_", " "),
                        "total_productos": total,
                        "ultimo_catalogo": fecha
                    })
    return jsonify(proveedores)


@app.route("/api/productos/<proveedor>")
def api_productos(proveedor):
    db_path = get_db_path(proveedor)
    if not db_path:
        return jsonify({"error": "Proveedor no encontrado"}), 404

    search = request.args.get("q", "").strip()
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 50))

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    query = "SELECT * FROM productos WHERE 1=1"
    params = []

    if search:
        query += " AND (sku LIKE ? OR nombre LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])

    query += " ORDER BY sku"
    query += " LIMIT ? OFFSET ?"
    params.extend([per_page, (page - 1) * per_page])

    c.execute(query, params)
    productos = [dict(row) for row in c.fetchall()]

    c.execute("SELECT COUNT(*) FROM productos" + (" WHERE sku LIKE ? OR nombre LIKE ?" if search else ""),
              [f"%{search}%", f"%{search}%"] if search else [])
    total = c.fetchone()[0]

    img_dir = PROVEEDORES_DIR / proveedor / "images"
    for p in productos:
        sku = p["sku"]
        if sku:
            img_path = img_dir / f"{sku}.jpg"
            if img_path.exists():
                p["imagen_url"] = f"/proveedores/{proveedor}/images/{sku}.jpg"
            else:
                p["imagen_url"] = None
        else:
            p["imagen_url"] = None

    conn.close()
    return jsonify({"productos": productos, "total": total, "page": page, "per_page": per_page})


@app.route("/api/pedido/pdf", methods=["POST"])
def api_pedido_pdf():
    data = request.json
    proveedor = data.get("proveedor", "")
    items = data.get("items", [])
    cliente = data.get("cliente", "")
    notas = data.get("notas", "")

    if not items:
        return jsonify({"error": "Pedido vacío"}), 400

    db_path = get_db_path(proveedor)
    if not db_path:
        return jsonify({"error": "Proveedor no encontrado"}), 404

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    skus = [item["sku"] for item in items]
    placeholders = ",".join(["?" for _ in skus])
    c.execute(f"SELECT sku, nombre, precio_texto, imagen_path FROM productos WHERE sku IN ({placeholders})", skus)
    productos_db = {row["sku"]: dict(row) for row in c.fetchall()}
    conn.close()

    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            leftMargin=15*mm, rightMargin=15*mm,
                            topMargin=20*mm, bottomMargin=20*mm)

    styles = getSampleStyleSheet()
    elements = []

    title_style = ParagraphStyle('CustomTitle', parent=styles['Title'], fontSize=16, spaceAfter=5*mm)
    subtitle_style = ParagraphStyle('Subtitle', parent=styles['Normal'], fontSize=10, textColor=colors.grey, spaceAfter=3*mm)
    normal_style = ParagraphStyle('CustomNormal', parent=styles['Normal'], fontSize=9)

    elements.append(Paragraph(f"Pedido - {proveedor.upper().replace('_', ' ')}", title_style))
    elements.append(Paragraph(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}", subtitle_style))
    if cliente:
        elements.append(Paragraph(f"Cliente: {cliente}", subtitle_style))
    elements.append(Spacer(1, 5*mm))

    header = ["SKU", "Producto", "Cant.", "Precio", "Subtotal"]
    table_data = [header]

    total_general = 0
    for item in items:
        sku = item["sku"]
        cant = int(item.get("cantidad", 1))
        prod = productos_db.get(sku, {})
        nombre = prod.get("nombre", sku)
        if len(nombre) > 35:
            nombre = nombre[:32] + "..."
        precio_str = prod.get("precio_texto", "")
        try:
            precio = float(precio_str.replace(",", "."))
        except (ValueError, AttributeError):
            precio = 0
        subtotal = precio * cant
        total_general += subtotal

        if precio > 0:
            precio_fmt = f"{precio:,.2f}"
            subtotal_fmt = f"{subtotal:,.2f}"
        else:
            precio_fmt = "-"
            subtotal_fmt = "-"

        table_data.append([sku, Paragraph(nombre, normal_style), str(cant), precio_fmt, subtotal_fmt])

    table_data.append(["", "", "", "TOTAL:", f"{total_general:,.2f}"])

    col_widths = [55, 200, 40, 60, 70]
    table = Table(table_data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -2), colors.HexColor("#ecf0f1")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor("#f8f9fa")]),
        ('ALIGN', (2, 1), (2, -1), 'CENTER'),
        ('ALIGN', (3, 1), (4, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#bdc3c7")),
        ('LINEBELOW', (0, -2), (-1, -2), 1, colors.HexColor("#2c3e50")),
        ('FONTSIZE', (-2, -1), (-1, -1), 10),
        ('TEXTCOLOR', (-2, -1), (-1, -1), colors.HexColor("#2c3e50")),
    ]))
    elements.append(table)

    if notas:
        elements.append(Spacer(1, 8*mm))
        elements.append(Paragraph(f"<b>Notas:</b> {notas}", normal_style))

    doc.build(elements)
    buffer.seek(0)

    filename = f"pedido_{proveedor}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    return send_file(buffer, mimetype="application/pdf", as_attachment=True, download_name=filename)


@app.route("/manifest.json")
def manifest():
    return send_from_directory("static", "manifest.json")


@app.route("/sw.js")
def service_worker():
    return send_from_directory("static", "sw.js")


@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory("static", filename)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    print(f"\n  App de pedidos iniciada!")
    print(f"  Abre en navegador: http://localhost:{port}")
    print(f"  Presiona Ctrl+C para detener\n")
    app.run(host="0.0.0.0", port=port, debug=False)
