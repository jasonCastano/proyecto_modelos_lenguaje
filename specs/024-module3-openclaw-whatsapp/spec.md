# Feature Specification: Entrega final del Módulo 3: Valer-IA Caña en WhatsApp con OpenClaw y 20 herramientas

**Feature Branch**: `024-module3-openclaw-whatsapp`

**Created**: 2026-11-23

**Status**: Draft

**Input**: User description: "El docente ha compartido la nueva rúbrica de evaluación para el módulo 3. La rúbrica se
encuentra en "C:\Users\JCastano\Downloads\Anuncio_007_Sustentacion_Final_Modulo_3.md". Añade a este proyecto todas las
nuevas metas asociadas a los nuevos requerimientos mencionadas en la rúbrica para dar cumplimiento a este proyecto"

**Contexto**: El Anuncio 007 fija la sustentación final del Módulo 3 para el **sábado 28 de noviembre de 2026, 8:00
a.m.**: 15 minutos por grupo (7 de pitch y 8 de discusión técnica), sin diapositivas, con invitados de las empresas
(entre ellas Manuelita) probando el agente **desde sus teléfonos por WhatsApp**. La rúbrica tiene 15 ítems ponderados
(1.0–5.0) y el 55 % está en la arquitectura del agente (25 %) y en OpenClaw, canales y despliegue (30 %).

Estado de partida (rama `main`, 2026-11-23): Valer-IA Caña ya conversa, enruta (reglas, Jev y LLM), recuerda (hilo
persistente y perfil entre hilos), cita, busca en Qdrant con búsqueda híbrida, se blinda ante inyección, pide aprobación
humana para escribir, habla y escucha en la web. Los huecos frente a la rúbrica son:

| Ítem | Peso | Hueco principal |
|------|-----:|-----------------|
| 1.1 Catálogo de 20 tools | 10 % | El agente tiene **7** herramientas (3 de lectura y 4 de escritura con aprobación). Faltan 13. |
| 1.2 Router y plan | 8 % | La decisión de ruta se ve en la web, pero no en el canal de WhatsApp ni como plan explícito de varios pasos. |
| 1.3 Memoria por capas | 7 % | Existe; falta el workspace legible de OpenClaw (`MEMORY.md`) y la demostración desde WhatsApp. |
| 2.1 Pipeline del M1 | 5 % | Existe por capas; falta **un solo comando** que reconstruya el corpus de punta a punta. |
| 2.2 RAG sobre Qdrant | 6 % | El índice HNSW real con servidor no se ha probado en vivo; el modo embebido busca exacto. |
| 2.3 Evaluación del conocimiento | 4 % | Hay Recall@k y nDCG@10; **no hay proyección t-SNE/UMAP** de los embeddings. |
| 3.1 Gateway OpenClaw | 8 % | **No existe**. |
| 3.2 WhatsApp en producción | 10 % | **No existe**; tampoco hay un despliegue fuera de localhost. |
| 3.3 Workspace operativo | 7 % | **No existe** (`SOUL.md`, `AGENTS.md`, `USER.md`, `MEMORY.md`, bitácora diaria del agente). |
| 3.4 Skill/plugin/MCP propio | 5 % | **No existe** en el ecosistema OpenClaw. |
| 4.1 Código y pruebas | 7 % | Cumple; las pruebas nuevas deben mantener el estándar. |
| 4.2 Seguridad y hardening | 7 % | Blindaje e HITL existen; faltan sandbox, deny-list, workspace-only, allowlist/pairing y la auditoría de OpenClaw. |
| 4.3 Documentación final | 6 % | Falta la guía de despliegue, el manual de uso en WhatsApp y los diagramas con el gateway. |
| 5.1 / 5.2 Sustentación | 10 % | Falta el guion del Módulo 3, el ensayo y el plan de contingencia. |

Esta funcionalidad reúne **todas las metas nuevas** que la rúbrica exige, para que el proyecto llegue completo al sábado.

## Clarifications

### Session 2026-11-23

- Q: ¿Dónde se despliegan el agente y el gateway para la demo? → A: En un **PC del equipo que queda encendido**
  (servidor dedicado durante la jornada), expuesto con un **túnel** seguro; no en el portátil que se usa para presentar.
