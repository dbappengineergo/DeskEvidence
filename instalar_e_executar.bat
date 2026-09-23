@echo off
title DeskEvidence - Instalador e Inicializador
echo ========================================================
echo        DeskEvidence - Preparando Ambiente
echo ========================================================
echo.

cd /d "%~dp0"

:: 1. Verifica se o Python esta instalado no sistema
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERRO] O Python nao foi encontrado neste computador!
    echo.
    echo Para executar o codigo-fonte diretamente, instale o Python 3.9+ em:
    echo https://www.python.org/downloads/
    echo.
    echo DICA: Se preferir nao instalar nada, peca o arquivo "DeskEvidence.exe"
    echo compilado, que roda diretamente sem precisar de Python instalado.
    echo.
    pause
    exit /b 1
)

:: 2. Se a pasta .venv nao existir neste PC, cria o ambiente virtual local
if not exist ".venv\Scripts\python.exe" (
    echo [1/2] Criando ambiente virtual local (.venv)...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo [ERRO] Falha ao criar o ambiente virtual.
        pause
        exit /b 1
    )
    
    echo [2/2] Instalando dependencias necessarias...
    .\.venv\Scripts\python.exe -m pip install --upgrade pip --quiet
    .\.venv\Scripts\python.exe -m pip install -r requirements.txt --quiet
    .\.venv\Scripts\python.exe deskevidence\assets\generate_icons.py
)

:: 3. Executa o aplicativo em segundo plano via pythonw
echo.
echo Iniciando DeskEvidence em segundo plano...
start "" ".\.venv\Scripts\pythonw.exe" -m deskevidence.main
echo.
echo Pronto! O DeskEvidence esta ativo no System Tray (ao lado do relogio).
timeout /t 3 /nobreak >nul
