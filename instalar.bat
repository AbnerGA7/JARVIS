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

echo [1/3] Instalando librerias de Python...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 goto errorpip

echo.
echo [2/3] Revisando Ollama, el cerebro de JARVIS...
where ollama >nul 2>&1
if not errorlevel 1 goto hayollama
if exist "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" set "PATH=%PATH%;%LOCALAPPDATA%\Programs\Ollama"
where ollama >nul 2>&1
if not errorlevel 1 goto hayollama
echo [!] Falta Ollama. Se abrira la pagina de descarga: instalalo y vuelve a abrir este archivo.
start https://ollama.com/download/windows
pause
exit /b

:hayollama
for /f %%r in ('powershell -NoProfile -Command "[int]((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory/1GB)"') do set RAM=%%r
echo     Tu PC tiene %RAM% GB de RAM.
set MODELO=qwen2.5:3b
if %RAM% GEQ 14 set MODELO=qwen2.5:7b
echo     Descargando el cerebro %MODELO%  -  solo la primera vez, puede tardar...
ollama pull %MODELO%

echo.
echo [3/3] Modulo de vision opcional: permite que JARVIS vea tu pantalla, unos 1.7 GB
choice /c SN /m "  Quieres instalarlo"
if errorlevel 2 goto fin
ollama pull moondream

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
echo [X] Hubo un error instalando las librerias. Toma una captura y enviasela a Claude.
pause
exit /b
