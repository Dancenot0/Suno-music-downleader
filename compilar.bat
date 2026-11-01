@echo off
REM Compila "Mi Suno" a un ejecutable de Windows con PyInstaller.
REM Requiere conexion a internet la primera vez (instala pyinstaller).
cd /d "%~dp0"

echo == Generando icono ==
".venv\Scripts\python.exe" build_icon.py

echo == Instalando PyInstaller ==
".venv\Scripts\python.exe" -m pip install --upgrade pyinstaller

echo == Compilando ==
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --windowed ^
  --name "Mi Suno" ^
  --icon "assets\mi_suno.ico" ^
  --add-data "assets;assets" ^
  --add-data "herramientas;herramientas" ^
  app_pyside.py

echo.
echo Listo: dist\Mi Suno\Mi Suno.exe
pause
