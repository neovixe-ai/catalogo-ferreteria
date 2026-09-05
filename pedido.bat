@echo off
title App de Pedidos
echo.
echo === App de Pedidos ===
echo Iniciando servidor...
echo.

cd /d "%~dp0"

start /b pythonw app/pedido.py 5000

timeout /t 2 /nobreak >nul

start http://localhost:5000

echo.
echo App iniciada. Cierra esta ventana.
echo La app seguira abierta en el navegador.
echo.
pause