- Q: ¿Qué número de WhatsApp usa el bot? → A: El **número de un integrante**, vinculado como dispositivo.
- Q: ¿Cómo acceden los invitados? → A: **Lista de autorizados + emparejamiento**: números conocidos registrados antes
  del sábado; cualquier otro pide acceso con código y el equipo lo aprueba en el momento.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Un invitado le escribe a Valer-IA por WhatsApp y recibe una respuesta citada (Priority: P1)

Un invitado de una empresa, autorizado previamente, abre WhatsApp en su propio teléfono, le escribe al número del
proyecto «¿Qué produce Manuelita?» y en pocos segundos recibe la respuesta de Valer-IA Caña con sus fuentes. Sigue la
conversación («¿y en Perú?») y el agente entiende la referencia al turno anterior. El agente corre como servicio en un PC del
equipo dedicado, no en el portátil con el que se presenta.

**Why this priority**: Es la condición de entrada de la sustentación. Sin WhatsApp real el ítem 3.2 (10 %) vale cero y
la rúbrica lo declara «no se acepta»; también es la demo del pitch (5.1).

**Independent Test**: Desde un teléfono incluido en la lista de autorizados, enviar tres mensajes encadenados al número
del proyecto con el portátil de presentación apagado y verificar respuestas coherentes, citadas y en el mismo hilo.

**Acceptance Scenarios**:

1. **Given** el agente desplegado y un número autorizado, **When** el invitado escribe una pregunta sobre Manuelita,
   **Then** recibe por WhatsApp una respuesta en español con al menos una fuente identificable (documento y enlace o
   página).
2. **Given** una conversación en curso, **When** el invitado hace una repregunta con referencia implícita, **Then** el
   agente la resuelve usando el hilo de ese número.
3. **Given** un número **no** autorizado, **When** escribe al bot, **Then** no recibe respuestas del agente ni consume
   cuota del modelo; el intento queda registrado.
4. **Given** un saludo o «gracias», **When** llega por WhatsApp, **Then** el agente responde sin ejecutar búsquedas.
5. **Given** que el servicio del modelo en la nube falla, **When** llega un mensaje, **Then** el agente responde con un
   mensaje breve de indisponibilidad (o usa el modelo de respaldo) en vez de quedarse callado.

---

### User Story 2 - El agente usa 20 herramientas tipadas y explica cuál eligió y por qué (Priority: P1)

Un evaluador pide a Valer-IA tareas que exigen distintas capacidades: una cifra exacta de un informe, una comparación
entre años, un indicador ambiental, los canales oficiales de contacto, guardar una preferencia, exportar la
conversación. El agente decide qué herramienta usar (o ninguna), la ejecuta con argumentos validados y la decisión queda
visible en la traza. El equipo puede mostrar el catálogo completo de 20 herramientas, cada una con su descripción y
esquema de argumentos, y explicar cada una.

**Why this priority**: El ítem 1.1 (10 %) exige 20 herramientas conectadas, tipadas y demostrables; la rúbrica rechaza
«un agente con menos de 20 tools». El ítem 1.2 (8 %) exige ver la decisión del router.

**Independent Test**: Listar el catálogo (20 entradas con nombre, descripción y esquema); ejecutar una consulta de prueba
por herramienta y comprobar en la traza que se invocó la herramienta esperada con argumentos válidos.

**Acceptance Scenarios**:

1. **Given** el agente en marcha, **When** se consulta su catálogo, **Then** aparecen exactamente 20 herramientas o más,
   cada una con nombre único, descripción en español y esquema de argumentos con tipos y validaciones.
2. **Given** una consulta que requiere una herramienta concreta, **When** el agente responde, **Then** la traza muestra
   la ruta elegida, el plan (pasos previstos) y la herramienta invocada con sus argumentos.
3. **Given** argumentos inválidos generados por el modelo, **When** se invoca una herramienta, **Then** la validación los
   rechaza con un error claro y el agente se recupera sin romper la conversación.
4. **Given** una herramienta que escribe, envía o modifica algo, **When** el agente la propone, **Then** se pide
   confirmación explícita del usuario antes de ejecutarla, también en WhatsApp.
5. **Given** una consulta trivial (saludo, agradecimiento, pregunta sobre el propio asistente), **When** el router
   decide, **Then** no se ejecuta ninguna herramienta de búsqueda.

