@echo off
chcp 65001 >nul
title Instalador de J.A.R.V.I.S. 2.0
color 0B
cd /d "%~dp0"
echo.
echo   ======================================================
echo         J.A.R.V.I.S. 2.0  -  Instalacion de componentes
echo   ======================================================
echo.

python --version >nul 2>&1
if errorlevel 1 goto sinpython

echo [1/2] Instalando librerias de Python...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 goto errorpip

echo.
echo [2/2] Cerebro en la nube: Groq, gratis
echo     No hay que descargar nada. La primera vez que abras JARVIS
echo     te aparecera una ventana para pegar tu clave gratuita de Groq.
echo     Si quieres tenerla lista, se abrira la pagina para crearla.
choice /c SN /m "  Abrir la pagina de Groq ahora"
if errorlevel 2 goto fin
start https://console.groq.com/keys

:fin
echo.
echo   ======================================================
echo     LISTO. Abre "iniciar_jarvis.bat" para probarlo,
echo     o "compilar_exe.bat" para crear el instalador .exe
echo   ======================================================
pause
exit /b

:sinpython
echo [X] No tienes Python instalado.
echo     Descarga Python 3.12 desde la pagina que se abrira
echo     y MARCA la casilla "Add Python to PATH" al instalar.
start https://www.python.org/downloads/release/python-3128/
pause
exit /b

:errorpip
echo [X] Hubo un error instalando las librerias. Toma una captura y guardala para revisarla.
pause
exit /b
