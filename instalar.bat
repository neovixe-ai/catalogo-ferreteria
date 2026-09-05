@echo off
title Instalador - App de Pedidos
echo.
echo === Instalador App de Pedidos ===
echo.

cd /d "%~dp0"

echo Creando acceso directo en escritorio...

set SCRIPT="%TEMP%\create_shortcut.vbs"
echo Set oWS = WScript.CreateObject("WScript.Shell") > %SCRIPT%
echo sLinkFile = oWS.SpecialFolders("Desktop") ^& "\Pedido Ferreteria.lnk" >> %SCRIPT%
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> %SCRIPT%
echo oLink.TargetPath = "%~dp0pedido.bat" >> %SCRIPT%
echo oLink.WorkingDirectory = "%~dp0" >> %SCRIPT%
echo oLink.Description = "App de Pedidos" >> %SCRIPT%
echo oLink.Save >> %SCRIPT%

cscript /nologo %SCRIPT%
del %SCRIPT%

echo.
echo Acceso directo creado en el escritorio.
echo.
echo Para que inicie automaticamente con Windows:
echo   1. Presiona Win+R
echo   2. Escribe: shell:startup
echo   3. Copia "Pedido Ferreteria.lnk" ahi
echo.
echo LISTO. Doble clic en "Pedido Ferreteria" para abrir.
echo.
pause
