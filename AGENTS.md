# AGENTS.md — Guia para IA: Como Colaborar en Este Proyecto

## Que es Este Proyecto

Sistema completo para ferreterias venezolanas que permite:
1. **Extraer** catalogos desde PDFs (scraper/)
2. **Distribuir** una app de pedidos como APK (apk-builder/)
3. **Vendedores** reciben el APK por WhatsApp, lo instalan, y hacen pedidos

## Arquitectura General

```
┌─────────────────────────────────────────────────────────────────┐
│                        TRES PARTES                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. EXTRACCION (scraper/)                                       │
│     PDF → Template JSON → SQLite + Imagenes                     │
│                                                                 │
│  2. APP PEDIDOS (apk-builder/ferreteria/assets/www/)            │
│     HTML + JS + Imagenes → App que corre en WebView             │
│                                                                 │
│  3. BUILD APK (apk-builder/)                                    │
│     Java + HTML + Imagenes → APK firmado para Android           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Entornos Soportados

| Entorno | Para que sirve | Comando inicial |
|---------|----------------|-----------------|
| **Windows** | Editar codigo, imagenes, JSON | Abrir carpeta en VS Code |
| **Linux** | Editar codigo, extraer PDFs | `cd ~/catalogo-ferreteria && git pull` |
| **Termux** | Construir APK | `cd ~/catalogo-ferreteria && git pull` |

### Flujo de Trabajo

```
WINDOWS (editor)  →  git push  →  TERMUX (build)  →  APK  →  WhatsApp
```

1. Editas codigo en Windows (VS Code, Notepad++, etc.)
2. Haces `git push`
3. En Termux haces `git pull`
4. Construyes el APK con `./build.sh`
5. Envias el APK por WhatsApp

---

## PARTE 1: Extraccion de Catalogos (scraper/)

### Que hace
Convierte PDFs de catalogos de ferreteria en:
- Base de datos SQLite (proveedores/{proveedor}/catalogo.db)
- Imagenes de productos (proveedores/{proveedor}/images/)
- JSON con productos (proveedores/{proveedor}/productos.json)

### Estructura

```
scraper/
├── extractor_con_posiciones.py     # Extraccion con imagenes (principal)
├── extractor_con_actualizacion.py  # Logica de fechas (catalogos nuevos)
├── generar_json.py                 # Convierte DB a JSON
├── generar_dist.sh                 # Genera distribucion ZIP
├── test_template.py                # Pruebas
└── requirements.txt                # Dependencias Python
```

### Templates

Cada proveedor tiene un template en `templates/{proveedor}.json`:

```json
{
  "version": "1.0",
  "proveedor": { "nombre": "LC 2050", "rif": "J-50799044-3" },
  "layout": { "productos_por_pagina": 10, "columnas": 2, "filas": 5 },
  "producto": {
    "sku": { "formato": "[A-Z]{3}[0-9]{3}", "posicion": "superior_izquierda" },
    "nombre": { "case": "MAYUSCULAS", "max_lineas": 3 },
    "precio": { "formato": "[0-9]+,[0-9]+\\$", "posicion": "inferior" }
  }
}
```

### Proveedor Actual: LC 2050

- **RIF**: J-50799044-3
- **Ubicacion**: `proveedores/lc_2050/`
- **Productos**: ~1,726
- **Imagenes**: 3,940 JPGs (~261MB)
- **DB**: `proveedores/lc_2050/catalogo.db`

### Logica de Fechas

Cuando llega un catalogo nuevo:
| Condicion | Fecha Catalogo | Accion |
|-----------|----------------|--------|
| SKU no existe | Cualquiera | INSERTAR |
| SKU existe | Mas nueva que DB | ACTUALIZAR precio |
| SKU existe | Mas vieja que DB | NO TOCAR |
| SKU existe | Igual que DB | NO TOCAR |

**NUNCA eliminar productos.** Solo insertar o actualizar.

### Comandos Utiles

```bash
# Ver productos en DB
sqlite3 proveedores/lc_2050/catalogo.db "SELECT COUNT(*) FROM productos"

