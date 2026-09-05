#!/bin/bash
# Instalador - Ejecutar una sola vez
# Esto instala Termux:Boot y crea el icono en la pantalla de inicio

echo "=== Instalador App de Pedidos ==="
echo ""

# 1. Instalar Termux:Boot
echo "1. Instalando Termux:Boot..."
if ! command -v termux-boot &> /dev/null; then
    pkg install termux-boot -y 2>/dev/null || echo "   Instala Termux:Boot desde F-Droid"
fi

# 2. Crear script de auto-start
echo "2. Configurando auto-start..."
mkdir -p ~/.termux/boot
cat > ~/.termux/boot/start-pedido.sh << 'EOF'
#!/data/data/com.termux/files/usr/bin/bash
termux-wake-lock
cd ~/catalogo-ferreteria
python3 app/pedido.py 5000 &
EOF
chmod +x ~/.termux/boot/start-pedido.sh

# 3. Iniciar ahora mismo
echo "3. Iniciando servidor..."
cd ~/catalogo-ferreteria
python3 app/pedido.py 5000 &
sleep 2

# 4. Mostrar IP
IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")
echo ""
echo "=== LISTO ==="
echo ""
echo "Abre en Chrome:"
echo "  http://localhost:5000"
echo ""
echo "Para agregar icono a pantalla de inicio:"
echo "  1. Abre http://localhost:5000 en Chrome"
echo "  2. Toca los 3 puntos (menu)"
echo "  3. Toca 'Agregar a pantalla de inicio'"
echo "  4. Toca 'Agregar'"
echo ""
echo "La app iniciara automaticamente al encender el telefono."