---

### User Story 3 - El equipo opera el gateway OpenClaw con su workspace, su skill propio y su seguridad (Priority: P1)

Un integrante enciende el gateway de OpenClaw en el servidor del proyecto, revisa el estado de los canales, sigue los
registros en vivo y pasa la auditoría de seguridad. El gateway tiene su configuración versionada (sin secretos), un
modelo principal en la nube con respaldo, escucha solo en la interfaz local con token, y un workspace con la identidad
de Valer-IA (`SOUL.md`), sus reglas (`AGENTS.md`), el perfil del usuario (`USER.md`), la memoria curada (`MEMORY.md`) y
una bitácora diaria. Al menos un skill o servidor MCP propio del proyecto está conectado al gateway con permisos
declarados.

**Why this priority**: Los ítems 3.1 (8 %), 3.3 (7 %), 3.4 (5 %) y 4.2 (7 %) dependen de OpenClaw, y la rúbrica rechaza
«un agente sin las capacidades de OpenClaw».

**Independent Test**: Ejecutar la prueba de 3 minutos del Anuncio 007 (sincronizar el entorno, levantar o reiniciar el
gateway, sondear los canales, seguir los registros y correr la auditoría) en el servidor de la demo y obtener todo en
verde.

**Acceptance Scenarios**:

1. **Given** el servidor del proyecto, **When** se inicia el gateway, **Then** arranca como servicio, con la
   configuración del repositorio, el modelo principal en la nube y al menos un modelo de respaldo.
2. **Given** el gateway en marcha, **When** se sondean los canales, **Then** WhatsApp aparece vinculado y operativo.
3. **Given** el workspace, **When** un integrante abre sus archivos, **Then** encuentra la identidad y el tono separados
   de los límites (red lines), la memoria legible y editable, y la bitácora del día.
4. **Given** el skill o servidor MCP propio, **When** el agente lo usa, **Then** la traza lo muestra y su permiso está
   declarado en la configuración; el equipo puede explicar cómo se autoriza.
5. **Given** la auditoría de seguridad de OpenClaw, **When** se ejecuta, **Then** termina sin hallazgos críticos.
6. **Given** un mensaje con una instrucción inyectada (directa o dentro de un documento recuperado), **When** el agente
   lo procesa, **Then** no la obedece, no revela su configuración y no ejecuta acciones sensibles sin confirmación.

---

### User Story 4 - La memoria sobrevive al reinicio y un hilo nuevo recuerda el perfil (Priority: P2)

Un invitado le dice a Valer-IA por WhatsApp «me llamo Ana y trabajo en logística», aprueba que lo recuerde, y sigue
conversando. El equipo reinicia el servicio. Ana vuelve a escribir y el hilo continúa. Al día siguiente, en un hilo
nuevo, el agente la saluda por su nombre. El equipo puede mostrar dónde está guardado ese recuerdo y borrarlo si Ana lo
pide.

**Why this priority**: El ítem 1.3 (7 %) pide exactamente esto, auditable. La base existe en la web (spec 014); falta
demostrarla en el canal real y en el workspace.

**Independent Test**: Guardar un perfil por WhatsApp, reiniciar el servicio, comprobar la continuidad del hilo; abrir un
hilo nuevo y comprobar que el perfil se recupera; pedir «olvida mis datos» y comprobar que desaparecen.

**Acceptance Scenarios**:

1. **Given** un perfil aprobado, **When** se reinicia el servicio, **Then** el hilo del número continúa sin pérdida.
2. **Given** un hilo nuevo del mismo número, **When** el invitado saluda, **Then** el agente usa su perfil.
3. **Given** que el invitado pide olvidar sus datos, **When** confirma, **Then** el perfil se borra y deja de usarse.
4. **Given** la memoria a largo plazo, **When** el equipo la inspecciona, **Then** puede leer qué se guardó, de quién y
   cuándo, sin exponer números completos de teléfono en documentos versionados.

---

### User Story 5 - El conocimiento se reconstruye con un comando y se evalúa con métricas y una proyección 2D (Priority: P2)

