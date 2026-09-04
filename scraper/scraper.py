#!/usr/bin/env python3
"""
Scraper Genérico de Catálogos de Ferretería
============================================
Reutilizable para cualquier proveedor. Lee la configuración desde
proveedores/{nombre}/config.json y genera:
  - proveedores/{nombre}/catalogo.db (SQLite)
  - proveedores/{nombre}/images/ (imágenes descargadas)

Uso:
  python scraper.py --proveedor mi_proveedor
  python scraper.py --proveedor mi_proveedor --piloto
  python scraper.py --proveedor mi_proveedor --solo-imagenes
"""

import argparse
import hashlib
import json
import logging
import os
import re
import sqlite3
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# ─── Constantes ───────────────────────────────────────────────────────
RAIZ = Path(__file__).resolve().parent.parent
PROVEEDORES_DIR = RAIZ / "proveedores"


# ─── Utilidades ───────────────────────────────────────────────────────
def slugificar(texto: str) -> str:
    """Convierte texto a slug válido para URLs y filenames."""
    texto = texto.lower().strip()
    texto = re.sub(r"[^\w\s-]", "", texto)
    texto = re.sub(r"[\s_]+", "-", texto)
    texto = re.sub(r"-+", "-", texto)
    return texto.strip("-")


def setup_logging(log_dir: Path) -> logging.Logger:
    """Configura logging a archivo y consola."""
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("scraper")
    logger.setLevel(logging.DEBUG)

    fh = logging.FileHandler(log_dir / "scraper.log", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("%(message)s"))

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


