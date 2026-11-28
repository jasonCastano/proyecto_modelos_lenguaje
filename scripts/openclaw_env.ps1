# Entorno y servicio del gateway OpenClaw de Valer-IA (spec 024, T012; modos de acceso: spec 028, T036).
# Uso (PowerShell, en el PC servidor):  .\scripts\openclaw_env.ps1 [-Install] [-Restart] [-Mode open|closed]
#   -Install  registra la tarea programada "ValerIA-Gateway" (al iniciar sesion) y arranca el gateway;
#             aplica ademas el parche de cuentas por ID (spec 033, openclaw\patches\whatsapp-lid.mjs)
#             y el de stickers (spec 037, openclaw\patches\whatsapp-sticker.mjs)
#   -Restart  reinicia el gateway y espera a que escuche en el puerto
#   -Run      (lo usa la tarea) ejecuta el gateway en primer plano y lo reinicia si cae
#   -Mode     closed: solo los numeros de prueba (WA_ALLOW_1..3) responden
#             open:   cualquier numero (ensayo y sustentacion); guarda los de prueba en WA_TEST_1..3
#             Cambia solo el .env externo y reinicia el gateway; nunca toca archivos versionados.
# Los secretos y los numeros viven en $env:USERPROFILE\.openclaw-valeria\.env (nunca en Git).
#
# Por que una tarea propia (spec 028): OpenClaw 2026.11.10 solo instala su servicio con las rutas por
# defecto (~/.openclaw). Valer-IA usa su propio estado para no mezclarse con otra instalacion de
# OpenClaw del mismo usuario, asi que el gateway corre como tarea programada propia en el puerto 18790.
param(
    [switch]$Install,
    [switch]$Restart,
    [switch]$Run,
    [ValidateSet("open", "closed")][string]$Mode,
    [switch]$Force  # spec 031: cerrar sin numeros de prueba guardados sin pedir confirmacion
)
$TaskName = "ValerIA-Gateway"
$Port = 18790

$ErrorActionPreference = "Stop"
$Repo = Split-Path -Parent $PSScriptRoot
$State = Join-Path $env:USERPROFILE ".openclaw-valeria"
$EnvFile = Join-Path $State ".env"

# Spec 028: OpenClaw trabaja sobre una copia de la plantilla del repositorio, fuera de Git y con permisos
# solo del usuario (la auditoria marca como critico un archivo de configuracion escribible por otros, y
# OpenClaw reescribe el archivo cuando instala plugins).
$Template = Join-Path $Repo "openclaw\openclaw.json5"
$env:OPENCLAW_CONFIG_PATH = Join-Path $State "openclaw.json5"
$env:OPENCLAW_STATE_DIR = $State
if (-not $env:OPENCLAW_WORKSPACE_DIR) { $env:OPENCLAW_WORKSPACE_DIR = Join-Path $State "workspace" }
if (-not $env:VALERIA_REPO) { $env:VALERIA_REPO = $Repo }

# Persiste las rutas para el servicio (tarea programada) del usuario actual.
[Environment]::SetEnvironmentVariable("OPENCLAW_CONFIG_PATH", $env:OPENCLAW_CONFIG_PATH, "User")
[Environment]::SetEnvironmentVariable("OPENCLAW_STATE_DIR", $env:OPENCLAW_STATE_DIR, "User")
[Environment]::SetEnvironmentVariable("OPENCLAW_WORKSPACE_DIR", $env:OPENCLAW_WORKSPACE_DIR, "User")
[Environment]::SetEnvironmentVariable("VALERIA_REPO", $env:VALERIA_REPO, "User")

if (-not (Test-Path $EnvFile)) {
    Write-Warning "Falta $EnvFile : copia openclaw\.env.example y completa los valores."
}

Write-Host "OPENCLAW_CONFIG_PATH=$env:OPENCLAW_CONFIG_PATH"
Write-Host "OPENCLAW_STATE_DIR=$env:OPENCLAW_STATE_DIR"
Write-Host "OPENCLAW_WORKSPACE_DIR=$env:OPENCLAW_WORKSPACE_DIR"