Un evaluador pide reconstruir el corpus: con un solo comando se ejecuta el pipeline del Módulo 1 (extracción,
limpieza, fragmentación con solapamiento y metadatos) e indexación en Qdrant, conservando la trazabilidad a la fuente.
Luego revisa la evaluación del retrieval (Recall@10 y nDCG@10 sobre 20–30 consultas) y una proyección t-SNE o UMAP de
los embeddings que el equipo usa para diagnosticar clústeres y fallos.

**Why this priority**: Ítems 2.1 (5 %), 2.2 (6 %) y 2.3 (4 %); la proyección 2D además da el bonus transversal de
excelencia científica (hasta +10 % sobre el M3).

**Independent Test**: Ejecutar el comando de reconstrucción en un entorno limpio (en modo que no reescriba las capas
versionadas) y verificar que produce el índice; abrir el informe de evaluación y la proyección y comprobar que las
consultas fallidas se ubican en la figura.

**Acceptance Scenarios**:

1. **Given** el repositorio clonado, **When** se ejecuta el comando de reconstrucción, **Then** se recorren todas las
   etapas en orden y cada fragmento conserva su documento, URL y posición de origen.
2. **Given** el índice en el servidor de Qdrant, **When** se consulta, **Then** usa el índice aproximado (no la búsqueda
   exacta embebida), con filtros por metadatos, búsqueda híbrida y cita verificable.
3. **Given** el conjunto de evaluación, **When** se corre la evaluación, **Then** se reportan Recall@10 y nDCG@10 sobre
   entre 20 y 30 consultas etiquetadas.
4. **Given** la proyección 2D, **When** se abre, **Then** se distinguen los clústeres por tema o unidad de negocio y se
   marcan las consultas con bajo desempeño, con una lectura escrita del diagnóstico.

---

### User Story 6 - Cualquier persona entiende y despliega el proyecto sin abrir el código (Priority: P2)

Un evaluador lee el README y la documentación final: entiende la arquitectura completa (corpus → RAG → agente →
gateway → WhatsApp) con diagramas, sigue la guía de despliegue paso a paso, consulta el manual de uso para invitados y
revisa las decisiones y resultados. No hay secretos en el repositorio.

**Why this priority**: Ítem 4.3 (6 %) y parte del 4.1; además el «no se acepta» de keys y `.env` en el repositorio.

**Independent Test**: Una persona ajena al equipo sigue la guía de despliegue en una máquina limpia hasta tener el agente
respondiendo en un canal de prueba; un escaneo del repositorio no encuentra secretos.

**Acceptance Scenarios**:

1. **Given** el README, **When** se lee, **Then** incluye el diagrama de arquitectura actualizado con el gateway y
   WhatsApp, y enlaces a la guía de despliegue, el manual de uso y las decisiones.
2. **Given** la guía de despliegue, **When** se sigue, **Then** cubre servidor, variables de entorno, gateway, vinculación
   de WhatsApp, lista de autorizados, servicio y verificación.
3. **Given** el historial del repositorio, **When** se escanea, **Then** no contiene claves, credenciales del canal ni
   archivos `.env`.

---

### User Story 7 - El equipo sustenta en 15 minutos con la demo en el teléfono del invitado (Priority: P3)

El equipo tiene un guion de 7 minutos de pitch (problema de Manuelita, propuesta de valor, demo real en WhatsApp desde
el teléfono de un invitado, cierre comercial) y 8 de discusión técnica, con la división de temas por integrante, el
ensayo cronometrado, la versión en inglés (bonus) y un plan de contingencia si el bot o el gateway fallan. Los invitados
de Manuelita quedan registrados en la pestaña 2 antes del sábado.

**Why this priority**: Ítems 5.1 (6 %) y 5.2 (4 %). Depende de que las historias 1–3 funcionen.

**Independent Test**: Ensayo completo cronometrado con un teléfono ajeno al equipo, dentro de 15 minutos, con cada
integrante respondiendo preguntas de su parte.

**Acceptance Scenarios**:

1. **Given** el guion, **When** se ensaya, **Then** el pitch dura ≤ 7 minutos e incluye la demo real en WhatsApp.
2. **Given** una falla del bot durante la demo, **When** ocurre, **Then** el equipo aplica el plan de contingencia
   documentado (mostrar repositorio, registros y explicar qué falló) sin cambiar de computador.
