@echo off
chcp 65001 >nul
title Fabricando J.A.R.V.I.S.
color 0B
cd /d "%~dp0"
echo.
echo   ======================================================
echo     Paso 1 de 2: creando JARVIS.exe
echo   ======================================================
python -m pip install --upgrade pyinstaller
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
python -m PyInstaller --noconfirm --clean JARVIS.spec
if not exist "dist\JARVIS\JARVIS.exe" goto fallo

echo.
echo   ======================================================
echo     Paso 2 de 2: creando el instalador JARVIS_Setup.exe
echo   ======================================================
set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if exist "%ISCC%" goto compilar
echo   Instalando Inno Setup, el programa que fabrica instaladores...
winget install -e --id JRSoftware.InnoSetup --accept-package-agreements --accept-source-agreements
set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" goto sininno

:compilar
"%ISCC%" instalador.iss
if errorlevel 1 goto sininno
echo.
echo   ======================================================
echo     LISTO!  Tu instalador: salida\JARVIS_Setup.exe
echo   ======================================================
start "" salida
pause
exit /b

:sininno
echo   No pude crear el instalador, pero JARVIS ya funciona desde: dist\JARVIS\JARVIS.exe
echo   Para el instalador, instala Inno Setup desde https://jrsoftware.org/isdl.php y repite.
start "" dist\JARVIS
pause
exit /b

:fallo
echo [X] Fallo la compilacion. Toma una captura de los mensajes de arriba y enviasela a Claude.
pause
exit /b
