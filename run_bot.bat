@echo off
title Lanzador de Bot - Fases AFK
:: Cambiar al directorio del script
cd /d "%~dp0"

:: Comprobar si se ejecuta como Administrador
net session >nul 2>&1
if %errorLevel% == 0 (
    echo ============================================================
    echo           Lanzando Bot con Privilegios de Administrador
    echo ============================================================
    python bot.py
) else (
    echo ============================================================
    echo Solicitando permisos de Administrador...
    echo ============================================================
    :: Lanzar el mismo archivo BAT con permisos de administrador
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
)