3. **Given** la lista de verificación del Anuncio 007, **When** se revisa el viernes 27, **Then** todos los obligatorios
   están marcados con evidencia.

---

### Edge Cases

- El invitado envía audio, imagen, ubicación o sticker por WhatsApp: el agente responde que por ahora solo entiende texto
  (o transcribe la nota de voz si se habilita) y no falla.
- Mensajes muy largos (> 2.000 caracteres) o ráfagas de mensajes seguidos: se recortan o se agrupan sin perder el hilo y
  sin respuestas duplicadas.
- Varios invitados escriben a la vez durante la sustentación (12 grupos, público en sala): cada número tiene su hilo y no
  se mezclan contextos; las respuestas llegan en orden.
- La sesión de WhatsApp se desvincula o el teléfono anfitrión pierde conexión: el estado del canal lo muestra y hay un
  procedimiento de revinculación en minutos.
- Se agota la cuota o el saldo del proveedor del modelo: se usa el modelo de respaldo o se responde con un mensaje
  claro; una alerta avisa al equipo.
- Una aprobación pendiente (HITL) en WhatsApp nunca se responde: expira sin ejecutar la acción.
- Un invitado pide datos personales de terceros o información interna no pública: el agente se niega según sus límites.
- Un número no autorizado insiste o intenta emparejarse: no obtiene acceso sin aprobación del equipo.
- El invitado escribe en inglés: el agente responde en inglés con las mismas reglas de citas.
- La respuesta incluye formato de la web (Markdown complejo, enlaces largos): se adapta al formato que WhatsApp muestra
  bien.

## Requirements *(mandatory)*

### Functional Requirements

**Canal WhatsApp y despliegue (ítems 3.2, 5.1)**

- **FR-001**: Valer-IA Caña MUST responder por WhatsApp desde el número real de un integrante vinculado al gateway,
  en un despliegue que corre como servicio en un PC del equipo dedicado y encendido, expuesto con un túnel seguro, y
  que no depende del portátil con el que se presenta.
- **FR-001a**: Como el número es personal, el agente MUST responder solo en chats individuales de números autorizados o
  emparejados y MUST NOT leer, responder ni actuar en grupos ni en los demás chats de ese número.
- **FR-002**: Solo los números incluidos en una lista de autorizados en formato E.164, o aprobados por el equipo
  mediante código de emparejamiento, MUST obtener respuestas; los demás se ignoran (o reciben solo la instrucción de
  emparejamiento) y quedan registrados. Aprobar un emparejamiento MUST tomar menos de 1 minuto durante la jornada.
- **FR-003**: Cada número MUST tener su propio hilo de conversación persistente; las respuestas por WhatsApp MUST pasar
  por el mismo agente (router, memoria, herramientas, blindaje, citas) que la web.
- **FR-004**: Las respuestas por WhatsApp MUST adaptarse al formato del canal (texto breve, fuentes al final como enlaces
  cortos, sin componentes de la web) y MUST llegar en un tiempo que el invitado perciba como conversacional.
- **FR-005**: Los mensajes que no son texto MUST recibir una respuesta controlada y no romper el servicio.
- **FR-006**: El despliegue MUST incluir monitoreo básico (estado del gateway, del canal y del modelo), registros
  consultables en vivo y un plan de contingencia documentado.
- **FR-007**: Un segundo canal (por ejemplo Telegram) MAY añadirse como extra, nunca como reemplazo de WhatsApp.

**Gateway OpenClaw (ítem 3.1)**

- **FR-008**: El proyecto MUST incluir la configuración del gateway OpenClaw versionada en el repositorio, sin secretos,
  con modelo principal en la nube (DeepSeek) y al menos un modelo de respaldo.
- **FR-009**: El gateway MUST escuchar solo en la interfaz local (bind loopback), exigir token de autenticación y correr
  como servicio que se reinicia ante fallos.
- **FR-010**: El motor del agente en la demo MUST ser una API de modelo en la nube; ningún modelo local (Ollama u otro)
  MUST usarse como motor de la demo. Las claves MUST vivir en variables de entorno del servidor.

**Workspace (ítem 3.3)**

