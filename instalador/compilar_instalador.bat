@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0.."
color 07
title Compilar instalador - Suno v1

set "RAIZ=%CD%"
set "INST=%RAIZ%\instalador"
set "WIX=%INST%\wix"
set "ARTE=%INST%\arte"
set "PY=%RAIZ%\.venv\Scripts\python.exe"

echo.
echo  ============================================
echo   SUNO v1 - compilar instalador .msi
echo  ============================================
echo.

if not exist "%PY%" (
  echo  [X] No encuentro .venv\Scripts\python.exe
  echo      Ejecuta primero "Iniciar Mi Suno.bat".
  goto :error
)

if not exist "%RAIZ%\dist\Mi Suno\Mi Suno.exe" (
  echo  [X] No existe dist\Mi Suno\Mi Suno.exe
  echo      Compila la aplicacion con compilar.bat y vuelve a intentarlo.
  goto :error
)

echo  [1/5] Generando arte del instalador...
"%PY%" "%INST%\hacer_arte.py"
if errorlevel 1 goto :error

echo  [2/5] Listando archivos de la aplicacion...
"%PY%" "%INST%\generar_componentes.py"
if errorlevel 1 goto :error

if exist "%WIX%\candle.exe" (
  echo  [3/5] WiX Toolset ya presente, sin descargar.
  goto :wix_listo
)
echo  [3/5] Descargando WiX Toolset 3.14...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference='Stop'; New-Item -ItemType Directory -Force -Path '%WIX%' | Out-Null; Invoke-WebRequest -Uri 'https://github.com/wixtoolset/wix3/releases/download/wix3141rtm/wix314-binaries.zip' -OutFile '%WIX%\wix314.zip' -UseBasicParsing; Expand-Archive -Path '%WIX%\wix314.zip' -DestinationPath '%WIX%' -Force; Remove-Item '%WIX%\wix314.zip'"
if not exist "%WIX%\candle.exe" (
  echo  [X] No se pudo descargar WiX. Revisa la conexion a internet.
  goto :error
)
:wix_listo

echo  [4/5] Compilando recursos (candle)...
if not exist "%INST%\obj" mkdir "%INST%\obj"
"%WIX%\candle.exe" -nologo -arch x64 "-dArte=%ARTE%" -ext "%WIX%\WixUIExtension.dll" -out "%INST%\obj\\" "%INST%\Producto.wxs" "%INST%\Ficheros.wxs"
if errorlevel 1 goto :error

echo  [5/5] Empaquetando el .msi (light)...
"%WIX%\light.exe" -nologo -sw1076 -sice:ICE38 -sice:ICE43 -sice:ICE57 -ext "%WIX%\WixUIExtension.dll" -cultures:es-ES -out "%INST%\Suno v1.msi" "%INST%\obj\Producto.wixobj" "%INST%\obj\Ficheros.wixobj"
if errorlevel 1 goto :error

echo.
echo  ============================================
echo   Listo: instalador\Suno v1.msi
echo  ============================================
echo   Instala en C:\Program Files\Suno v1
echo   Acceso directo en el menu Inicio y en
echo   Aplicaciones instaladas. Pide administrador.
echo.
start "" explorer /select,"%INST%\Suno v1.msi"
goto :fin

:error
echo.
echo  [X] La compilacion fallo. Revisa los mensajes de arriba.

:fin
echo.
pause
endlocal