function Get-EnvValue([string[]]$Lines, [string]$Key) {
    foreach ($line in $Lines) {
        if ($line -match "^\s*$Key\s*=(.*)$") { return $Matches[1].Trim() }
    }
    return ""
}

function Set-EnvValue([System.Collections.Generic.List[string]]$Lines, [string]$Key, [string]$Value) {
    for ($i = 0; $i -lt $Lines.Count; $i++) {
        if ($Lines[$i] -match "^\s*$Key\s*=") { $Lines[$i] = "$Key=$Value"; return }
    }
    $Lines.Add("$Key=$Value")
}

if ($Mode) {
    if (-not (Test-Path $EnvFile)) { throw "No existe $EnvFile; no se puede cambiar el modo." }
    $lines = [System.Collections.Generic.List[string]]::new()
    foreach ($line in (Get-Content -Path $EnvFile -Encoding UTF8)) { $lines.Add($line) }
    if ($Mode -eq "open") {
        if ((Get-EnvValue $lines "WA_ALLOW_1") -ne "*") {
            foreach ($n in 1..3) { Set-EnvValue $lines "WA_TEST_$n" (Get-EnvValue $lines "WA_ALLOW_$n") }
        }
        Set-EnvValue $lines "WA_DM_POLICY" "open"
        Set-EnvValue $lines "WA_ALLOW_1" "*"
        Set-EnvValue $lines "WA_ALLOW_2" ""
        Set-EnvValue $lines "WA_ALLOW_3" ""
    } else {
        $saved = Get-EnvValue $lines "WA_TEST_1"
        if ((Get-EnvValue $lines "WA_ALLOW_1") -eq "*" -and -not $saved) {
            Write-Warning "No hay numeros de prueba guardados (WA_TEST_1..3): el modo cerrado no admitira a nadie."
            if (-not $Force) {
                $answer = Read-Host "Escribe SI para cerrar el canal de todos modos"
                if ($answer -ne "SI") { Write-Host "Sin cambios: el canal sigue como estaba."; exit 1 }
            }
        }
        if ($saved) {
            foreach ($n in 1..3) { Set-EnvValue $lines "WA_ALLOW_$n" (Get-EnvValue $lines "WA_TEST_$n") }
        } elseif ((Get-EnvValue $lines "WA_ALLOW_1") -eq "*") {
            Set-EnvValue $lines "WA_ALLOW_1" ""
        }
        Set-EnvValue $lines "WA_DM_POLICY" "allowlist"
    }
    # UTF-8 sin BOM: el lector de .env de OpenClaw no debe ver un BOM antes de la primera clave.
    [System.IO.File]::WriteAllLines($EnvFile, $lines, (New-Object System.Text.UTF8Encoding $false))
    $allowed = @(1..3 | ForEach-Object { Get-EnvValue $lines "WA_ALLOW_$_" } | Where-Object { $_ })
    if ($Mode -eq "open") {
        Write-Host "Modo ABIERTO: cualquier numero puede escribirle a Valer-IA (grupos deshabilitados)."
        Write-Host "Espera ~2 min a que el gateway escuche WhatsApp antes de probar."
        Write-Host "Los limites por numero y el bloqueo los aplica el backend (VALERIA_OPERATORS sin limites)."
        Write-Warning "Cierralo al terminar el proyecto: .\scripts\openclaw_env.ps1 -Mode closed"
    } else {
        Write-Host "Modo CERRADO: responden solo $($allowed.Count) numero(s) de prueba."
    }
    $Restart = $true
}

$Entry = Join-Path $env:APPDATA "npm\node_modules\openclaw\openclaw.mjs"

function Test-GatewayPort {
    return [bool](Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
}

function Stop-ValeriaGateway {
    if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
        Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    }
    # El proceso node del gateway puede sobrevivir a la tarea: se detiene el que escucha en el puerto.
    Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 2
}

