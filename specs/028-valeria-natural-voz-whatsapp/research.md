# Research: Valer-IA natural y con voz por WhatsApp (spec 028)

Fuentes verificadas el 2026-11-26 en este portátil: tipos del SDK de OpenClaw 2026.11.6
(`dist/config-contracts-*.d.ts`, `types-*.d.ts`), documentación instalada (`docs/channels/whatsapp.md`,
`docs/nodes/audio.md`, `docs/tools/tts/*.md`, `docs/concepts/queue-steering.md`), catálogo de Phonon
(`ptts.catalog_voices()`) y el código del canal de la spec 024.

## R1. Prueba técnica previa (primera tarea de implementación)

- **Decision**: antes de escribir el código de voz se corre una prueba de ≤ 2 h en el gateway real que confirma
  cinco hechos. Cada uno tiene criterio de éxito y salida alternativa ya decidida:

  | # | Hecho a confirmar | Éxito | Si falla |
  |---|---|---|---|
  | S1 | Con `tools.media.audio` activo, `before_dispatch` recibe en `content` un bloque `[Audio]` con la transcripción | El plugin ve el texto transcrito | El plugin recibe `<media:audio>`; se activa `pluginHooks.messageReceived` para obtener la ruta del adjunto y se transcribe en el backend |
  | S2 | El plugin puede enviar un audio al remitente desde el hook (`api.runtime.gateway.request("send", …)` con `media`) y WhatsApp lo muestra como nota de voz | Llega una nota de voz PTT | `openclaw message send --channel whatsapp --target <senderId> --media <ruta>` desde el plugin (`child_process`, CLI documentado) |
  | S3 | El modelo `phonon-31m-en` descarga y sintetiza en este equipo | WAV en inglés < 5 s para 300 caracteres | Voz inglesa de OpenClaw (`microsoft`, sin clave) generada por la ruta Auto-TTS solo para inglés |
  | S4 | PyAV codifica Ogg/Opus 48 kHz mono | Archivo `.ogg` válido | Se envía WAV y OpenClaw lo transcodifica con `ffmpeg` (documentado para WhatsApp) |
  | S5 | `dmPolicy: "${WA_DM_POLICY}"` y `allowFrom` con `"*"` desde variables pasan la validación estricta | `openclaw doctor` sin errores con `open` y con `allowlist` | Dos archivos de configuración versionados (`openclaw.json5` y `openclaw.open.json5`) y el script cambia `OPENCLAW_CONFIG_PATH` |

- **Rationale**: los tipos verificados muestran que `before_dispatch` solo transporta texto
  (`PluginHookBeforeDispatchEvent.content`, resultado `{handled, text}`); la transcripción de OpenClaw
  reemplaza `Body` por un bloque `[Audio]` antes del despacho, y WhatsApp envía todo audio saliente como PTT
  (`ptt: true`, transcodifica con `ffmpeg` lo que no sea Ogg/Opus). Falta verlo con el gateway vivo.
- **Alternatives considered**: implementar sin prueba (riesgo de descubrir el sábado que no hay voz); usar solo
  Auto-TTS (R2).

## R2. Ruta de la voz saliente: el backend genera el audio, el plugin lo envía

- **Decision**: ruta B. El backend produce el guion, sintetiza y deja un Ogg/Opus temporal; la respuesta del
  canal trae `voice.audio_path`; el plugin envía la nota de voz (S2) y luego devuelve el texto como resultado
  del hook.
- **Rationale**: la spec exige que la voz sea un guion conversacional distinto del texto con citas (FR-003). La
  ruta A (Auto-TTS `tts.auto: "inbound"`) sintetiza el texto de la respuesta: leería las citas y el bloque de
  fuentes, y además no está garantizado que se aplique a respuestas de un plugin (la documentación excluye las
  respuestas de comandos de plugin). Con la ruta B el backend controla idioma, guion y voz, y la prueba se hace
  sin red con motores simulados.
- **Alternatives considered**: ruta A con un CLI que limpie el texto (sigue siendo lectura del texto, no un
  guion); que el backend envíe el audio por su cuenta (no conoce el número: solo el seudónimo).

## R3. Guion hablado conversacional

