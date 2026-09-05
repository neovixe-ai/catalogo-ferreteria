#!/bin/bash
# Genera el paquete distribuible para el usuario final
# Solo incluye la app de pedidos, no todo el proyecto

echo "Generando paquete de distribución..."

RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
DIST="$RAIZ/dist"

rm -rf "$DIST"
mkdir -p "$DIST/app/data"
mkdir -p "$DIST/proveedores/lc_2050/images"

# App
cp "$RAIZ/app/index.html" "$DIST/app/"
cp "$RAIZ/app/data/productos.json" "$DIST/app/data/"

# Imágenes (solo las que tienen SKU)
cp "$RAIZ"/proveedores/lc_2050/images/*.jpg "$DIST/proveedores/lc_2050/images/" 2>/dev/null

# Windows: script para abrir
cat > "$DIST/abrir.bat" << 'EOF'
@echo off
start "" "%~dp0app\index.html"
EOF

# Windows: instalador
cat > "$DIST/instalar.bat" << 'EOF'
@echo off
title Instalador - App de Pedidos
cd /d "%~dp0"
set SCRIPT="%TEMP%\create_shortcut.vbs"
echo Set oWS = WScript.CreateObject("WScript.Shell") > %SCRIPT%
echo sLinkFile = oWS.SpecialFolders("Desktop") ^& "\Pedido LC 2050.lnk" >> %SCRIPT%
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> %SCRIPT%
echo oLink.TargetPath = "%~dp0abrir.bat" >> %SCRIPT%
echo oLink.WorkingDirectory = "%~dp0" >> %SCRIPT%
echo oLink.Description = "Pedido LC 2050" >> %SCRIPT%
echo oLink.Save >> %SCRIPT%
cscript /nologo %SCRIPT%
del %SCRIPT%
echo.
echo LISTO. Toca "Pedido LC 2050" en tu escritorio.
echo.
pause
EOF

echo ""
echo "Paquete generado en: $DIST"
echo ""

# Contar archivos
imgs=$(ls "$DIST/proveedores/lc_2050/images/"*.jpg 2>/dev/null | wc -l)
echo "  Imágenes: $imgs"
echo ""
echo "Para comprimir:"
echo "  cd $RAIZ && zip -r pedido-lc2050.zip dist/"
