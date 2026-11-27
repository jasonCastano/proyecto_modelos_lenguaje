# Contrato operativo: instrucciones paso a paso para OpenClaw (spec 028)

Regla del equipo: **cada paso manual se entrega aquí antes de ejecutarse**. Se ejecutan en PowerShell desde la
raíz del repositorio. Nunca se pegan en el chat ni se versionan claves, tokens ni números de teléfono.

Prerrequisito: la **Fase A** de la spec 024 **sin Docker** (`ffmpeg`, energía, OpenClaw actualizado, `.env`
externo, variables, workspace, plugin enlazado, backend y gateway como servicios). Este portátil no permite
virtualización (research R12): Qdrant corre como binario nativo (O0) y el sandbox de OpenClaw queda apagado con
controles compensatorios.

## O0. Qdrant nativo, sin Docker

1. Si Docker Desktop quedó instalado y no arranca, desinstálalo para que no intente iniciar con Windows:
   `winget uninstall -e --id Docker.DockerDesktop`.
2. `.\scripts\qdrant_native.ps1 -Install` → descarga Qdrant v1.15.4 para Windows desde las *releases* oficiales
   de GitHub a `%USERPROFILE%\.qdrant-valeria\`, verifica el archivo y crea la configuración (solo
   `127.0.0.1`, almacenamiento en `%USERPROFILE%\.qdrant-valeria\storage`).
3. `.\scripts\qdrant_native.ps1 -Register` → tarea programada «ValerIA-Qdrant» que lo arranca al iniciar sesión,
   y lo inicia ahora. Si Windows pregunta por el firewall, elige **cancelar/no permitir**: solo escucha en
   loopback y no necesita acceso de red.
4. `.\scripts\qdrant_native.ps1 -Status` → debe responder la versión 1.15.4.
5. En el `.env` del proyecto y en `%USERPROFILE%\.openclaw-valeria\.env`: `QDRANT_URL=http://127.0.0.1:6333`.
6. `uv run python -m proyecto_modelos_lenguaje.rag qdrant build --force` y luego
   `uv run python -m proyecto_modelos_lenguaje.rag qdrant status` → modo servidor, HNSW `m=16`.
7. Reiniciar el backend: `Stop-ScheduledTask ValerIA-Backend; Start-ScheduledTask ValerIA-Backend`.

## O1. Vincular la SIM dedicada

1. En el teléfono con la SIM nueva, instalar WhatsApp (o WhatsApp Business) y activarlo con ese número.
2. En el portátil: `openclaw channels login --channel whatsapp` (muestra un QR).
3. En ese teléfono: WhatsApp → Ajustes → **Dispositivos vinculados** → **Vincular un dispositivo** → escanear.
4. `openclaw channels status --probe` debe mostrar WhatsApp vinculado.
5. `openclaw gateway restart --wait 30s`.
6. Mantener el teléfono de la SIM cargado y con datos o wifi hasta el sábado (WhatsApp desvincula dispositivos
   si el teléfono principal pasa ~14 días sin conectarse; no aplica a esta ventana, pero conviene).

## O2. Prueba técnica de voz (T013, research R1)

Requisitos: Fase A completa, gateway con la configuración de esta rama (`tools.media.audio` y sandbox
apagado), SIM vinculada (O1) y un teléfono de prueba incluido en `WA_ALLOW_*`. Resultados ya confirmados sin
teléfono (2026-11-26): **S4** PyAV codifica y decodifica Ogg/Opus en este portátil; **S5** `openclaw config
validate` acepta `dmPolicy` por variable en modo `allowlist` y en modo `open` con `"*"`.

**S1 — la transcripción llega al puente**

1. En el `.env` externo (`%USERPROFILE%\.openclaw-valeria\.env`) añade temporalmente
   `VALERIA_BRIDGE_DEBUG=1` (el plugin registra los primeros 80 caracteres del contenido recibido).
2. `.\scripts\openclaw_env.ps1 -Restart`.
3. Desde el teléfono de prueba, envía al número de Valer-IA una nota de voz: «¿Qué produce Manuelita?».
4. `openclaw logs --limit 80 | Select-String "valeria-bridge"` → busca la línea `contenido recibido:`.
   - **Éxito**: muestra `[Audio]` seguido de la transcripción.
   - **Si muestra `<media:audio>`**: la transcripción no corrió; revisa `openclaw logs --limit 80 | Select-String
     "media|audio|transcri"` y pégame esas líneas (sin números).
5. Quita `VALERIA_BRIDGE_DEBUG=1` del `.env` y reinicia (`-Restart`): el registro no debe guardar contenido.

**S2 — el gateway envía una nota de voz**

1. `uv run python -m proyecto_modelos_lenguaje.voice --say "Hola, soy Valeria. Esta es una prueba de voz." -o "$env:TEMP\prueba-voz.wav"`
2. `openclaw message send --channel whatsapp --target <TU_NÚMERO_DE_PRUEBA> --media "$env:TEMP\prueba-voz.wav"`
   (escribe el número solo en tu terminal, nunca en el chat ni en un archivo).
3. **Éxito**: en el teléfono llega una **nota de voz** (burbuja con onda), no un archivo adjunto.
4. `Remove-Item "$env:TEMP\prueba-voz.wav"`.

**S3 — voz en inglés**

1. `uv run python -m proyecto_modelos_lenguaje.voice --check --language en` (la primera vez descarga el modelo
   `phonon-31m-en`; si falla por permisos, acepta las condiciones en Hugging Face, paso 6 de la Fase A).
2. Escucha `--say "Hi, I'm Valeria, Manuelita's virtual assistant." --language en --voice Harper -o en.wav`
   y repite con `--voice Everly` y `--voice Juniper`; dime cuál prefieres.

Anota en el chat: S1 (qué apareció), S2 (nota de voz sí/no), S3 (voz elegida y si descargó).

## O3. Modo cerrado (por defecto, pruebas del equipo)

1. `.\scripts\openclaw_env.ps1 -Mode closed` → escribe en `%USERPROFILE%\.openclaw-valeria\.env`
   `WA_DM_POLICY=allowlist` y conserva `WA_ALLOW_1..3` (números de prueba que tú escribes en ese archivo).
2. El script reinicia el gateway y muestra `openclaw channels status`.
3. Verificar: un teléfono fuera de la lista no recibe respuesta.

## O4. Modo abierto (ensayo del viernes por la tarde y sábado)

1. `.\scripts\openclaw_env.ps1 -Mode open` → `WA_DM_POLICY=open`, `WA_ALLOW_1=*` (guarda los números de prueba
   en `WA_TEST_*` para restaurarlos).
2. El script reinicia el gateway y ejecuta `openclaw doctor`.
3. Verificar: un teléfono que nunca escribió recibe respuesta a «hola».

## O5. Cierre después de la sustentación

1. `.\scripts\openclaw_env.ps1 -Mode closed`.
2. `openclaw channels logout --channel whatsapp` (desvincula el número).
3. En el teléfono de la SIM: Ajustes → Dispositivos vinculados → cerrar la sesión del portátil; luego eliminar
   la cuenta de WhatsApp y desactivar la SIM.
4. Opcional: `Unregister-ScheduledTask ValerIA-Backend` y `openclaw gateway uninstall` si el portátil deja de
   ser servidor.

## O6. Verificación del sábado (6:30–8:00)

1. `uv run pml ops check` en verde.
2. `.\scripts\openclaw_env.ps1 -Mode open`.
3. Desde un teléfono ajeno: «hola» (texto) y una nota de voz en español y otra en inglés.
4. Revisar `openclaw logs --limit 50` sin errores.