- **Decision**: nuevo prompt versionado `prompts/voice_script.md` (1.0). Entrada: pregunta, respuesta citada e
  idioma. Salida: 40–110 palabras (≈ 20–55 s), segunda persona, sin etiquetas de cita, URLs, listas ni
  «fuentes», cifras dichas como se hablan, cierre breve que invite a seguir; prohibido añadir hechos. Se llama
  con el mismo modelo del agente (temperatura baja). Después pasa por `voice.text.clean_for_speech` (quita
  citas, Markdown y URLs que se cuelen). Respaldo determinista si el modelo falla: primeras oraciones limpias de
  la respuesta hasta 600 caracteres. En modo demo, el modelo guionado produce un guion fijo.
- **Rationale**: «natural, no robótica» (D5.1) pide reescribir, no recortar. Una llamada extra (~2–3 s) solo en
  turnos con voz. La verificación «no añade hechos» se prueba con números: toda cifra del guion debe estar en la
  respuesta.
- **Alternatives considered**: pedir el guion en la misma llamada del agente (cambia el contrato del grafo y
  arriesga las citas); solo `clean_for_speech` (lee la respuesta completa, no suena conversacional).

## R4. Voz en español e inglés con Phonon

- **Decision**: `VoiceService` pasa de un modelo a uno por idioma: `es` → `phonon-40m-es`, voz «Rebeca» (sin
  cambio); `en` → `hf://gradium/phonon-31m-en` (modelo por defecto de `ptts`), voz femenina elegida en la
  prueba S3 entre `Harper`, `Everly` y `Juniper`. Carga perezosa del inglés y precalentamiento opcional cuando
  `channels.voice_notes = true`. Se registra la licencia (CC BY-NC 4.0) en la ficha de voz.
- **Rationale**: el catálogo local de Phonon tiene 37 voces en inglés y 25 en español; mantiene todo local y sin
  claves. El modelo en inglés es más pequeño (31 M) que el español.
- **Alternatives considered**: voz Microsoft de OpenClaw (necesita internet y la ruta Auto-TTS; queda como
  respaldo de S3); voz española leyendo inglés (pronunciación incorrecta).

## R5. Transcripción y detección de idioma

- **Decision**: OpenClaw transcribe con `tools.media.audio` y una entrada `type: "cli"` que ejecuta
  `uv run --project <repo> python -m proyecto_modelos_lenguaje.channels.transcribe_cli {{AttachmentPath}}`.
  El CLI es un cliente delgado: envía el archivo a `POST /api/channels/transcriptions` (loopback + token), donde
  el servicio de dictado de la spec 023 ya está cargado; si el backend no responde, transcribe en proceso. El
  canal usa idioma automático (`language="auto"` → faster-whisper detecta; solo se aceptan `es` y `en`, otro
  idioma se trata como español con aviso). La transcripción sale por stdout; el idioma lo infiere el backend
  sobre el texto (`agent.plan.detect_language`) y, si existe, la pista del endpoint.
- **Rationale**: reutiliza el modelo cargado (sin 5–10 s de arranque por audio), decodifica Ogg/Opus con PyAV
  (`faster_whisper.decode_audio`), y el texto llega al puente por el camino normal del hook.
- **Alternatives considered**: `whisper` (CLI de Python) autodetectado por OpenClaw (otra dependencia y modelo
  distinto del evaluado en la spec 023); proveedor en la nube (claves y costo).

## R6. Conversación sin comandos

- **Decision**: un módulo `channels/intents.py` con léxico determinista en español e inglés, probado con un
  guion de conversación natural:
  - **Empezar de nuevo**: «empecemos de nuevo», «nueva conversación», «borrón y cuenta nueva», «start over»… →
    hilo nuevo con respuesta natural.
  - **Formato**: «respóndeme por escrito», «sin audios», «text me» → `text`; «mándame audio», «respóndeme con
    voz», «send me a voice note» → `voice`; por defecto `auto` (igual que la pregunta).
  - **Confirmaciones**: frases de hasta 8 palabras con afirmación («sí», «dale», «hágale», «de una», «claro»,
    «adelante», «guárdalo», «yes», «go ahead», «sure») o negación («no», «mejor no», «déjalo así», «olvídalo»,
    «cancela», «no thanks»). Si mezcla ambas o no tiene ninguna → ambigua.
  - **Ambigüedad con acción pendiente**: si el mensaje parece una pregunta nueva («?» o ≥ 6 palabras sin
    afirmación/negación) se cancela la acción con un aviso natural y se responde la pregunta; si es corto y
    ambiguo, se vuelve a preguntar en una frase. Nunca se ejecuta sin afirmación clara.
  - **Olvidar, perfil y capacidades**: los resuelve el agente por contexto (herramienta `forget_memory` con
    confirmación, disparadores de perfil, presentación en el prompt 1.8).
  - Todos los textos del canal se reescriben sin comandos; una prueba recorre las constantes y respuestas del
    guion y falla si aparece `/` seguido de una palabra. Los comandos siguen funcionando como atajos ocultos.