# Buscar producto
sqlite3 proveedores/lc_2050/catalogo.db "SELECT * FROM productos WHERE nombre LIKE '%compresor%'"

# Ver imagenes
ls proveedores/lc_2050/images/ | head -20

# Extraer catalogo nuevo
python3 scraper/extractor_con_actualizacion.py --pdf "nuevo_catalogo.pdf" --muestra 5
```

---

## PARTE 2: App de Pedidos (apk-builder/ferreteria/assets/www/)

### Que es
Una app HTML+JS que corre dentro de un WebView en Android. No necesita internet.

### Funcionalidades

1. **Scroll infinito** - Intersection Observer carga productos al hacer scroll
2. **Busqueda** - Filtra por SKU o nombre
3. **Detalle de producto** - Modal con imagen, precio, descripcion completa
4. **Agregar/quitar** - Botones +/- para cantidad
5. **Multiples pedidos** - Crear, enviar, eliminar pedidos (IndexedDB)
6. **Enviar por WhatsApp** - Links `wa.me` con mensaje formateado
7. **Descargar PDF** - Navegador imprime el pedido
8. **Alerta discontinuado** - Si un producto ya no esta en catalogo actual, avisa antes de enviar
9. **Ajustes** - Numero de WhatsApp editable, nombre del cliente
10. **Precios en $** - Formato: `$1.234,56`

### Estructura de Archivos

```
apk-builder/ferreteria/assets/www/
├── index.html                    # App principal (TODO el codigo)
├── data/
│   ├── productos.js              # Productos del catalogo (window.PRODUCTOS)
│   └── productos.json            # Mismo catalogo en JSON (para la web/app)
└── proveedores/
    └── lc_2050/
        └── images/
            ├── COC003.webp       # Imagen WebP optimizada
            ├── COC004.webp
            └── ...
```

### Como Funciona Internamente

```
index.html
├── <style>           # CSS completo (diseño movil)
├── <body>            # HTML (pantallas: lista, detalle, pedido, ajustes)
└── <script>          # JavaScript:
    ├── data/productos.js  # Catalogo via <script src> (window.PRODUCTOS)
    ├── IndexedDB     # Almacena productos y pedidos
    ├── localStorage  # Guarda ajustes (WhatsApp, nombre)
    ├── IntersectionObserver  # Scroll infinito
    └── wa.me links   # Envio por WhatsApp
```

**IMPORTANTE**: El catalogo se carga con `<script src="data/productos.js">`, **NO** con `fetch()`. En Android WebView con targetSdk >= 30, `fetch()` de archivos locales sobre `file://` esta bloqueado y la app queda con los 30 productos de respaldo.

### Como Modificar

#### Cambiar colores
Editar variables CSS al inicio del `<style>`:
```css
:root {
  --primary: #2c3e50;    /* Color principal */
  --success: #27ae60;    /* Verde (precios, totales) */
  --danger: #e74c3c;     /* Rojo (botones borrar) */
}
```

#### Cambiar formato de mensaje WhatsApp
Buscar la funcion `enviarWhatsApp()` y modificar el template del mensaje.

#### Agregar campo al pedido
1. Agregar input en HTML (seccion `s3`)
2. Modificar `renderPed()` para mostrarlo
3. Incluir en el mensaje de WhatsApp

#### Cambiar logica de precios
Buscar donde se parsea `precio_texto` y modificar el formato.

### Optimizacion de Imagenes

Las imagenes JPG originales (~66KB c/u) se convierten a WebP (~23KB c/u):

```python
# Script para optimizar
from PIL import Image
import os

input_dir = "proveedores/lc_2050/images"
output_dir = "apk-builder/ferreteria/assets/www/proveedores/lc_2050/images"

for f in os.listdir(input_dir):
    if f.endswith('.jpg'):
        img = Image.open(os.path.join(input_dir, f))
        img = img.resize((200, 200), Image.LANCZOS)
        out_name = f.replace('.jpg', '.webp')
        img.save(os.path.join(output_dir, out_name), 'WEBP', quality=80)
```

