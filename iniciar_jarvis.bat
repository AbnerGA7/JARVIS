@echo off
chcp 65001 >nul
title J.A.R.V.I.S. - consola de diagnostico
color 0B
cd /d "%~dp0"
echo  Iniciando J.A.R.V.I.S.  (cierra esta ventana para apagarlo)
python jarvis.py
if errorlevel 1 pause