- **FR-011**: El workspace del agente MUST contener `SOUL.md` (identidad y tono de Valer-IA), `AGENTS.md` (reglas
  operativas y límites), `USER.md` (perfil del usuario o del público objetivo), `MEMORY.md` (memoria curada) y una
  bitácora diaria generada por la operación del agente.
- **FR-012**: La identidad y el tono MUST estar separados de los límites (red lines) y ser coherentes con la persona
  definida en las specs 018–020.
- **FR-013**: La memoria del workspace MUST ser legible y editable por el equipo, y MUST NOT contener números de teléfono
  completos ni datos personales de invitados en archivos versionados.

**Skill/plugin/MCP propio (ítem 3.4)**

- **FR-014**: El proyecto MUST conectar al gateway al menos un skill modular o servidor MCP propio, con sus permisos
  declarados explícitamente en la configuración.
- **FR-015**: El uso de esa capacidad MUST ser visible en la traza o los registros, y su mecanismo de autorización MUST
  estar documentado.

**Catálogo de 20 herramientas y orquestación (ítems 1.1, 1.2)**

- **FR-016**: El agente MUST disponer de al menos 20 herramientas, cada una con nombre único, descripción en español y
  esquema de argumentos tipado con validación, declaradas en un solo catálogo del arnés.
- **FR-017**: Las herramientas MUST cubrir el dominio de Manuelita y la operación del asistente; como mínimo:
  búsqueda documental citada, consultas estructuradas y agregaciones de cifras, comparación de indicadores entre años,
  indicadores ambientales (agua, carbono, energía), unidades de negocio y presencia geográfica, productos, canales
  oficiales de contacto, preguntas frecuentes, resumen de un tema, noticias recientes del corpus, fecha y cálculo,
  perfil y preferencias del usuario, olvido de datos, exportación de la conversación y solicitud de contacto humano.
- **FR-018**: Toda herramienta que escriba, envíe o modifique estado MUST requerir confirmación humana explícita antes de
  ejecutarse, en la web y en WhatsApp; la confirmación pendiente MUST expirar.
- **FR-019**: Cada invocación MUST quedar en la traza con la ruta, el plan, la herramienta, los argumentos validados, la
  duración y el resultado resumido.
- **FR-020**: El router MUST decidir entre respuesta directa, RAG, herramienta estructurada, herramienta del ecosistema
  OpenClaw o aclaración, y MUST NOT ejecutar búsquedas ante saludos o consultas triviales.
- **FR-021**: Para consultas que requieran varios pasos, el agente MUST exponer su plan (pasos previstos) antes o junto
  con la respuesta en la traza.
- **FR-022**: Cada herramienta MUST tener al menos una prueba automatizada de su contrato y el router MUST tener una
  evaluación que incluya consultas que deben llevar a cada herramienta.

**Memoria (ítem 1.3)**

- **FR-023**: El hilo de cada usuario de WhatsApp MUST sobrevivir al reinicio del servicio.
- **FR-024**: El perfil y las preferencias aprobados MUST recuperarse en hilos nuevos del mismo usuario y MUST poder
  borrarse a petición.
- **FR-025**: La memoria a largo plazo MUST ser auditable: qué se guardó, para quién (identificador seudónimo) y cuándo.

**Datos, RAG y evaluación (ítems 2.1, 2.2, 2.3)**

- **FR-026**: MUST existir un único comando que reconstruya el corpus de punta a punta (extracción, limpieza,
  fragmentación con solapamiento y metadatos, embeddings e índice) conservando la trazabilidad a la fuente, con un modo
  que no reescriba las capas versionadas.
- **FR-027**: El despliegue de la demo MUST usar el servidor de Qdrant con índice aproximado, filtros por metadatos y
  búsqueda híbrida, y las respuestas MUST citar documento y fragmento; sin evidencia, el agente MUST decirlo.
- **FR-028**: La evaluación del retrieval MUST reportar Recall@10 y nDCG@10 sobre un conjunto de entre 20 y 30 consultas
  etiquetadas, sobre el índice desplegado.
- **FR-029**: El proyecto MUST incluir una proyección 2D (t-SNE o UMAP) de los embeddings del corpus, coloreada por tema
  o unidad de negocio, con las consultas evaluadas superpuestas y un análisis escrito de clústeres y fallos.

