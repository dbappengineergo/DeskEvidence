@echo off
title DeskEvidence
echo Iniciando DeskEvidence em segundo plano...

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [ERRO] Ambiente virtual .venv nao encontrado!
    echo Execute: python -m venv .venv
    pause
    exit /b 1
)

start "" ".venv\Scripts\pythonw.exe" -m deskevidence.main
echo DeskEvidence iniciado com sucesso! Verifique o icone na bandeja (System Tray).
timeout /t 3 /nobreak >nul
