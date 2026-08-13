@echo off
title Lanzador de Dashboard - Fases AFK
:: Cambiar al directorio del script
cd /d "%~dp0"

:: Comprobar si se ejecuta como Administrador
net session >nul 2>&1
if %errorLevel% == 0 (
    start "" pythonw gui.py
    exit
) else (
    :: Lanzar el mismo archivo BAT con permisos de administrador
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
)
