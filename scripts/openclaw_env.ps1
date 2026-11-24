# Entorno y servicio del gateway OpenClaw de Valer-IA (spec 024, T012).
# Uso (PowerShell, en el PC servidor):  .\scripts\openclaw_env.ps1 [-Install] [-Restart]
#   -Install  reinstala el servicio con la configuración del repositorio
#   -Restart  reinicia el gateway y espera a que quede listo
# Los secretos viven en $env:USERPROFILE\.openclaw-valeria\.env (nunca en Git).
param([switch]$Install, [switch]$Restart)

$ErrorActionPreference = "Stop"
$Repo = Split-Path -Parent $PSScriptRoot
$State = Join-Path $env:USERPROFILE ".openclaw-valeria"

$env:OPENCLAW_CONFIG_PATH = Join-Path $Repo "openclaw\openclaw.json5"
$env:OPENCLAW_STATE_DIR = $State
if (-not $env:OPENCLAW_WORKSPACE_DIR) { $env:OPENCLAW_WORKSPACE_DIR = Join-Path $State "workspace" }
if (-not $env:VALERIA_REPO) { $env:VALERIA_REPO = $Repo }

# Persiste las rutas para el servicio (tarea programada) del usuario actual.
[Environment]::SetEnvironmentVariable("OPENCLAW_CONFIG_PATH", $env:OPENCLAW_CONFIG_PATH, "User")
[Environment]::SetEnvironmentVariable("OPENCLAW_STATE_DIR", $env:OPENCLAW_STATE_DIR, "User")
[Environment]::SetEnvironmentVariable("OPENCLAW_WORKSPACE_DIR", $env:OPENCLAW_WORKSPACE_DIR, "User")
[Environment]::SetEnvironmentVariable("VALERIA_REPO", $env:VALERIA_REPO, "User")

if (-not (Test-Path (Join-Path $State ".env"))) {
    Write-Warning "Falta $State\.env: copia openclaw\.env.example y completa los valores."
}

Write-Host "OPENCLAW_CONFIG_PATH=$env:OPENCLAW_CONFIG_PATH"
Write-Host "OPENCLAW_STATE_DIR=$env:OPENCLAW_STATE_DIR"
Write-Host "OPENCLAW_WORKSPACE_DIR=$env:OPENCLAW_WORKSPACE_DIR"

if ($Install) {
    openclaw gateway install --force
}
if ($Install -or $Restart) {
    openclaw gateway restart --wait 30s
    openclaw gateway status
}
