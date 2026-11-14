# Research: Valer-IA Caña (spec 018)

Fecha: 2026-11-14. Puntos de partida en el código:
- `service.py::_prepare`: `redact_pii` antes de guardar y `user_id` del navegador en el estado del hilo.
- `graph.py`: respuestas deterministas `GREETING_ANSWER`, `OUT_OF_SCOPE_ANSWER` y `CLARIFY_ANSWER`.
- `router.py`: reglas `OUT_OF_SCOPE_PATTERNS`.
- `actions.py`: escrituras con aprobación humana (HITL).
- `memory.py`: Store `("users", user_id, …)`.
- `ChatView.tsx::anonymousUser`: el `user_id` vive en `localStorage` y nunca cambia.

## R1. Bienvenida: determinista y anclada al corpus

- **Decision**: el texto de bienvenida es una plantilla versionada (`prompts/welcome.md` v1.0) con cifras y citas a
  unidades del oro verificadas por prueba. Se sirve con `GET /api/welcome` (texto, citas y versión), sin llamar al
  modelo de lenguaje. La interfaz la muestra como primer mensaje de Valer-IA y la lee con la voz.
- **Rationale**: aparece en menos de 2 s (SC-001), no tiene costo ni variación, y cada afirmación sobre Manuelita es
  verificable (FR-023). Una prueba comprueba que las unidades citadas existen y contienen los datos de la plantilla
  (por ejemplo, «1864»).
- **Alternatives considered**: generarla con el LLM en cada visita (lento, con costo y riesgo de alucinación);
  escribirla en el frontend (sin trazabilidad ni versión de prompt).

## R2. Visita y cliente anónimo

- **Decision**: el `user_id` anónimo y el hilo pasan de `localStorage` a `sessionStorage`. Una visita nueva (nueva
  sesión del navegador) es un cliente nuevo y recargar la página no la termina (FR-006). Las conversaciones
  recientes (`localStorage`) solo se muestran en la vista técnica.
- **Rationale**: corrige el problema reportado sin botones (FR-007) y sin borrar datos (FR-002 de la versión
  anterior).
- **Alternatives considered**: expiración por tiempo (arbitraria); cookie del servidor (no aporta y complica las
  pruebas).

## R3. Reconocimiento conversacional por correo

- **Decision**: un paso determinista de identidad (`agent/identity.py`) corre **antes** de redactar el mensaje.
  - **Detecta el correo**:
    - con el detector de `privacy.py`, normaliza (sin espacios alrededor, `casefold`) y calcula
      `HMAC-SHA256(clave, correo)`;
    - descarta el correo en claro de inmediato;
    - al grafo solo llega el mensaje redactado (`[REDACTED_EMAIL]`) y la huella.
  - **Clave**: `MANUELITA_IDENTITY_KEY` en `.env`. Si falta, se genera una aleatoria y se guarda en
    `MANUELITA_STATE_DIR/identity.key`, fuera del repositorio.
  - **Nodo `identify`**: un nodo nuevo al inicio de ambos grafos (cadena y agente) atiende los turnos de identidad
    con respuestas deterministas de Valer-IA. Los turnos se guardan en el hilo como cualquier otro y no llaman al
    modelo de lenguaje.
  - **Correo registrado**: pide confirmar el nombre registrado, compara nombres normalizados (sin tildes ni
    mayúsculas; basta con el primer nombre) y, si coincide, el hilo cambia su `user_id` al del cliente reconocido.
    La respuesta HTTP devuelve el nuevo `user_id` para que el navegador lo adopte.
  - **Correo nuevo**: si el perfil no tiene nombre, Valer-IA lo pide. Después propone la acción `remember_client`
    con aprobación humana conversacional, que guarda el nombre y vincula la huella.
  - **«No soy Ana», «empecemos de nuevo», «soy otra persona»**: reglas que responden con `client_reset`. El
    navegador genera un cliente anónimo nuevo y abre otro hilo.
  - **Límites**: 3 confirmaciones fallidas por hilo (FR-011). Además, se bloquea una huella durante 1 hora tras 5
    fallos desde cualquier sesión, para resistir el sondeo con identificadores nuevos.
- **Rationale**: el reconocimiento es una decisión de seguridad. Hacerla con reglas, y no con el LLM, la hace
  determinista, probable y resistente a la inyección. El correo nunca entra al grafo, al modelo, a las trazas ni a
  los registros (FR-013).
- **Alternatives considered**:
  - Herramienta del LLM `identify_client(email)`: expone el correo al modelo y deja la seguridad a su criterio.
  - PIN o código de un solo uso: descartados en la spec; están en Assumptions como mejora futura.
  - Guardar el correo cifrado: innecesario, porque basta con la coincidencia.

## R4. Respuestas de situaciones difíciles