**Seguridad y hardening (ítem 4.2)**

- **FR-030**: El gateway MUST ejecutar las herramientas con sandbox, lista de herramientas denegadas y acceso al sistema
  de archivos limitado al workspace.
- **FR-031**: La defensa ante inyección directa (mensajes del usuario) e indirecta (contenido recuperado) MUST aplicarse
  también en WhatsApp, y MUST tener una evaluación reproducible que incluya ataques llegados por el canal.
- **FR-032**: La auditoría de seguridad de OpenClaw MUST pasar sin hallazgos críticos antes de la sustentación.
- **FR-033**: El repositorio MUST NOT contener claves, tokens, credenciales del canal, sesiones de WhatsApp ni archivos
  `.env`.

**Calidad y documentación (ítems 4.1, 4.3)**

- **FR-034**: El entorno MUST levantarse con `uv sync` sin pasos manuales adicionales para el backend, y las pruebas
  MUST pasar sin red ni claves (con dobles para el canal y el gateway).
- **FR-035**: La documentación final MUST incluir: arquitectura con diagramas actualizados (gateway, canal, agente, RAG,
  memoria), guía de despliegue, manual de uso para invitados, decisiones (ADR) y resultados de las evaluaciones.
- **FR-036**: `CONSTITUTION.md` MUST actualizarse con los cambios de arquitectura, tecnología y proceso introducidos.

**Sustentación (ítems 5.1, 5.2)**

- **FR-037**: El proyecto MUST incluir el guion del Módulo 3 (7 + 8 minutos), la división de temas por integrante, una
  versión en inglés del pitch y la discusión, y el plan de contingencia.
- **FR-038**: MUST existir una lista de verificación del Anuncio 007 con el estado y la evidencia de cada ítem
  (autoevaluación de los 15 ítems con su peso), revisada el viernes 27 de noviembre.

### Key Entities

- **Usuario de canal**: persona que escribe por WhatsApp; se identifica por su número (E.164) y se representa en
  registros y memoria con un identificador seudónimo derivado. Tiene estado autorizado/no autorizado.
- **Hilo de canal**: conversación persistente asociada a un usuario de canal; equivale al hilo de la web.
- **Herramienta**: capacidad del agente con nombre, descripción, esquema de argumentos, tipo (lectura/escritura) y si
  requiere confirmación.
- **Invocación**: registro en la traza de una herramienta usada en un turno (argumentos, duración, resultado, ruta).
- **Aprobación pendiente**: acción de escritura propuesta y no confirmada, con vencimiento.
- **Workspace**: conjunto de archivos de identidad, reglas, usuario, memoria y bitácora del agente en el gateway.
- **Capacidad de ecosistema**: skill o servidor MCP propio con permisos declarados.
- **Consulta de evaluación**: pregunta etiquetada con sus fragmentos relevantes, usada para Recall@10, nDCG@10 y la
  proyección 2D.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Desde 3 teléfonos autorizados distintos, ajenos al equipo, el 100 % de 10 mensajes de prueba reciben
  respuesta por WhatsApp con el portátil de presentación apagado.
- **SC-002**: El 90 % de las respuestas por WhatsApp llegan en menos de 15 segundos y ninguna tarda más de 45 segundos
  en la prueba de carga de la sustentación (al menos 10 usuarios escribiendo a la vez).
- **SC-003**: Los números no autorizados reciben 0 respuestas del agente en 20 intentos; un número nuevo queda habilitado
  por emparejamiento en menos de 1 minuto; el agente envía 0 mensajes a grupos u otros chats del número anfitrión.
- **SC-004**: El catálogo tiene al menos 20 herramientas y una batería de al menos 40 consultas (≥ 2 por herramienta)
  lleva a la herramienta esperada en al menos el 90 % de los casos; 0 búsquedas ante 10 saludos o agradecimientos.
- **SC-005**: El 100 % de las herramientas de escritura piden confirmación antes de ejecutarse, en la web y en WhatsApp.
- **SC-006**: Tras reiniciar el servicio, 5 de 5 hilos de WhatsApp continúan, y un hilo nuevo recupera el perfil en 5 de
  5 casos.
- **SC-007**: El comando de reconstrucción del corpus termina sin intervención manual y el índice resultante tiene
  trazabilidad a la fuente en el 100 % de los fragmentos.
