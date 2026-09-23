# Script PowerShell para iniciar DeskEvidence
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$PythonwPath = Join-Path $ScriptDir ".venv\Scripts\pythonw.exe"

if (-not (Test-Path $PythonwPath)) {
    Write-Error "Ambiente virtual .venv não encontrado em $ScriptDir"
    exit 1
}

Write-Host "Iniciando DeskEvidence no System Tray..." -ForegroundColor Green
Start-Process -FilePath $PythonwPath -ArgumentList "-m deskevidence.main" -WindowStyle Hidden
Write-Host "DeskEvidence está ativo em segundo plano! Verifique o ícone próximo ao relógio do Windows." -ForegroundColor Cyan
