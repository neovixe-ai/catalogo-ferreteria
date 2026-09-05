# Mi Pedido - Catalogo de Ferreteria

Sistema para que vendedores de ferreteria hagan pedidos desde su telefono.

## Como Funciona

```
1. Recibes un APK por WhatsApp (91MB)
2. Lo instalas (1 toque)
3. Abres la app "Mi Pedido"
4. Buscas productos
5. Agregas al pedido
6. Envias por WhatsApp o descargas PDF
```

**Sin internet. Sin configuracion. Sin extraer archivos.**

## Distribucion

El APK se envia por WhatsApp. El vendedor:
- Recibe el archivo
- Toca "Instalar"
- Abre la app
- ¡Listo!

## Desarrollo

### Estructura del Proyecto

```
catalogo-ferreteria/
├── scraper/                    # Extraccion de PDFs
│   ├── extractor_con_posiciones.py
│   └── extractor_con_actualizacion.py
├── templates/                  # Templates por proveedor
│   └── lc_2050.json
├── proveedores/                # Datos extraidos
│   └── lc_2050/
│       ├── catalogo.db         # SQLite (1,726 productos)
│       ├── images/             # 3,940 imagenes JPG
│       └── productos.json      # JSON para la app
├── apk-builder/                # Construccion del APK
│   ├── build.sh                # Script de construccion
│   └── ferreteria/
│       ├── AndroidManifest.xml
│       ├── assets/www/         # App HTML va aqui
│       ├── res/                # Iconos, layouts
│       └── src/                # Java (WebView)
└── index.html                  # App de pedidos (standalone)
```

### Requisitos

**Para extraccion:**
- Python 3.8+
- PyMuPDF (`pip install PyMuPDF`)
- SQLite3

**Para APK:**
- Termux (Android)
- openjdk-17
- aapt
- apksigner
- Android SDK build-tools (para d8)

### Modificar la App

1. Editar `apk-builder/ferreteria/assets/www/index.html`
2. Probar en navegador (abrir index.html)
3. Construir APK: `cd apk-builder && ./build.sh ferreteria`
4. Probar en dispositivo Android

### Agregar Nuevo Proveedor

1. Crear template en `templates/{proveedor}.json`
2. Extraer catalogo: `python3 scraper/extractor_con_posiciones.py --pdf "catalogo.pdf"`
3. Optimizar imagenes a WebP
4. Copiar a `apk-builder/ferreteria/assets/www/proveedores/{proveedor}/images/`
5. Actualizar JSON
6. Construir APK

### Construir el APK

```bash
cd apk-builder
./build.sh ferreteria
# Genera: ferreteria-app.apk (~91MB)
```

### Probar en Dispositivo

```bash
# Con cable USB
adb install -r ferreteria-app.apk

# Sin cable: enviar APK por WhatsApp y abrir
```

## Proveedor Actual

**LC 2050** (Distribuidora 2050 LC)
- RIF: J-50799044-3
- Productos: ~1,726
- Imagenes: 3,940

## Documentacion

- `AGENTS.md` - Guia completa para IA y desarrolladores
- `scraper/` - Scripts de extraccion de PDFs
- `apk-builder/` - Construccion del APK

## License

Uso interno.
