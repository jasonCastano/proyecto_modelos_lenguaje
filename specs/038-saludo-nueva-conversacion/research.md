# Research: Saludo y presentación al iniciar una conversación (spec 038)

## R1. ¿Quién escribe la presentación?

- **Decision**: la escribe el bridge del canal, de forma determinista, con variantes. El modelo sigue respondiendo
  como hoy.
- **Rationale**:
  - El fallo reportado nace justo de depender del modelo: `prompts/agent.md` solo pide presentarse ante un saludo.
  - Una frase fija anclada al inicio cumple el 100 % (SC-001) en modo real, en modo demo (modelo guionado) y cuando
    el modelo falla.
  - Mantiene el grafo intacto: hay varias rutas (conversación, búsqueda y planificación), cada una con su prompt.
- **Alternatives considered**:
  - **Solo prompt** (regla «si es el inicio, preséntate»): variado, pero no garantiza el 100 % y repite el
    problema actual.
  - **Híbrido** (pista al modelo más red de seguridad): más natural, pero toca el grafo, los prompts de todas las
    rutas y el modelo demo, y deja dos fuentes de verdad.

## R2. Naturalidad de una frase fija

- **Decision**:
  - tres variantes por idioma (es/en), elegidas de forma estable por el hilo (`hash(thread_id) % 3`);
  - cada una tiene dos frases como máximo: saludo e identidad, y propósito con la mención de voz;
  - si el servicio reconoce el nombre de la persona (`outcome.client.name`), el saludo lo usa;
  - nunca hay comandos ni menús.
- **Rationale**: varía entre personas sin ser aleatoria en las pruebas, y es reproducible en el modo demo.
- **Alternatives considered**: una sola frase (se siente robótica); elegir al azar (pruebas no deterministas).

## R3. Evitar la doble presentación con la respuesta del modelo

- **Decision**:
  - **Si la respuesta ya se presenta** (las dos primeras frases mencionan «Valer-IA» o «Valeria»), no se agrega
    nada. Es el caso de «Hola», donde `agent.md` ya pide presentarse. Igual se marca como presentada, con origen
    `agent`.
  - **Si la respuesta empieza con un saludo suelto** («¡Hola!», «Hola, …», «Hi!», «Hello»), ese saludo inicial se
    quita y se antepone la presentación.
  - **En los demás casos**, la presentación se antepone tal cual (origen `bridge`).
- **Rationale**: un solo saludo y una sola presentación por conversación (FR-005).
- **Alternatives considered**: no quitar el saludo del modelo («¡Hola! … ¡Hola! …», poco natural); pedirle al
  modelo que no salude (vuelve a depender del prompt).

## R4. ¿Cuándo empieza una conversación?

- **Decision**: se reconocen tres motivos.
  - **`first_contact`**: `ensure_user` crea el usuario.
  - **`inactivity`**: `now - last_seen > conversation_idle_hours`, que por defecto es 12 h y se configura en
    `[channels]` entre 1 y 720.
    - Se cierra el hilo y se abre otro, igual que `new_thread`.
    - La memoria aprobada (perfil) vive aparte, por `user_id`, y se conserva.
  - **`restart`**: la intención de empezar de nuevo, que ya existe.

  La marca que manda es `introduced` del hilo activo: la presentación va en la primera respuesta atendida de un
  hilo con `introduced = 0`.
- **Rationale**:
  - La marca por hilo cubre los tres motivos con una sola regla.
  - Sobrevive a reinicios del backend.
  - Evita repetirla si llegan varios mensajes seguidos: el candado por persona los ordena y el primero la marca.
- **Alternatives considered**:
  - Una marca en memoria: se pierde al reiniciar.
  - Inferirla de `started`: el hilo «empieza» también con un error o con un atajo del operador.

## R5. Hilos existentes al desplegar

- **Decision**: `ALTER TABLE channel_threads ADD COLUMN introduced INTEGER NOT NULL DEFAULT 1`. Los `INSERT` nuevos
  escriben `0` de forma explícita.
- **Rationale**:
  - Quien está conversando en este momento no recibe una presentación a mitad de su conversación.
  - Esos hilos se renuevan solos con la regla de inactividad (supuesto de la spec).
- **Alternatives considered**: `DEFAULT 0` (todos se presentarían en el siguiente mensaje, aunque lleven 5 minutos
  hablando).

## R6. Voz

- **Decision**:
  - `for_answer(question, answer_sin_presentación, language, with_sources, opening=presentación_hablada)`;
  - el guion del modelo (o el de respaldo) se genera sin la presentación y luego se antepone `opening`;
  - la cifra de validación (`valid_script`) se calcula como hoy, sobre la respuesta sin presentación;
  - para textos fijos (`for_text`), `spoken` ya incluye la presentación.
- **Rationale**:
  - El modelo del guion condensa y podría omitir o reescribir la presentación.
  - Anteponerla después garantiza el FR-006 sin cambiar `prompts/voice_script.md`.
- **Alternatives considered**: regla nueva en `voice_script.md` (dependería del modelo otra vez).

## R7. Casos sin presentación y errores

- **Decision**:
  - **Sin presentación**:
    - avisos de límite y bloqueo (ocurren antes de abrir el hilo);
    - atajos del operador;
    - aprobación pendiente (`reask`, `confirm`, `expired`);
    - confirmación «empezamos de cero» sin solicitud.
  - **Con presentación**: «no soportado» (imagen o sticker) y «no te escuché» (nota de voz sin texto), porque son
    respuestas atendidas de un hilo nuevo.
  - **Error del modelo**: el mensaje lleva una frase de identidad («Soy Valer-IA, la asistente virtual de
    Manuelita.») pero no marca `introduced`; la siguiente respuesta atendida se presenta completa.
- **Rationale**: es el criterio de casos límite de la spec. La presentación solo acompaña conversación real.
- **Alternatives considered**: presentarse también en el aviso de límite (contradice spec 031: un único aviso
  breve).
