#!/usr/bin/env node
/**
 * Importador de Catálogo → FerrePunto
 * ====================================
 * Lee el catalogo.db de un proveedor y lo importa a FerrePunto vía API REST.
 *
 * Uso:
 *   node importar_ferrepunto.js --proveedor barbosa --token JWT_TOKEN
 *   node importar_ferrepunto.js --proveedor barbosa --url http://localhost:4848 --token JWT
 */

const Database = require("better-sqlite3");
const fs = require("fs");
const path = require("path");

const RAIZ = path.resolve(__dirname, "..");
const PROVEEDORES_DIR = path.join(RAIZ, "proveedores");

function parseArgs() {
  const args = process.argv.slice(2);
  const config = { proveedor: null, url: "http://localhost:4848", token: null, empresa_id: null, dry_run: false };
  for (let i = 0; i < args.length; i++) {
    if (args[i] === "--proveedor" && args[i + 1]) config.proveedor = args[++i];
    else if (args[i] === "--url" && args[i + 1]) config.url = args[++i];
    else if (args[i] === "--token" && args[i + 1]) config.token = args[++i];
    else if (args[i] === "--empresa" && args[i + 1]) config.empresa_id = args[++i];
    else if (args[i] === "--dry-run") config.dry_run = true;
  }
  if (!config.proveedor) { console.error("Uso: node importar_ferrepunto.js --proveedor NOMBRE --token JWT"); process.exit(1); }
  if (!config.token) { console.error("Error: --token requerido"); process.exit(1); }
  return config;
}

async function apiFetch(config, method, endpoint, body = null) {
  const url = `${config.url}${endpoint}`;
  const opts = {
    method,
    headers: { "Authorization": `Bearer ${config.token}`, "Content-Type": "application/json" },
  };
  if (body) opts.body = JSON.stringify(body);
  const resp = await fetch(url, opts);
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`API ${method} ${endpoint} → ${resp.status}: ${text}`);
  }
  return resp.json();
}

async function main() {
  const config = parseArgs();
  const dbPath = path.join(PROVEEDORES_DIR, config.proveedor, "catalogo.db");
  if (!fs.existsSync(dbPath)) { console.error(`No se encontró ${dbPath}`); process.exit(1); }

  const db = new Database(dbPath, { readonly: true });
  console.log(`\nImportando catálogo de "${config.proveedor}" → FerrePunto (${config.url})\n`);

  // 1. Importar categorías
  const cats = db.prepare("SELECT * FROM categorias ORDER BY id").all();
  console.log(`Categorías a importar: ${cats.length}`);
  const catMap = {};
  for (const cat of cats) {
    if (config.dry_run) { console.log(`  [DRY] Categoría: ${cat.nombre}`); catMap[cat.id] = cat.id; continue; }
    try {
      const res = await apiFetch(config, "POST", "/api/categorias", { nombre: cat.nombre, codigo: cat.slug });
      catMap[cat.id] = res.id;
      console.log(`  ✓ ${cat.nombre} → ID ${res.id}`);
    } catch (e) {
      console.log(`  ✗ ${cat.nombre}: ${e.message}`);
    }
  }

  // 2. Importar productos
  const prods = db.prepare("SELECT * FROM productos ORDER BY id").all();
  console.log(`\nProductos a importar: ${prods.length}`);
  let importados = 0;
  for (const prod of prods) {
    const categoria_id = catMap[prod.categoria_id] || null;
    const payload = {
      nombre: prod.nombre,
      sku: prod.sku || undefined,
      categoria_id,
      precio_usd: 0,
      imagen_url: prod.imagen_principal ? `/api/storage/${config.empresa_id || "default"}/${prod.sku}.webp` : null,
      activo: 1,
    };
    if (config.dry_run) { console.log(`  [DRY] ${prod.sku} - ${prod.nombre}`); importados++; continue; }
    try {
      await apiFetch(config, "POST", "/api/productos", payload);
      importados++;
      if (importados % 10 === 0) console.log(`  ... ${importados}/${prods.length}`);
    } catch (e) {
      console.log(`  ✗ ${prod.sku}: ${e.message}`);
    }
  }

  console.log(`\n✓ Importación completada: ${importados}/${prods.length} productos`);
  db.close();
}

main().catch((e) => { console.error("Error fatal:", e); process.exit(1); });