- **Decision**: ampliar el enrutador con un campo nuevo, `scope_reason`, en la decisión: `off_topic`, `abuse`,
  `harmful`, `third_party`, `prompt_extraction`, `advice` y `identity`.
  - Cada motivo tiene reglas propias en `router.py`, revisadas sobre el español del corpus, y una respuesta
    determinista con la voz de Valer-IA en `prompts/conduct.md`, versionado.
  - Los casos `out_of_scope` del LLM sin motivo explícito usan `off_topic`.
  - Las quejas, el empleo y los trámites siguen por la ruta documental. La regla nueva del prompt del agente
    (v1.3) obliga a citar canales oficiales del corpus y a no inventar contactos.
- **Rationale**: las respuestas a abuso, daño, datos de terceros y extracción del prompt deben ser estables y
  verificables. Se reutiliza la ruta existente `out_of_scope`, que no busca en el corpus.
- **Alternatives considered**: solo instrucciones en el prompt (no deterministas, y difíciles de garantizar con 95
  %); moderación externa (servicio nuevo).

## R5. Datos sensibles compartidos por el visitante

- **Decision**: `redact_pii` ya los reemplaza. El servicio registra en el estado qué categorías se redactaron
  (`pii_notice`) y el nodo `finalize` antepone un aviso determinista: «Por tu seguridad, no compartas números de
  tarjeta ni documentos; no los guardé.» (FR-020).
- **Rationale**: es explícito y no depende del modelo.

## R6. Personaje en los prompts

- **Decision**: actualizar las versiones y registrarlas en `docs/prompt_log.md`:
  - `prompts/agent.md` → v1.3: rol Valer-IA Caña, tono, transparencia, reglas de conducta (secciones 1 y 4) y
    canales oficiales;
  - `prompts/router.md` → con `scope_reason`;
  - `prompts/welcome.md` (nuevo) y `prompts/conduct.md` (nuevo).

  Las constantes `GREETING_ANSWER`, `FAREWELL_ANSWER`, `CLARIFY_ANSWER` y `OUT_OF_SCOPE_ANSWER` pasan a leerse de
  `conduct.md`.
- **Despedida**: si el visitante es anónimo y aún no se le ofreció, incluye una vez por visita: «Si quieres que te
  reconozca en tu próxima visita, puedes compartirme tu correo» (FR-007).

## R7. Interfaz para visitantes y vista técnica

- **Decision**: la vista se elige con `?vista=tecnica` (persistida en `sessionStorage`).
  - **Vista normal**:
    - muestra la conversación, el avatar, los controles de voz, las fuentes, el campo de mensaje y las respuestas
      rápidas;
    - oculta las opciones de variante y trazas, las conversaciones recientes, los casos de demo, los chips de ruta,
      los fragmentos, las métricas y los avisos técnicos.
  - **Vista técnica**: idéntica a la actual.
  - **Acciones pendientes** en vista normal: un nuevo componente `QuickReplies` muestra los botones «Sí,
    recuérdame» / «No, gracias» (o las etiquetas de cada acción), que llaman a `resume` con `approve` o `reject`.
    La tarjeta `ApprovalCard` queda en la vista técnica.
  - **Modo**: en vista normal se usa el modo real si el proveedor está configurado. Si no, se usa el modo demo sin
    mostrarlo como «demostración», con el mismo personaje.
- **Rationale**: cumple FR-024 a FR-026 sin perder la sustentación.

## R8. Voz de la bienvenida

- **Decision**: al cargar se llama a `voice.speak(bienvenida)`.
  - Si el navegador bloquea el audio, se espera al primer gesto del visitante (`pointerdown` o `keydown`) y se
    reproduce, salvo que ya haya enviado un mensaje.
  - Una marca en `sessionStorage` evita repetirla en la misma visita (FR-004).
  - Al enviar el primer mensaje, `startLive` detiene la bienvenida, como cualquier otra lectura.

## R9. Evaluación de conducta

- **Decision**: un comando `agent conduct`, análogo a `agent shield`, con las piezas siguientes:
  - **Casos**: `tests/fixtures/conduct/conduct_cases.jsonl`, con 24 casos: fuera de tema, datos de terceros,
    extracción del prompt, insultos, solicitudes dañinas, datos sensibles, quejas o trámites, asesoría, identidad
    con correo registrado o falso, y presentación como IA.
  - **Verificaciones deterministas por caso**: `must_contain_any`, `must_not_contain` y `expected_reason`.
  - **Corridas**: el modo demo se ejecuta en pytest sin red; el modo real genera `docs/evaluacion_conducta.md` y
    su JSON.
  - **Métricas**: % de cumplimiento (meta ≥ 95 %) y fugas (meta 0).
- **Revaluación**: se vuelve a correr la evaluación del Módulo 2 (enrutador y cadena vs. agente) para comprobar
  que no hubo regresión (SC-008).
