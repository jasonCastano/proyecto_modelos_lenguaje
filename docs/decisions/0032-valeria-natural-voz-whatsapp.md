# ADR 0032 — Valer-IA natural y con voz por WhatsApp, abierta el día de la sustentación

- **Estado**: propuesta (requiere la aprobación de ambos integrantes, constitución §11)
- **Fecha**: 2026-11-26
- **Autor**: Jason Alejandro Castaño
- **Relacionadas**:
  - ADR 0028 (OpenClaw con un solo agente y plugin puente);
  - ADR 0029 (plataforma de agentes y planificador);
  - ADR 0031 (perfiles abiertos en la web; autorización por canal);
  - `specs/028-valeria-natural-voz-whatsapp/` (spec, plan, research R1–R12, contratos, tareas).

## Contexto

La sustentación del Módulo 3 (sábado 28 de noviembre de 2026) se hace con el teléfono de un invitado. Con la
spec 024, el canal exigía comandos (`/ayuda`, `/nuevo`, `/olvidar`, `/traza`, `/perfil`) y confirmaciones «SÍ/NO»,
solo leía texto, usaba el número personal de un integrante con lista de autorizados y emparejamiento, y el
planificador solo existía para números autorizados (ADR 0031). Además, el portátil que hace de servidor no
permite virtualización (firmware con VT-x deshabilitado y BIOS de un equipo de trabajo), así que Docker no arranca.

El equipo decidió que la experiencia sea la de hablar con una persona: sin comandos, con voz cuando el invitado
habla, en su idioma, y abierta a cualquiera el día de la prueba.

## Decisión

1. **Conversación sin comandos**. Las intenciones del canal se reconocen con un léxico determinista en español e
   inglés (`channels/intents.py`): empezar de nuevo, responder por escrito o con voz, confirmar o rechazar una
   escritura. Una respuesta ambigua se vuelve a preguntar; una pregunta nueva cancela la acción pendiente con un
   aviso. Nunca se ejecuta una escritura sin una afirmación clara (la aprobación humana se conserva). Ningún texto
   sugiere comandos (`tests/unit/channels/test_no_commands.py`). Los comandos quedan como atajos ocultos del
   operador; `/traza` se usa en la discusión técnica.
2. **Notas de voz (ruta B)**. OpenClaw transcribe la nota de voz con nuestro dictado local (spec 023) mediante un
   CLI delgado (`channels/transcribe_cli.py` → `POST /api/channels/transcriptions`). El backend responde siempre por
   escrito con citas y fuentes y, si la pregunta llegó por voz (o la persona pidió audio), escribe un **guion
   conversacional** (`prompts/voice_script.md`, sin citas ni cifras nuevas, validado en código), lo sintetiza con
   Phonon en el idioma de la pregunta (español «Rebeca»; inglés `phonon-31m-en`) y deja un Ogg/Opus temporal. El
   plugin lo envía con `openclaw message send --media` y después entrega el texto. Se descartó la voz automática de
   OpenClaw (`tts.auto`) porque leería el texto con sus citas y no está garantizada para respuestas de un plugin.
3. **SIM dedicada y acceso abierto**. Valer-IA usa una SIM propia que se desactiva después de la sustentación.
   `dmPolicy` se lee de una variable: modo cerrado (`allowlist`, números de prueba) y modo abierto (`open` con
   `allowFrom: ["*"]`) solo en el ensayo y la jornada, sin límite de mensajes. Se cambia con
   `scripts/openclaw_env.ps1 -Mode open|closed`, que solo edita el `.env` externo. Grupos siempre desactivados.
4. **Planificador abierto y por contexto**. El perfil planificador deja de exigir autorización en todos los canales.
   El enrutador activa la ruta `planning` cuando el mensaje plantea un problema de producción o cuando es una
   repregunta de un turno de planificación, solo para ese turno y sin cambiar el perfil del hilo
   (15/15 y 15/15 en `docs/evaluacion_activacion_planificador.md`). **Esto también aplica en la web**: el grafo es
   compartido; se informa a Roberto, responsable de la web, en la descripción del PR.
5. **MCP de 15 herramientas**. Las lecturas de planificación salen del MCP: el modo degradado no puede simular ni
   optimizar, así que tampoco consulta la planta sintética.
6. **Cola por persona y timeout de 90 s**. Los mensajes de una misma persona esperan en orden (hasta 60 s); el
   plugin espera 90 s antes del modo degradado.
7. **Operación sin Docker**. Qdrant corre como binario nativo de Windows (v1.15.4, SHA-256 verificado, solo
   loopback, `scripts/qdrant_native.ps1`): es el mismo servidor HNSW. El sandbox de OpenClaw queda apagado y la
   protección pasa a la política: `tools.deny` retira al agente nativo todas sus herramientas propias
   (`group:openclaw`, `group:fs`, `group:runtime`, `group:ui`, `group:web`, `group:messaging`…), solo conserva el MCP
   de lectura, `exec` está denegado y `elevated` apagado.

## Consecuencias

- **Positivas**: un invitado cualquiera conversa sin preparación, por texto o voz, en español o inglés; la demo
  muestra el planificador sin cambiar de perfil; las citas se conservan en el texto aunque la voz no las lea.
- **Riesgo aceptado (sandbox)**: sin contenedor, si el agente nativo tuviera una herramienta peligrosa correría en
  el portátil. Se mitiga porque no tiene ninguna: solo el MCP de lectura, y solo actúa en modo degradado. La
  auditoría `openclaw security audit --deep` debe quedar sin hallazgos críticos o con la excepción documentada.
- **Riesgo aceptado (acceso abierto)**: cualquiera con el número puede escribir durante la ventana y consumir
  saldo del modelo; la SIM es dedicada, la ventana es corta y el número se desactiva después.
- **Costo**: una llamada extra al modelo por cada respuesta con voz (el guion); el resto es local.
- **Dependencias**: ninguna dependencia Python nueva; `ffmpeg` en el portátil (respaldo de transcodificación de
  OpenClaw) y el modelo de voz en inglés (CC BY-NC 4.0, como el español).
- **Reemplaza**: en la ADR 0028, el número de un integrante, `allowlist`+`pairing`, el sandbox Docker y el timeout de
  45 s; en la ADR 0031, la autorización del planificador en WhatsApp.
- Constitución: enmienda **MINOR 2.3.0** (reglas 9, 11, 12, 14, 16 y 20, y nueva regla 22).