- **Rationale**: lo determinista es rápido, sin costo y comprobable; las intenciones abiertas (olvidar, perfil)
  ya las resuelve el agente y no conviene duplicarlas.
- **Alternatives considered**: clasificar todo con el modelo (latencia y no determinismo en confirmaciones,
  justo donde importa la seguridad); mantener «Responde *SÍ* o *NO*» (es una instrucción de comando).

## R7. Cola por usuario sin perder mensajes

- **Decision**: el candado por usuario espera (hasta `queue_wait_seconds = 60`) en lugar de responder «busy»; el
  timeout del puente sube a 90 s (`bridge_timeout_seconds`, `timeoutMs` del plugin) y se enmienda la regla 12.
  La prueba S1 registra además si OpenClaw ya serializa los despachos de una misma conversación.
- **Rationale**: FR-018 exige atender todo en orden y sin límite. Con 20 invitados y respuestas de ~10–20 s,
  60 s de espera cubren dos mensajes encadenados.
- **Alternatives considered**: cola persistente con respuesta diferida (el hook no puede responder más tarde);
  responder «busy» (pierde el mensaje).

## R8. Modo abierto y cerrado sin tocar archivos versionados

- **Decision**: `openclaw.json5` lee `dmPolicy: "${WA_DM_POLICY}"` y `allowFrom` desde `WA_ALLOW_*`. El
  script `scripts/openclaw_env.ps1 -Mode open|closed` escribe en el `.env` externo `WA_DM_POLICY=open` +
  `WA_ALLOW_1=*` (abierto) o `allowlist` + números de prueba (cerrado) y reinicia el gateway. `groupPolicy`
  sigue `disabled` y `selfChatMode: false`. Respaldo si S5 falla: dos archivos de configuración versionados.
- **Rationale**: FR-016 pide operarlo sin cambiar el código y sin escribir números en Git; `openclaw config set`
  escribiría sobre el archivo versionado.
- **Alternatives considered**: `pairing` (exige aprobar cada invitado); editar a mano (propenso a error el
  sábado temprano).

## R9. Planificador abierto y activado por contexto

- **Decision**: `config/profiles.toml` → `planificador.requires_authorization = false` (web y WhatsApp; el
  código de autorización queda inactivo). En el router, `planning_decision` deja de exigir el perfil: activa la
  ruta `planning` si `is_planning_request(mensaje)` o si el turno anterior del hilo fue `planning` y el mensaje
  es una repregunta del escenario (elíptica: «¿y si…?», «¿y con…?», «what if…», un porcentaje o cifra sin tema
  nuevo). El grafo aplica el foco y las herramientas del planificador solo a ese turno; el perfil del hilo no
  cambia. `PLANNING_CUE` se ajusta para no disparar con usos informativos («programas sociales con cultivadores
  de caña», «¿cuánta caña molió en 2022?»). Conjunto fijado antes de medir: 15 consultas de planificación y 15
  parecidas (`tests/fixtures/agent/planning_activation.jsonl`) con meta ≥ 14/15 en cada lado.
- **Rationale**: D3 pide la misma experiencia que la web y sin comandos; activarlo por turno evita que un falso
  positivo deje al visitante «atrapado» en planificación.
- **Alternatives considered**: perfil pegajoso (más natural en repreguntas, pero peor ante falsos positivos);
  clasificador con el modelo (más costo y menos predecible para la demo).