- **SC-008**: La evaluación sobre 30 consultas en el índice desplegado (servidor) no queda por debajo de la línea base
  del Módulo 2 (búsqueda híbrida, 2026-11-14: Recall@10 0,67 y nDCG@10 0,50) y reporta ambas cifras con su
  comparación; la proyección 2D ubica el 100 % de las consultas fallidas con su lectura escrita.
- **SC-009**: La auditoría de seguridad de OpenClaw termina sin hallazgos críticos, y la evaluación de inyección por
  WhatsApp registra 0 instrucciones obedecidas, 0 filtraciones del prompt y 0 escrituras sin confirmación.
- **SC-010**: Un escaneo de secretos del repositorio completo (incluido el historial) no encuentra claves ni sesiones.
- **SC-011**: Una persona ajena al equipo despliega el proyecto siguiendo solo la guía en menos de 2 horas.
- **SC-012**: El ensayo cronometrado completo cabe en 15 minutos (pitch ≤ 7) con la demo en el teléfono de una persona
  externa, y la autoevaluación de los 15 ítems queda en ≥ 4,5 ponderado con evidencia por ítem.
- **SC-013**: La prueba de 3 minutos del Anuncio 007 pasa completa en el servidor de la demo el viernes 27 de noviembre.

## Assumptions

- **Fuente**: el Anuncio 007 (copia local en `C:\Users\JCastano\Downloads\`) se guarda como referencia fuera de Git, igual
  que la rúbrica del Módulo 2 (`data/module2/`); el cumplimiento y el guion se documentan en
  `docs/rubrica_modulo3.md`, siguiendo `docs/rubrica_modulo2.md`.
- **Ruta A**: el catálogo se implementa con herramientas tipadas con esquemas Pydantic (la ruta que ya usa el proyecto),
  no con manifiestos HAND.toml.
- **Un solo agente**: OpenClaw aporta gateway, canales, workspace, skills/MCP y sandbox; el razonamiento, el router, la
  memoria y el RAG siguen siendo los de Valer-IA Caña, de modo que web y WhatsApp comparten comportamiento. La forma de
  conectarlos se decide en el plan.
- **Modelo**: DeepSeek por API es el modelo principal (ya configurado y con saldo); el respaldo puede ser otro modelo de
  DeepSeek u otro proveedor en la nube. Ollama queda solo para desarrollo, fuera de la demo.
- **Catálogo propuesto** (referencia para el plan, nombres finales en el plan): las 7 existentes
  (`search_documents`, `query_structured`, `aggregate_series`, `save_profile`, `save_preference`, `forget_memory`,
  `export_conversation`) más 13 nuevas sobre datos ya presentes en las capas oro y curadas: comparación de indicadores
  entre años, indicadores ambientales, unidades de negocio, presencia por país, productos, canales oficiales, FAQ,
  resumen de tema, noticias recientes, cita/fragmento por identificador, fecha y cálculo, perfil del usuario y solicitud
  de contacto humano (con confirmación). Ninguna herramienta nueva escribe en `data/`.
- **Voz en WhatsApp**: transcribir notas de voz con el dictado de la spec 023 es deseable, no obligatorio.
- **Servidor y túnel**: el PC del equipo debe quedar encendido, con suspensión desactivada, reinicio automático del
  servicio y conexión estable desde el viernes 27; el túnel no expone el gateway (que sigue en loopback con token),
  solo lo necesario. Se asume el riesgo, aceptado por el equipo, de que el evaluador lo perciba como equipo de un
  integrante; la guía de despliegue y el plan de contingencia lo mitigan mostrando que corre como servicio.
- **Plazo**: la sustentación es el sábado 28 de noviembre de 2026; todo lo obligatorio debe estar desplegado y verificado
  el viernes 27. Lo deseable (inglés, segundo canal, búsqueda web, LangSmith) se aborda solo si queda tiempo.
- **Invitados**: el registro de invitados en la pestaña 2 (nombre, cédula, cargo) es una tarea del equipo fuera del
  software; sus datos no se guardan en el repositorio.
- **Gobernanza**: commits y PRs los hacen solo los integrantes (ADR 0017); se mantienen la CI y la revisión de PRs.
