# Qdrant servidor sin Docker para el portatil servidor (spec 028, research R12, T002).
# El portatil no permite virtualizacion: Qdrant corre como binario nativo de Windows, solo en
# loopback, con almacenamiento fuera del repositorio. Es el mismo servidor (HNSW, filtros por
# payload) que la imagen qdrant/qdrant:v1.15.4 de docker-compose.yml.
#
# Uso:
#   .\scripts\qdrant_native.ps1 -Install    # descarga v1.15.4, verifica SHA-256 y crea el lanzador
#   .\scripts\qdrant_native.ps1 -Register   # tarea programada "ValerIA-Qdrant" (al iniciar sesion) y la inicia
#   .\scripts\qdrant_native.ps1 -Status     # consulta http://127.0.0.1:6333/
#   .\scripts\qdrant_native.ps1             # ejecuta Qdrant en primer plano (lo usa la tarea)
param([switch]$Install, [switch]$Register, [switch]$Status)

$ErrorActionPreference = "Stop"
$Version = "v1.15.4"
$Asset = "qdrant-x86_64-pc-windows-msvc.zip"
# Digest publicado por GitHub para el asset de la release oficial (api.github.com, campo "digest").
$Sha256 = "5348af719d5d9f3658597c8d3a8231bb8c38e7139a8076b69bd3dd59151d06d5"
$Url = "https://github.com/qdrant/qdrant/releases/download/$Version/$Asset"
$Home_ = Join-Path $env:USERPROFILE ".qdrant-valeria"
$Storage = Join-Path $Home_ "storage"
$Launcher = Join-Path $Home_ "start-qdrant.cmd"
$Endpoint = "http://127.0.0.1:6333/"

function Find-QdrantExe {
    Get-ChildItem $Home_ -Filter qdrant.exe -Recurse -ErrorAction SilentlyContinue |
        Select-Object -First 1 -ExpandProperty FullName
}

if ($Install) {
    New-Item -ItemType Directory -Force $Storage | Out-Null
    $zip = Join-Path $Home_ $Asset
    Write-Host "Descargando Qdrant $Version ..."
    Invoke-WebRequest $Url -OutFile $zip -UseBasicParsing
    $actual = (Get-FileHash $zip -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $Sha256) {
        Remove-Item $zip -Force
        throw "El SHA-256 del archivo descargado no coincide con el publicado; no se instala."
    }
    Expand-Archive $zip -DestinationPath $Home_ -Force
    Remove-Item $zip -Force
    $exe = Find-QdrantExe
    if (-not $exe) { throw "No se encontro qdrant.exe despues de descomprimir." }
    # Solo loopback, almacenamiento propio y sin telemetria.
    $cmd = @(
        "@echo off",
        "set QDRANT__SERVICE__HOST=127.0.0.1",
        "set QDRANT__STORAGE__STORAGE_PATH=$Storage",
        "set QDRANT__TELEMETRY_DISABLED=true",
        "cd /d `"$Home_`"",
        "`"$exe`""
    )
    Set-Content -Path $Launcher -Value $cmd -Encoding ascii
    Write-Host "Qdrant $Version instalado en $Home_ (lanzador: $Launcher)."
    exit 0
}

if ($Register) {
    if (-not (Test-Path $Launcher)) { throw "Primero ejecuta: .\scripts\qdrant_native.ps1 -Install" }
    # Ventana oculta (spec 028): cerrar la ventana por error detenia Qdrant (0xC000013A).
    $action = New-ScheduledTaskAction -Execute "powershell.exe" `
        -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$PSCommandPath`"" `
        -WorkingDirectory $Home_
    $trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
    $settings = New-ScheduledTaskSettingsSet -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) `
        -ExecutionTimeLimit ([TimeSpan]::Zero) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
    Register-ScheduledTask -TaskName "ValerIA-Qdrant" -Action $action -Trigger $trigger `
        -Settings $settings -Description "Qdrant nativo de Valer-IA (spec 028, sin Docker)" -Force | Out-Null
    Start-ScheduledTask -TaskName "ValerIA-Qdrant"
    Write-Host "Tarea ValerIA-Qdrant registrada e iniciada; arranca al iniciar sesion."
    exit 0
}

if ($Status) {
    try {
        $info = Invoke-RestMethod $Endpoint -TimeoutSec 5
        Write-Host "Qdrant responde en $Endpoint (version $($info.version))."
        exit 0
    } catch {
        Write-Warning "Qdrant no responde en $Endpoint. Revisa: Get-ScheduledTask ValerIA-Qdrant"
        exit 1
    }
}

if (-not (Test-Path $Launcher)) { throw "Primero ejecuta: .\scripts\qdrant_native.ps1 -Install" }
& cmd.exe /c "`"$Launcher`""