- **Impacto en la web**: el grafo es compartido; la activación automática aplica también en la web. Se informa
  a Roberto (responsable de la web) antes del merge.

## R10. MCP de 15 herramientas y nueva medición

- **Decision**: `mcp_allowed=False` en `get_plant_state`, `get_commitments` y `search_operating_procedures`;
  prueba que fija 15 herramientas y actualización de `openclaw/workspace/AGENTS.md`. La medición de exactitud se
  corre sobre las 43 consultas (20 herramientas de atención) en modo real después de los cambios de router y
  prompt; si baja de 88,4 % (regla 21) se corrige antes del merge y se documenta el análisis. Discurso: «20 de
  atención + 6 de planificación = 26».
- **Rationale**: D1 (a) y D2 (a); el modo degradado no puede simular ni optimizar.
- **Alternatives considered**: medir 26 herramientas (exige consultas nuevas del planificador y más tiempo).

## R12. Operar sin Docker (el portátil no permite virtualización)

- **Hallazgo (2026-11-26)**: el i9-12900H soporta VT-x, pero está deshabilitado en el firmware
  (`VirtualizationFirmwareEnabled: False`, `HypervisorPresent: False`); Docker Desktop no arranca. En el
  repositorio Docker solo se usa para (a) Qdrant servidor (`docker-compose.yml`, `make qdrant-up`) y (b) el
  sandbox del agente nativo de OpenClaw (`sandbox.backend: "docker"`).
- **Decision (a) Qdrant**: binario nativo de Windows de Qdrant (misma versión que la imagen validada,
  v1.15.4, publicado en las *releases* oficiales de GitHub), escuchando solo en `127.0.0.1:6333`, con su
  almacenamiento en `%USERPROFILE%\.qdrant-valeria\storage` y registrado como tarea programada
  «ValerIA-Qdrant». Es un servidor real con índice HNSW y filtros por *payload*: la rúbrica 2.2 se cumple igual
  (`vectorstore.py` ya acepta «Docker o binario» vía `QDRANT_URL`). `make qdrant-up` queda para quien tenga
  Docker.
- **Decision (b) sandbox**: `sandbox.mode: "off"` con controles compensatorios que ya existen o se refuerzan:
  el agente nativo solo actúa en modo degradado; `exec` denegado (`security: "deny"`), `elevated` deshabilitado,
  `fs.workspaceOnly`, `tools.deny` con los grupos `runtime`, `fs`, `automation`, navegador, web y mensajería
  (solo queda el MCP de solo lectura `valeria-tools`), grupos de WhatsApp deshabilitados. Se documenta como
  riesgo aceptado en la ADR 0037 y en la auditoría. La auditoría `openclaw security audit --deep` debe quedar
  sin hallazgos críticos; si marca el sandbox apagado como crítico, se ajusta la política de herramientas hasta
  cumplirlo o se documenta la excepción.
- **Rationale**: no depende de cambiar el firmware de un equipo corporativo; mantiene todo en un solo portátil;
  el riesgo real del sandbox es bajo porque el agente nativo no puede ejecutar comandos ni escribir archivos.
- **Alternatives considered**: activar VT-x en el firmware (Lenovo: F1 al encender → Security →
  Virtualization → Intel VT-x; viable solo si el equipo no tiene la BIOS bloqueada por TI; si se logra, vuelve el
  plan original); backends de sandbox `ssh`/`openshell`/`crabbox` (requieren otra máquina o un servicio en la
  nube); Podman (también necesita virtualización); servidor en el PC de Roberto (contradice «todo en este
  equipo»).

## R11. Audio temporal y privacidad

- **Decision**: los Ogg/Opus generados se escriben en `$MANUELITA_STATE_DIR/channels/voice/<uuid>.ogg` (fuera
  del repositorio) y se borran a los 10 minutos o al arrancar; el audio entrante lo maneja OpenClaw en su
  directorio de estado y el endpoint de transcripción lo procesa en memoria (spec 023). Los registros guardan
  solo `input_mode`, idioma, duración y latencias, nunca texto ni audio.
- **Rationale**: FR-008 y regla 10.
- **Alternatives considered**: enviar el audio en base64 dentro de la respuesta HTTP (el plugin tendría que
  escribirlo a disco de todos modos para `--media`).
