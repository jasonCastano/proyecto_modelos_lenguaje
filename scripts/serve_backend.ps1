# Backend de Valer-IA como servicio del PC servidor (spec 024, T027).
# Uso:
#   .\scripts\serve_backend.ps1              # arranca uvicorn en 127.0.0.1:8000 (reinicia si cae)
#   .\scripts\serve_backend.ps1 -Register    # registra la tarea programada «ValerIA-Backend»
# Lee el .env del proyecto (DEEPSEEK_API_KEY, VALERIA_CHANNEL_TOKEN, VALERIA_CHANNEL_SALT, QDRANT_URL…).
param([switch]$Register, [int]$Port = 8000)

$ErrorActionPreference = "Stop"
$Repo = Split-Path -Parent $PSScriptRoot

if ($Register) {
    $action = New-ScheduledTaskAction -Execute "powershell.exe" `
        -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$PSCommandPath`" -Port $Port" `
        -WorkingDirectory $Repo
    $trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
    $settings = New-ScheduledTaskSettingsSet -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) `
        -ExecutionTimeLimit ([TimeSpan]::Zero) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
    Register-ScheduledTask -TaskName "ValerIA-Backend" -Action $action -Trigger $trigger `
        -Settings $settings -Description "Backend FastAPI de Valer-IA Caña (spec 024)" -Force | Out-Null
    Write-Host "Tarea «ValerIA-Backend» registrada; se inicia al iniciar sesión."
    exit 0
}

Set-Location $Repo
if (-not $env:QDRANT_URL) { $env:QDRANT_URL = "http://127.0.0.1:6333" }
while ($true) {
    Write-Host "$(Get-Date -Format s) arrancando backend en 127.0.0.1:$Port"
    uv run uvicorn proyecto_modelos_lenguaje.api:app --host 127.0.0.1 --port $Port --env-file .env
    Write-Warning "$(Get-Date -Format s) el backend terminó (código $LASTEXITCODE); reinicio en 5 s"
    Start-Sleep -Seconds 5
}
