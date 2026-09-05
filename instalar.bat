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
echo oLink.TargetPath = "%~dp0abrir.bat" >> %SCRIPT%
echo oLink.WorkingDirectory = "%~dp0" >> %SCRIPT%
echo oLink.Description = "App de Pedidos" >> %SCRIPT%
echo oLink.IconLocation = "%~dp0app\static\icon-192.png,0" >> %SCRIPT%
echo oLink.Save >> %SCRIPT%

cscript /nologo %SCRIPT%
del %SCRIPT%

echo.
echo LISTO. Ahora tienes "Pedido Ferreteria" en tu escritorio.
echo Doble clic para abrir la app.
echo.
pause