# ─── Clase Base del Scraper ──────────────────────────────────────────
class ScraperBase:
    """Scraper genérico para tiendas WooCommerce."""

    def __init__(self, proveedor: str, piloto: bool = False):
        self.proveedor = proveedor
        self.dir_proveedor = PROVEEDORES_DIR / proveedor
        self.dir_images = self.dir_proveedor / "images"
        self.dir_logs = self.dir_proveedor / "logs"
        self.config_path = self.dir_proveedor / "config.json"

        if not self.config_path.exists():
            print(f"Error: No se encontró {self.config_path}")
            sys.exit(1)

        with open(self.config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)

        self.base_url = self.config["base_url"].rstrip("/")
        self.rate_limit = self.config.get("rate_limit_segundos", 1.0)
        self.max_retries = self.config.get("max_retries", 3)
        self.timeout = self.config.get("timeout_request", 15)
        self.user_agent = self.config.get("user_agent", "CatalogoScraper/1.0")
        self.descargar_imgs = self.config.get("descargar_imagenes", True)
        self.workers_imgs = self.config.get("workers_imagenes", 3)

        self.piloto = piloto or self.config.get("piloto", {}).get("activo", False)
        self.piloto_categoria = self.config.get("piloto", {}).get("categoria_slug", "")
        self.piloto_max = self.config.get("piloto", {}).get("max_productos", 20)

        self.dir_images.mkdir(parents=True, exist_ok=True)
        self.dir_logs.mkdir(parents=True, exist_ok=True)
        self.logger = setup_logging(self.dir_logs)

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "es-VE,es;q=0.9,en;q=0.8",
        })

        self._ultimo_request = 0.0
        self.db = None

    def _throttle(self):
        """Rate limiting: espera entre requests."""
        elapsed = time.time() - self._ultimo_request
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)
        self._ultimo_request = time.time()

    def _get(self, url: str) -> requests.Response | None:
        """GET con reintentos y rate limiting."""
        self._throttle()
        for intento in range(1, self.max_retries + 1):
            try:
                resp = self.session.get(url, timeout=self.timeout)
                if resp.status_code == 200:
                    return resp
                if resp.status_code == 429:
                    espera = int(resp.headers.get("Retry-After", 5))
                    self.logger.warning(f"  429 Too Many Requests. Esperando {espera}s...")
                    time.sleep(espera)
                    continue
                if resp.status_code >= 500:
                    self.logger.warning(f"  Error {resp.status_code} en {url} (intento {intento})")
                    time.sleep(2 ** intento)
                    continue
                self.logger.debug(f"  HTTP {resp.status_code} para {url}")
                return None
            except requests.RequestException as e:
                self.logger.warning(f"  Error de conexión: {e} (intento {intento})")
                time.sleep(2 ** intento)
        return None

    # ─── Base de Datos ───────────────────────────────────────────────
    def init_db(self):
        """Inicializa la base de datos SQLite del catálogo."""
        db_path = self.dir_proveedor / "catalogo.db"
        self.db = sqlite3.connect(str(db_path))
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA foreign_keys=ON")

        self.db.executescript("""
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
        self.db.commit()

    def guardar_categoria(self, nombre: str, parent_id: int = None) -> int:
        """Inserta o retorna ID de categoría existente."""
        slug = slugificar(nombre)
        row = self.db.execute(
            "SELECT id FROM categorias WHERE slug = ?", (slug,)
        ).fetchone()
        if row:
            return row[0]
        cur = self.db.execute(
            "INSERT INTO categorias (nombre, slug, parent_id) VALUES (?, ?, ?)",
            (nombre, slug, parent_id),
        )
        self.db.commit()
        return cur.lastrowid

    def guardar_producto(self, producto: dict) -> int:
        """Inserta un producto y retorna su ID. Actualiza si el SKU ya existe."""
        existing = None
        if producto.get("sku"):
            existing = self.db.execute(
                "SELECT id FROM productos WHERE sku = ?", (producto["sku"],)
            ).fetchone()

        if existing:
            self.db.execute("""
                UPDATE productos
                SET nombre = ?, descripcion = ?, marca = ?, categoria_id = ?,
                    url_original = ?, imagen_principal = ?, precio_texto = ?
                WHERE id = ?
            """, (
                producto["nombre"], producto.get("descripcion"),
                producto.get("marca"), producto.get("categoria_id"),
                producto.get("url_original"), producto.get("imagen_principal"),
                producto.get("precio_texto"), existing[0],
            ))
            self.db.commit()
            return existing[0]
        else:
            cur = self.db.execute("""
                INSERT INTO productos
                (sku, nombre, descripcion, marca, categoria_id, url_original,
                 imagen_principal, precio_texto)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                producto.get("sku"), producto["nombre"],
                producto.get("descripcion"), producto.get("marca"),
                producto.get("categoria_id"), producto.get("url_original"),
                producto.get("imagen_principal"), producto.get("precio_texto"),
            ))
            self.db.commit()
            return cur.lastrowid

    def guardar_meta(self, producto_id: int, clave: str, valor: str):
        """Inserta o actualiza metadata de un producto."""
        self.db.execute("""
            INSERT INTO producto_meta (producto_id, clave, valor)
            VALUES (?, ?, ?)
            ON CONFLICT(producto_id, clave) DO UPDATE SET valor = excluded.valor
        """, (producto_id, clave, valor))
        self.db.commit()

    def guardar_imagen(self, producto_id: int, url: str, local_path: str, es_principal: bool = False):
        """Registra una imagen en la base de datos."""
        self.db.execute("""
            INSERT INTO imagenes (producto_id, url_original, local_path, es_principal)
            VALUES (?, ?, ?, ?)
        """, (producto_id, url, local_path, 1 if es_principal else 0))
        self.db.commit()

    def actualizar_contador_categoria(self):
        """Actualiza el conteo de productos por categoría."""
        self.db.execute("""
            UPDATE categorias SET total_productos = (
                SELECT COUNT(*) FROM productos WHERE productos.categoria_id = categorias.id
            )
        """)
        self.db.commit()

    # ─── Descarga de Imágenes ────────────────────────────────────────
    def descargar_imagen(self, url: str, sku: str, sufijo: str = "") -> str | None:
        """Descarga una imagen y la guarda localmente. Retorna la ruta relativa."""
        if not url or not self.descargar_imgs:
            return None
        # Filtrar data URIs y SVGs
        if url.startswith("data:"):
            return None

        ext = self.config.get("formato_imagen", "jpg")
        nombre_archivo = f"{sku}{sufijo}.{ext}" if sufijo else f"{sku}.{ext}"
        ruta_local = self.dir_images / nombre_archivo
        ruta_relativa = f"images/{nombre_archivo}"

        if ruta_local.exists():
            return ruta_relativa

        try:
            resp = self._get(url)
            if resp and resp.status_code == 200:
                tipo = resp.headers.get("Content-Type", "")
                if "webp" in tipo:
                    ruta_local = self.dir_images / f"{sku}{sufijo}.webp" if sufijo else self.dir_images / f"{sku}.webp"
                    ruta_relativa = f"images/{sku}{sufijo}.webp" if sufijo else f"images/{sku}.webp"
                elif "png" in tipo:
                    ruta_local = self.dir_images / f"{sku}{sufijo}.png" if sufijo else self.dir_images / f"{sku}.png"
                    ruta_relativa = f"images/{sku}{sufijo}.png" if sufijo else f"images/{sku}.png"

                with open(ruta_local, "wb") as f:
                    f.write(resp.content)
                self.logger.debug(f"  Imagen descargada: {ruta_relativa}")
                return ruta_relativa
        except Exception as e:
            self.logger.warning(f"  Error descargando imagen {url}: {e}")
        return None

    # ─── Métodos a Sobreescribir ─────────────────────────────────────
    def obtener_urls_productos(self) -> list[str]:
        """
        Retorna lista de URLs de productos a scrapear.
        Implementación por defecto: usa sitemap XML.
        Sobreescribir para scraping por categorías.
        """
        urls = []
        sitemap_urls = self.config.get("sitemap_urls", [])
        for sitemap_url in sitemap_urls:
            self.logger.info(f"Descargando sitemap: {sitemap_url}")
            resp = self._get(sitemap_url)
            if not resp:
                continue
            soup = BeautifulSoup(resp.content, "lxml-xml")
            for loc in soup.find_all("loc"):
                url = loc.get_text(strip=True)
                if "/producto/" in url:
                    urls.append(url)
            self.logger.info(f"  Encontradas {len(urls)} URLs en sitemaps")
        return urls

    def parsear_producto(self, url: str, html: str) -> dict | None:
        """
        Parsea el HTML de una página de producto y retorna un dict con los datos.
        Implementación genérica para WooCommerce. Sobreescribir si el sitio
        usa una estructura diferente.
        """
        soup = BeautifulSoup(html, "html.parser")

        nombre = ""
        h1 = soup.find("h1", class_="product_title") or soup.find("h1")
        if h1:
            nombre = h1.get_text(strip=True)

        if not nombre:
            return None

        # SKU
        sku = ""
        sku_el = soup.find("span", class_="sku") or soup.find("sku")
        if sku_el:
            sku = sku_el.get_text(strip=True)

        # Descripción
        desc = ""
        desc_el = soup.find("div", class_="woocommerce-product-details__short-description")
        if not desc_el:
            desc_el = soup.find("div", class_="product-short-description")
        if not desc_el:
            desc_el = soup.find("div", id="tab-description")
        if desc_el:
            desc = desc_el.get_text(separator="\n", strip=True)

        # Precio
        precio = ""
        precio_el = soup.find("p", class_="price") or soup.find("span", class_="price")
        if precio_el:
            precio = precio_el.get_text(strip=True)

        # Imagen principal
        imagen = ""
        img_el = None

        # Buscar en galería WooCommerce (varios selectores posibles)
        gallery = soup.find("div", class_="woocommerce-product-gallery")
        if gallery:
            img_el = gallery.find("img", class_=lambda c: c and "wp-post-image" in c)
            if not img_el:
                img_el = gallery.find("img", class_="woocommerce-product-gallery__image")
            if not img_el:
                img_el = gallery.find("img")

        if not img_el:
            img_el = soup.find("img", class_="wp-post-image")

        if img_el:
            # Prioridad: data-src > data-large_image > src
            imagen = img_el.get("data-src") or ""
            data_large = img_el.get("data-large_image", "")
            if data_large:
                imagen = data_large
            if not imagen:
                imagen = img_el.get("src", "")

        # Filtrar data URIs y SVGs (lazy loading placeholders)
        if imagen.startswith("data:"):
            imagen = ""
        # Buscar imagen real en srcset si la principal es placeholder
        if not imagen and img_el:
            srcset = img_el.get("srcset") or img_el.get("data-srcset", "")
            if srcset:
                partes_srcset = srcset.split(",")
                if partes_srcset:
                    ultima = partes_srcset[-1].strip().split(" ")[0]
                    if ultima.startswith("http"):
                        imagen = ultima

        # Galería de imágenes
        galeria = []
        if gallery:
            for a in gallery.find_all("a"):
                href = a.get("href", "")
                if href and href != "#product-zoom" and not href.startswith("data:"):
                    # Verificar que es una imagen
                    if any(ext in href.lower() for ext in [".jpg", ".jpeg", ".png", ".webp"]):
                        if href != imagen:  # No duplicar la principal
                            galeria.append(href)

        # Categoría (breadcrumb)
        categoria = ""
        breadcrumb = soup.find("nav", class_="woocommerce-breadcrumb") or soup.find("div", class_="breadcrumb")
        if breadcrumb:
            links = breadcrumb.find_all("a")
            if len(links) >= 2:
                # Tomar la categoría (generalmente la segunda después de Inicio)
                cats = [a.get_text(strip=True) for a in links[1:]]
                categoria = " > ".join(cats)

        # Marca
        marca = ""
        marca_el = soup.find("a", href=lambda h: h and "/marca/" in h if h else False)
        if marca_el:
            marca = marca_el.get_text(strip=True)
        else:
            # Buscar en tab adicional
            for tab in soup.find_all("div", class_="woocommerce-product-attributes-item"):
                label = tab.find("th")
                value = tab.find("td")
                if label and "marca" in label.get_text(strip=True).lower():
                    marca = value.get_text(strip=True) if value else ""
                    break

        # Stock por ubicación
        stock_info = {}
        stock_el = soup.find("div", class_="stock") or soup.find("p", class_="stock")

        # Disponibilidad por tienda
        tiendas_el = soup.find("table", class_="variations") or soup.find("div", class_="variations")
        if not tiendas_el:
            # Buscar tablas de inventario
            for table in soup.find_all("table"):
                header = table.find("th")
                if header and "tienda" in header.get_text(strip=True).lower():
                    tiendas_el = table
                    break

        return {
            "sku": sku,
            "nombre": nombre,
            "descripcion": desc,
            "marca": marca,
            "categoria": categoria,
            "url_original": url,
            "imagen_principal": imagen,
            "galeria": galeria,
            "precio_texto": precio,
            "stock_texto": stock_el.get_text(strip=True) if stock_el else "",
        }

    # ─── Flujo Principal ─────────────────────────────────────────────
    def ejecutar(self):
        """Ejecuta el scraping completo."""
        self.logger.info(f"{'='*60}")
        self.logger.info(f"SCRAPER: {self.config['nombre']}")
        self.logger.info(f"Modo: {'PILOTO' if self.piloto else 'COMPLETO'}")
        self.logger.info(f"{'='*60}")

        self.init_db()

        # Obtener URLs de productos
        self.logger.info("\nPaso 1: Obteniendo URLs de productos...")
        urls = self.obtener_urls_productos()
        if not urls:
            self.logger.error("No se encontraron URLs de productos.")
            return

        if self.piloto:
            urls = urls[:self.piloto_max]
            self.logger.info(f"  Modo piloto: {len(urls)} productos seleccionados")

        self.logger.info(f"  Total URLs a procesar: {len(urls)}")

        # Scrapear cada producto
        self.logger.info("\nPaso 2: Scrapeando productos...")
        productos_guardados = 0
        for i, url in enumerate(urls, 1):
            self.logger.info(f"  [{i}/{len(urls)}] {url}")

            resp = self._get(url)
            if not resp:
                self.logger.warning(f"    Saltando (no se pudo obtener)")
                continue

            producto = self.parsear_producto(url, resp.text)
            if not producto:
                self.logger.warning(f"    Saltando (no se pudo parsear)")
                continue

            # Crear categoría si existe
            if producto.get("categoria"):
                partes = [p.strip() for p in producto["categoria"].split(">")]
                parent_id = None
                for parte in partes:
                    if parte:
                        cat_id = self.guardar_categoria(parte, parent_id)
                        parent_id = cat_id
                producto["categoria_id"] = cat_id
            else:
                producto["categoria_id"] = None

            # Guardar producto
            prod_id = self.guardar_producto(producto)
            productos_guardados += 1

            # Guardar metadata extra
            if producto.get("precio_texto"):
                self.guardar_meta(prod_id, "precio_texto", producto["precio_texto"])
            if producto.get("marca"):
                self.guardar_meta(prod_id, "marca", producto["marca"])
            if producto.get("stock_texto"):
                self.guardar_meta(prod_id, "stock_texto", producto["stock_texto"])

            # Descargar imagen principal
            if producto.get("imagen_principal") and self.descargar_imgs:
                ruta = self.descargar_imagen(
                    producto["imagen_principal"],
                    producto.get("sku", str(prod_id))
                )
                if ruta:
                    self.db.execute(
                        "UPDATE productos SET imagen_principal = ? WHERE id = ?",
                        (ruta, prod_id),
                    )
                    self.db.commit()
                    self.guardar_imagen(prod_id, producto["imagen_principal"], ruta, True)

            # Descargar galería
            if producto.get("galeria") and self.descargar_imgs:
                for j, img_url in enumerate(producto["galeria"][:5], 1):
                    sufijo = f"_galeria_{j}"
                    ruta = self.descargar_imagen(
                        img_url,
                        producto.get("sku", str(prod_id)),
                        sufijo,
                    )
                    if ruta:
                        self.guardar_imagen(prod_id, img_url, ruta, False)

            self.logger.info(f"    OK: {producto['nombre'][:50]}")

        # Actualizar contadores
        self.actualizar_contador_categoria()

        # Resumen
        total_prods = self.db.execute("SELECT COUNT(*) FROM productos").fetchone()[0]
        total_cats = self.db.execute("SELECT COUNT(*) FROM categorias").fetchone()[0]
        total_imgs = self.db.execute("SELECT COUNT(*) FROM imagenes").fetchone()[0]

        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"COMPLETADO")
        self.logger.info(f"  Productos guardados: {productos_guardados}")
        self.logger.info(f"  Total en catálogo:   {total_prods}")
        self.logger.info(f"  Categorías:         {total_cats}")
        self.logger.info(f"  Imágenes:           {total_imgs}")
        self.logger.info(f"  Base de datos:      {self.dir_proveedor / 'catalogo.db'}")
        self.logger.info(f"{'='*60}")

        self.db.close()


# ─── Punto de Entrada ─────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Scraper genérico de catálogos de ferretería"
    )
    parser.add_argument(
        "--proveedor", "-p",
        required=True,
        help="Nombre del proveedor (carpeta en proveedores/)",
    )
    parser.add_argument(
        "--piloto",
        action="store_true",
        help="Modo piloto: descarga solo una categoría pequeña",
    )
    parser.add_argument(
        "--solo-imagenes",
        action="store_true",
        help="Solo descarga imágenes (asume que catalogo.db ya existe)",
    )
    args = parser.parse_args()

    proveedor_dir = PROVEEDORES_DIR / args.proveedor
    if not proveedor_dir.exists():
        print(f"Error: No existe el proveedor '{args.proveedor}'")
        print(f"Crea la configuración en {proveedor_dir}/config.json")
        sys.exit(1)

    scraper = ScraperBase(args.proveedor, piloto=args.piloto)
    scraper.ejecutar()


if __name__ == "__main__":
    main()