**Resultado**: 261MB JPG → ~91MB WebP

---

## PARTE 3: Construccion del APK (apk-builder/)

### Prerrequisitos (una sola vez en Termux)

```bash
# 1. Actualizar sistema
pkg update && pkg upgrade

# 2. Instalar herramientas
pkg install openjdk-17 aapt apksigner wget unzip

# 3. Descargar Android SDK build-tools (para d8)
wget -O /tmp/cmdline-tools.zip \
  https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip
mkdir -p ~/android-sdk
unzip /tmp/cmdline-tools.zip -d ~/android-sdk/

# 4. Instalar build-tools con sdkmanager
yes | ~/android-sdk/cmdline-tools/bin/sdkmanager --install "build-tools;34.0.0"

# 5. Agregar al PATH
echo 'export PATH=$PATH:~/android-sdk/build-tools/34.0.0' >> ~/.bashrc
source ~/.bashrc

# 6. Verificar
d8 --version
aapt version
apksigner --version
```

### Estructura del Proyecto Android

```
apk-builder/
├── build.sh                          # Script de construccion
└── ferreteria/
    ├── AndroidManifest.xml           # Package, permisos, activity
    ├── assets/
    │   └── www/                      # La app HTML va aqui
    │       ├── index.html
    │       ├── data/productos.js     # Catalogo (cargado con <script src>, funciona en file://)
    │       ├── data/productos.json
    │       └── proveedores/lc_2050/images/*.webp
    ├── res/
    │   ├── layout/activity_main.xml  # Layout del WebView
    │   ├── mipmap-*/ic_launcher.png  # Iconos (5 tamanos)
    │   └── values/
    │       ├── strings.xml           # Nombre de la app
    │       └── styles.xml            # Tema
    └── src/com/ferreteria/pedido/
        └── MainActivity.java         # WebView + copia assets
```

### Pipeline de Construccion

```
src/com/ferreteria/pedido/*.java
   ↓ javac --release 8
build/classes/*.class
   ↓ jar cvf
build/classes.jar
   ↓ d8 --min-api 26
build/classes.dex
                        ┐
AndroidManifest.xml  ──┐│
res/                 ──┼┤ aapt package -F build/base.apk
assets/www/          ──┘┘
                        ┘
build/base.apk
   ↓ aapt add (classes.dex + assets)
   ↓ apksigner sign
ferreteria-app.apk
```

### Comando para Construir

```bash
cd apk-builder
./build.sh ferreteria
# → ferreteria-app.apk (~91MB)
```

### Probar en Dispositivo

```bash
# Opcion 1: ADB (si hay cable USB)
adb install -r ferreteria-app.apk
adb shell am start -n com.ferreteria.pedido/.MainActivity

# Opcion 2: Enviar por WhatsApp
# Copiar APK a telefono y abrir
```

### Tamano Estimado del APK

| Componente | Tamano |
|------------|--------|
| Shell Android (Java + DEX) | ~30KB |
| HTML + CSS + JS | ~175KB |
| JSON productos | ~158KB |
| Imagenes WebP (3,940) | ~91MB |
| **Total** | **~91MB** |

---

## Logica de Negocio

### Catalogo Semilla

El catalogo mas nuevo es el valido para pedidos.

### Reglas

1. **Solo el nuevo vale** - Solo se puede pedir productos del catalogo actual
2. **Sin precio = no disponible** - Sin precio en catalogo nuevo, no se puede pedir
3. **No esta = descontinuado** - Si no esta en catalogo nuevo, no se puede pedir
4. **Nunca borrar** - Productos viejos quedan en DB como historico
5. **Precio nuevo prevalece** - El precio del catalogo nuevo es el unico valido

### Formato de Precio

- **Moneda**: $ (dolares)
- **Formato**: `$1.234,56` (coma separador de miles, punto decimal)
- **Ejemplo**: `$1.234,56` = mil doscientos treinta y cuatro dolares con 56 centavos

