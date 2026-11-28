# Research: Valer-IA atiende a cualquier número de WhatsApp (spec 031)

Sin `NEEDS CLARIFICATION` en el contexto técnico. Hallazgos verificados contra el código y OpenClaw 2026.11.10 el
2026-11-27.

## R1. Cómo se abre el canal en OpenClaw

- **Hallazgo**:
  - El acceso por WhatsApp lo decide OpenClaw antes de que el mensaje llegue al plugin. Por eso el número no
    habilitado de la prueba no recibió respuesta: el canal está en `dmPolicy: "allowlist"` con tres números
    (`WA_ALLOW_1..3`).
  - OpenClaw valida que `dmPolicy: "open"` exige `allowFrom` con `"*"` («dmPolicy="open" requires
    channels.whatsapp.allowFrom to include "*"»).
  - `scripts/openclaw_env.ps1 -Mode open` (spec 028) ya hace exactamente eso: guarda los números de prueba en
    `WA_TEST_1..3`, pone `WA_DM_POLICY=open`, `WA_ALLOW_1="*"` y reinicia el gateway.
- **Decision**:
  - Se mantiene ese mecanismo y se vuelve verificable: un paso documentado, el estado visible en `ops check` y una
    prueba con un número nuevo.
  - **No** se usa `dmPolicy: "pairing"`, porque le enviaría un código de emparejamiento a cada persona nueva
    (contradice FR-001).
- **Alternatives considered**:
  - Abrir con el agente nativo de OpenClaw. Descartado: es el plugin quien atiende.
  - Filtrar en el backend con el canal siempre abierto en OpenClaw. Descartado como única barrera: el modo cerrado
    perdería su sentido para mantenimiento.

## R2. Quién es «número de prueba» (operador) en el backend

- **Hallazgo**: el backend solo ve seudónimos (`wa-<16 hex>`, sal secreta). El planificador ya usa una lista de
  seudónimos en el `.env` del backend (`VALERIA_PLANNERS`).
- **Decision**:
  - Nueva variable `VALERIA_OPERATORS` (seudónimos separados por comas) en el `.env` del backend.
  - Los operadores no tienen límites y son los únicos con atajos del operador en modo abierto.
  - Nuevo comando `pml channels pseudonym --sender <E.164>`: imprime el seudónimo para copiarlo, sin guardar el
    número.
- **Rationale**:
  - Mismo patrón que `VALERIA_PLANNERS`.
  - El backend no necesita conocer los números ni el modo de OpenClaw.
- **Alternatives considered**:
  - Que el plugin marque al operador leyendo `WA_TEST_*`. Descartado: duplica la fuente de verdad y en modo cerrado
    esas variables pueden estar vacías.

## R3. Límites por número y tope diario

- **Decision**:
  - **Dónde**: en `ChannelBridge.handle`, después de la deduplicación y antes de la cola por persona, para que un
    número que abusa no ocupe turnos ni llame al modelo.
  - **Contadores**: por seudónimo en el almacén del canal (SQLite del estado, fuera del repo). Ventana corta fija de
    10 minutos (20 mensajes) y día calendario local (100 mensajes). Configurables en `[channels]` de
    `config/agent.toml`: `rate_window_minutes`, `rate_max_messages`, `daily_max_messages`.
  - **Al superar el límite**:
    - un único aviso por ventana o por día (bandera en el contador), en el idioma del mensaje;
    - los siguientes mensajes se registran como `event: "rate_limited"` o `"daily_capped"` y no reciben respuesta.
  - **Excepciones**: los operadores no cuentan. Los mensajes ignorados por duplicado tampoco.
- **Rationale**:
  - Protege el costo del modelo y la CPU del portátil, con persistencia entre reinicios para el tope diario.
  - La ventana fija es simple de probar.
- **Alternatives considered**:
  - Límite en OpenClaw. No hay control por número en la versión actual.
  - Ventana deslizante. Más compleja y sin beneficio real para la sustentación.

## R4. Bloqueo de números

- **Decision**:
  - Tabla `channel_blocked(user_id, blocked_at)` en el almacén del canal.
  - Comandos `pml channels block --sender <E.164>` y `pml channels unblock --sender …`: calculan el seudónimo y
    nunca guardan el número.
  - Un número bloqueado no recibe respuesta (`status: "ignored"`, `event: "blocked"`) y no llama al modelo.
- **Rationale**: un paso en el servidor, sin exponer comandos por WhatsApp (FR-012) ni números en disco.

## R5. Atajos del operador en modo abierto

- **Decision**:
  - Los atajos (`/traza`, `/perfil`, `/nuevo`, `/ayuda`) solo se ejecutan para operadores cuando hay operadores
    configurados.
  - Para cualquier otra persona, el texto sigue el flujo normal de conversación.
  - Sin `VALERIA_OPERATORS` (instalaciones previas), el comportamiento no cambia.
- **Rationale**: un desconocido no puede ver trazas ni cambiar de perfil por un atajo oculto.

## R6. Visibilidad del modo y del uso

- **Decision**:
  - **`ops check`**: gana la comprobación `modo-canal`. Lee solo la clave `WA_DM_POLICY` del `.env` externo de
    OpenClaw (`%USERPROFILE%\.openclaw-valeria\.env` u `OPENCLAW_STATE_DIR`):
    - `open` → «ABIERTO al público» (con advertencia visible);
    - `allowlist` → «cerrado (N números)».
    - Nunca imprime números.
  - **`GET /api/channels/status`**: añade `people_today` (seudónimos distintos), `limited_today` (limitados y topes)
    y `blocked_today`, calculados del registro diario del canal.
- **Rationale**:
  - El modo vive en OpenClaw y lo lee `ops`, que corre en el mismo equipo.
  - El uso lo mide el backend sin contenido.

## R7. Privacidad con números nuevos

- **Hallazgo**: `pseudonym()` y `mask()` ya se aplican a todo remitente. El registro guarda `user_id` (seudónimo) y
  el hash del mensaje, y el almacén guarda el número enmascarado.
- **Decision**: no se cambia la privacidad. Se agrega una prueba con 3 números distintos que verifica que ningún
  número completo aparece en registros, almacén ni estado (SC-005).
