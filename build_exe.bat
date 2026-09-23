@echo off
title Compilar DeskEvidence em Executavel Unico (.exe)
echo ========================================================
echo       Compilando DeskEvidence para Executavel
echo ========================================================
echo.

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [ERRO] Ambiente virtual .venv nao encontrado!
    echo Execute: python -m venv .venv
    pause
    exit /b 1
)

echo [1/3] Garantindo dependencias de build (PyInstaller)...
.\.venv\Scripts\python.exe -m pip install pyinstaller --quiet

echo [2/3] Gerando icones caso necessario...
.\.venv\Scripts\python.exe deskevidence\assets\generate_icons.py

echo Fechando instancias antigas em execucao para liberar o arquivo...
taskkill /f /im DeskEvidence.exe >nul 2>nul

echo [3/3] Gerando executavel standalone DeskEvidence.exe em dist/...
.\.venv\Scripts\pyinstaller.exe ^
    --noconsole ^
    --onefile ^
    --paths . ^
    --name DeskEvidence ^
    --icon deskevidence\assets\icon.ico ^
    --add-data "deskevidence\assets;deskevidence\assets" ^
    --collect-all customtkinter ^
    --clean ^
    deskevidence\main.py

if exist "dist\DeskEvidence.exe" (
    echo.
    echo ========================================================
    echo  SUCESSO! Executavel gerado em: dist\DeskEvidence.exe
    echo  Basta copiar este arquivo para qualquer computador Windows!
    echo ========================================================
) else (
    echo.
    echo [ERRO] Falha na compilacao do executavel.
)

pause