### Descuentos

- El usuario puede aplicar un **descuento porcentaje** sobre el subtotal
- El descuento se calcula sobre el total antes de impuestos
- El porcentaje es editable (0% a 100%)
- El descuento se guarda en el pedido y se muestra en el PDF

### Envio por WhatsApp

**IMPORTANTE**: El mensaje al proveedor **NO incluye precios ni montos**.

El formato del mensaje es:
```
*Pedido Mi Pedido*

*Cliente:* Nombre del cliente
*Fecha:* 05/09/2026

*Productos:*
*COC003* ANILLO DE COMPRESION x5
*COC004* BANDEJA P/ RESISTENCIA x10
...

*Notas:* Instrucciones especiales
```

**Reglas para WhatsApp:**
1. Solo SKU + nombre corto (max 3 palabras) + cantidad
2. Sin precios, sin subtotales, sin total
3. El proveedor calcula los precios
4. Los productos sin precio se omiten del mensaje

### PDF (Descarga)

El PDF **SÍ incluye precios** (es para uso interno del cliente):
- Subtotal
- Descuento (si aplica)
- Total final

---

## Errores Comunes

| Error | Causa | Solucion |
|-------|-------|----------|
| APK no compila | Falta d8 en PATH | Verificar `echo $PATH` |
| WebView blanco | Archivos no copiados | Verificar assets/www/ |
| Imagenes no cargan | Ruta incorrecta | Verificar path en HTML |
| WhatsApp no abre | Numero incorrecto | Verificar ajustes de WhatsApp |
| Precios mal | Formato incorrecto | Revisar parseo en JS |

---

## Checklist para Modificar el Proyecto

### Agregar funcionalidad al HTML
- [ ] Editar `apk-builder/ferreteria/assets/www/index.html`
- [ ] Probar en navegador (abrir index.html directamente)
- [ ] Si funciona, construir APK con `./build.sh ferreteria`
- [ ] Probar APK en dispositivo Android

### Agregar nuevo proveedor
- [ ] Crear template en `templates/{proveedor}.json`
- [ ] Extraer catalogo con `scraper/extractor_con_posiciones.py`
- [ ] Optimizar imagenes a WebP
- [ ] Copiar imagenes a `apk-builder/ferreteria/assets/www/proveedores/{proveedor}/images/`
- [ ] Actualizar JSON con `scraper/generar_json.py`
- [ ] Modificar HTML para soportar multiples proveedores
- [ ] Construir APK

### Cambiar numero de WhatsApp
- [ ] Editar funcion `enviarWhatsApp()` en index.html
- [ ] Cambiar numero por defecto en `localStorage`
- [ ] Construir APK

### Cambiar nombre de app
- [ ] Editar `apk-builder/ferreteria/res/values/strings.xml`
- [ ] Cambiar `app_name`
- [ ] Construir APK
- [ ] El icono se actualiza con el mismo nombre

---

## Herramientas del Sistema

```bash
# Git
git pull
git add .
git commit -m "feat: agregar catalogo [Proveedor] [Fecha]"
git push

# Python (extraccion)
python3 scraper/extractor_con_posiciones.py --pdf "catalogo.pdf"

# SQLite
sqlite3 proveedores/{proveedor}/catalogo.db "SELECT..."

# Android (desde Termux)
cd apk-builder && ./build.sh ferreteria

# Optimizar imagenes
python3 -c "from PIL import Image; ..."

# Verificar APK
apksigner verify --print-certs ferreteria-app.apk
```

---

## Notas Importantes

1. **El APK se construye UNA SOLA VEZ** y se distribuye por WhatsApp
2. **Las actualizaciones** requieren nuevo APK (no hay auto-update)
3. **Sin internet** - La app funciona 100% offline
4. **Tamano ~91MB** - Es normal por las imagenes optimizadas
5. **Windows para codigo, Termux para build** - Es el workflow recomendado