if ($Run) {
    if (-not (Test-Path $Entry)) { throw "No se encontro OpenClaw en $Entry (npm install -g openclaw)." }
    while ($true) {
        Write-Host "$(Get-Date -Format s) arrancando el gateway de Valer-IA en 127.0.0.1:$Port"
        & node $Entry gateway --port $Port
        Write-Warning "$(Get-Date -Format s) el gateway termino (codigo $LASTEXITCODE); reinicio en 5 s"
        Start-Sleep -Seconds 5
    }
}

function Sync-ValeriaConfig {
    # Copia la plantilla, restringe permisos (usuario actual y SYSTEM) y vuelve a enlazar el plugin.
    New-Item -ItemType Directory -Force $State | Out-Null
    Copy-Item $Template $env:OPENCLAW_CONFIG_PATH -Force
    $me = "$env:USERDOMAIN\$env:USERNAME"
    & icacls.exe $env:OPENCLAW_CONFIG_PATH /inheritance:r /grant:r "${me}:F" /grant:r "*S-1-5-18:F" | Out-Null
    & icacls.exe $EnvFile /inheritance:r /grant:r "${me}:F" /grant:r "*S-1-5-18:F" | Out-Null
    # Plugin propio: se aceptan sus permisos (lee la conversacion para enviarla al backend por loopback).
    openclaw plugins install --link (Join-Path $Repo "openclaw\plugins\valeria-bridge") --force `
        --accept-capabilities
    # Spec 033 (ADR 0038): parche versionado del componente de WhatsApp para cuentas identificadas solo
    # por ID (LID). Es idempotente y no adivina: si no puede aplicarse, avisa y el canal sigue igual
    # para las cuentas con numero.
    $patch = Join-Path $Repo "openclaw\patches\whatsapp-lid.mjs"
    $patchOutput = & node $patch --state-dir $State 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Warning ("Parche de cuentas por ID no aplicado: " + ($patchOutput -join " "))
    } else {
        Write-Host ($patchOutput -join " ")
    }
    # Spec 037 (ADR 0039): parche de stickers nativos (el listener expone sendSticker y los valeria-*.webp
    # salen como sticker por el adaptador de salida). Sin el, no hay stickers; el texto llega igual.
    $stickerPatch = Join-Path $Repo "openclaw\patches\whatsapp-sticker.mjs"
    $stickerOutput = & node $stickerPatch --state-dir $State 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Warning ("Parche de stickers no aplicado: " + ($stickerOutput -join " "))
    } else {
        Write-Host ($stickerOutput -join " ")
    }
    Write-Host "Configuracion de ejecucion: $env:OPENCLAW_CONFIG_PATH (plantilla: $Template)"
}

if ($Install) {
    Sync-ValeriaConfig
    $action = New-ScheduledTaskAction -Execute "powershell.exe" `
        -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$PSCommandPath`" -Run" `
        -WorkingDirectory $Repo
    $trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
    $settings = New-ScheduledTaskSettingsSet -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) `
        -ExecutionTimeLimit ([TimeSpan]::Zero) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings `
        -Description "Gateway OpenClaw de Valer-IA (spec 028, puerto $Port)" -Force | Out-Null
    Write-Host "Tarea $TaskName registrada; arranca al iniciar sesion."
}
if ($Install -or $Restart) {
    Stop-ValeriaGateway
    Start-ScheduledTask -TaskName $TaskName
    $listening = $false
    foreach ($i in 1..45) {
        Start-Sleep -Seconds 2
        if (Test-GatewayPort) { $listening = $true; break }
    }
    if ($listening) {
        Write-Host "Gateway de Valer-IA escuchando en 127.0.0.1:$Port."
    } else {
        Write-Warning "El gateway no escucha en el puerto $Port despues de 90 s. Revisa: Get-ScheduledTask $TaskName"
    }
    if ($Mode) { openclaw channels status }
}
