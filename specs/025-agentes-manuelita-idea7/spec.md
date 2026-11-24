# Feature Specification: Valer-IA como plataforma de agentes de Manuelita (idea 7) con planificación industrial

**Feature Branch**: `025-agentes-manuelita-idea7`

**Created**: 2026-11-24

**Status**: Draft

**Autor**: Roberto José Guerrero

**Input**: User description: "Enfoca el proyecto y producto final entorno a la idea 7 del markdown
`docs/alucinaciones/ideas_negocio_ia_manuelita.md`. Los requerimientos de este proyecto deben actualizarse en función
de dar cumplimiento a esta idea de proyecto y deben también estar alineados con los requerimientos del Módulo 3
compartidos por el docente en la rúbrica."

**Contexto**: La idea 7 propone agentes de IA generativa para los públicos de Manuelita. Son cuatro:

1. un asistente comercial B2B;
2. un agrónomo virtual para proveedores;
3. un copiloto interno para colaboradores;
4. un agente de planificación industrial (§7.4) que recomienda el mejor destino de cada tonelada de materia prima
   entre azúcar, etanol y energía.

La sustentación final del Módulo 3 es el **sábado 28 de noviembre de 2026** (Anuncio 007, `docs/rubrica_modulo3.md`).
El producto que existe hoy (spec 024) ya cumple casi todos los requisitos estructurales de la rúbrica: Valer-IA Caña
responde en WhatsApp por OpenClaw, tiene 20 herramientas, memoria, RAG sobre Qdrant, aprobación humana y blindaje.
Lo que esta spec cambia es el **producto**: deja de ser un asistente de preguntas para visitantes y pasa a ser una
**plataforma de agentes por perfil** que sirve a los públicos de la idea 7 con la misma arquitectura. Su
demostración estrella es el agente de planificación industrial.

## Clarifications

### Session 2026-11-24

- Q: ¿El agente de planificación (7.4) entra en la sustentación del sábado o queda como fase siguiente? → A: **Entra
  el sábado** como MVP, sobre **datos sintéticos declarados**: no hay acceso al ERP ni a los históricos de planta de
  Manuelita.
- Q: ¿Se reemplaza el producto actual? → A: No. Se **extiende**: el perfil por defecto (visitante) conserva la
  conducta evaluada en los Módulos 2 y 3, y la demo actual sigue siendo válida como respaldo.
- Q: ¿Qué datos usan los perfiles B2B, proveedor y colaborador? → A: Solo la información pública que ya está en la
  capa oro (fichas de productos, certificaciones, programas con proveedores, manuales PTEE, línea ética, seguridad y
  salud). El corpus interno real queda fuera del alcance y se declara como condición de un piloto con Manuelita.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Un planificador pide un programa de producción ante menos caña y recibe una recomendación explicada (Priority: P1)

Un planificador de planta escribe por WhatsApp o en la web: «Tenemos menor disponibilidad de caña esta semana.
Evalúa cómo cumplir los compromisos de azúcar y etanol y mantener el suministro energético». El agente:

1. consulta el estado de la planta (inventarios, capacidad disponible y equipos) y los compromisos (contratos de
   azúcar y etanol y energía comprometida);
2. recupera las restricciones operativas de los procedimientos;
3. ejecuta el simulador y el optimizador;
4. compara al menos dos alternativas por margen, energía exportable y cumplimiento;
5. responde con un plan recomendado, sus supuestos, la sensibilidad y la advertencia de que los datos son sintéticos
   y de que el equipo de planta decide.

Si el planificador lo aprueba con «SÍ», la propuesta se guarda para revisión.

**Why this priority**: Es el corazón de la idea 7 (§7.4) y la prueba más fuerte de los ítems 1.1 y 1.2: varias
herramientas encadenadas con un plan visible en la traza. También es el diferenciador del pitch (5.1).

**Independent Test**: Con el perfil planificador activo y los datos sintéticos generados con semilla, enviar la
solicitud de ejemplo y otra con una restricción de vapor. Hay que verificar cinco cosas:

- la traza muestra la secuencia de consulta, simulación, optimización y comparación;
- el plan no viola ninguna restricción dura;
- el margen alcanza el óptimo de referencia dentro de la tolerancia;
- la respuesta trae supuestos, alternativas y la advertencia;
- con «SÍ» la propuesta queda guardada y con «NO» no.

**Acceptance Scenarios**:

1. **Given** el perfil planificador y una semana con 15 % menos de caña, **When** el usuario pide cumplir azúcar,
   etanol y energía, **Then** el agente recomienda una mezcla de producción que cumple los contratos mínimos. La
   respuesta muestra el margen total, la energía exportable y qué restricción limita el resultado, y compara la
   recomendación con al menos una alternativa.
2. **Given** un escenario sin solución factible, **When** el usuario pide cumplir todos los compromisos, **Then** el
   agente dice que no es posible y nombra el compromiso o la restricción que lo impide. Además, propone la
   alternativa con el menor incumplimiento. Nunca inventa capacidad que la planta no tiene.
3. **Given** una recomendación, **When** el usuario pide guardarla, **Then** el agente describe la acción, pide «SÍ»
   y, solo tras «SÍ», guarda la propuesta con sus supuestos y la versión de los datos; vence a los 10 minutos.
4. **Given** el perfil visitante, **When** alguien pide un programa de producción, **Then** el agente explica que esa
   función es para planificadores autorizados y no ejecuta el optimizador.

---

### User Story 2 - Cada público recibe un agente con su propio foco y herramientas (Priority: P1)

Un usuario indica quién es («soy proveedor de caña», «compro azúcar para mi empresa», «trabajo en Manuelita») o usa el
comando `/perfil`. El agente adopta el perfil correspondiente:

- **cliente B2B**: productos, fichas, certificaciones y paso a un asesor para cotizar;
- **proveedor**: programas de apoyo, riego, control biológico y compost, siempre según los documentos públicos;
- **colaborador**: código de conducta, PTEE, línea ética, seguridad y salud;
- **planificador**: la historia 1, solo para usuarios autorizados.

El perfil activo se recuerda entre hilos con el consentimiento del usuario.

**Why this priority**: Convierte el asistente genérico en la plataforma de agentes de la idea 7 sin tocar la
arquitectura. Refuerza los ítems 1.2 (router y planificación por perfil), 1.3 (memoria de largo plazo) y 3.3
(workspace con reglas por perfil).

**Independent Test**: Ejecutar la batería de perfiles (consultas etiquetadas por perfil). Hay que verificar el perfil
detectado o elegido, el subconjunto de herramientas ofrecido y que una pregunta típica de cada perfil se responde con
citas. Después, reiniciar el backend y comprobar que el perfil persiste.

**Acceptance Scenarios**:

1. **Given** un usuario nuevo, **When** escribe «soy proveedor de caña, ¿qué apoyo dan a proveedores?», **Then** el
   agente propone activar el perfil proveedor y responde con los programas públicos citados (por ejemplo, control
   biológico y asesoría técnica). Si el usuario acepta con «SÍ», el perfil se guarda.
2. **Given** el perfil cliente B2B, **When** pide una cotización de azúcar orgánica, **Then** el agente informa las
   certificaciones y presentaciones públicas con citas. La cotización la ofrece por un asesor humano (solicitud de
   contacto con «SÍ»), nunca con precios inventados.
3. **Given** el perfil colaborador, **When** pregunta cómo reportar una situación ética, **Then** el agente responde con
   la línea ética y el procedimiento públicos, con sus citas.
4. **Given** cualquier perfil, **When** el usuario escribe `/perfil visitante`, **Then** vuelve a la conducta por
   defecto.

---

### User Story 3 - El equipo demuestra la plataforma en la sustentación sin perder lo ya evaluado (Priority: P1)

En los 7 minutos de pitch, el equipo presenta Valer-IA como la plataforma de agentes de la idea 7:

- un invitado prueba un perfil público (cliente o proveedor) desde su teléfono;
- un integrante con perfil planificador muestra la recomendación de producción;
- después se ve la traza (`/traza`) con el plan de pasos.

En la discusión técnica se muestran el simulador, el optimizador, el catálogo ampliado y las evaluaciones.

**Why this priority**: Los ítems 5.1 y 5.2 (10 %) y todos los ítems que dependen de la demo en vivo.

**Independent Test**: Ensayo cronometrado de 15 minutos el viernes 27 con un teléfono ajeno al equipo, con la
secuencia de la demo actual como respaldo si falla la parte de planificación.

**Acceptance Scenarios**:

1. **Given** el despliegue del sábado, **When** se ejecuta la secuencia de la demo, **Then** los pasos de perfil y
   planificación responden en WhatsApp dentro del tiempo objetivo, y la traza muestra las herramientas invocadas.
2. **Given** una falla del optimizador o del perfil planificador, **When** ocurre en plena demo, **Then** el agente
   responde con un mensaje controlado y el equipo continúa con la secuencia de respaldo (spec 024) sin reiniciar
   servicios.

---

### User Story 4 - El agente de planificación también cubre la planta de palma (Priority: P3)

El planificador elige la planta de palma y pide distribuir el aceite crudo entre aceite refinado, biodiésel y
derivados ante un cambio de demanda. Recibe una recomendación con el mismo formato que la de caña.

**Why this priority**: La idea 7.4 pide un modelo por planta, pero para la demo basta la planta de caña. La palma se
hace solo si las historias P1 están en verde antes del jueves 26.

**Independent Test**: Igual que la historia 1, con los datos sintéticos de palma.

**Acceptance Scenarios**:

1. **Given** el perfil planificador y la planta de palma, **When** cae la demanda de biodiésel, **Then** el agente
   redistribuye el aceite crudo dentro de las capacidades y explica el cambio de margen.

---

### Edge Cases

- El usuario declara un perfil que no corresponde a su pregunta: el agente responde la pregunta con las herramientas
  del perfil visitante y sugiere cambiar de perfil. No bloquea al usuario.
- Un usuario no autorizado intenta `/perfil planificador`: se le niega con cortesía, el intento queda en el registro
  sin el número y se le ofrece el perfil visitante.
- La solicitud de planificación es ambigua (no dice qué semana ni qué cambió): el agente pide una aclaración
  concreta en vez de suponer.
- La solicitud de planificación pide algo fuera del modelo, como cambiar la capacidad física, reprogramar
  mantenimiento o fijar precios de venta: el agente explica el límite del modelo y no lo simula.
- El optimizador tarda más que su límite de tiempo o falla: respuesta controlada, sin plan inventado y con la causa
  en el registro técnico.
- Valores fuera de rango (caña negativa, calidad imposible): el esquema de la herramienta los rechaza y el agente
  pide un valor válido.
- Inyección en un procedimiento sintético recuperado: rige el mismo blindaje de documentos que para el corpus
  público.
- Modo degradado (backend caído): el agente nativo de OpenClaw no planifica ni guarda propuestas. Solo responde con
  las herramientas de lectura públicas del MCP y avisa del «modo básico».

## Requirements *(mandatory)*

### Functional Requirements

**Perfiles de la plataforma (idea 7: 1–3; ítems 1.2, 1.3, 3.3)**

- **FR-001**: El sistema MUST ofrecer cinco perfiles:
  - **visitante** (por defecto, la conducta actual);
  - **cliente B2B**;
  - **proveedor**;
  - **colaborador**;
  - **planificador**.
- **FR-002**: Cada perfil MUST declarar en un solo lugar sus instrucciones de foco y el subconjunto de herramientas
  del catálogo que puede usar. El router MUST combinar la ruta (reglas → Jev → LLM) con el perfil para ofrecer
  solo esas herramientas, y la traza MUST mostrar el perfil activo.
- **FR-003**: El perfil MUST poder elegirse con un comando explícito (`/perfil <nombre>` en WhatsApp y un selector en
  la web). Si el usuario se presenta («soy proveedor…»), el agente MUST proponer el perfil y, con su aprobación,
  guardarlo en la memoria de largo plazo. MUST persistir entre hilos y reinicios, y `/olvidar` MUST borrarlo.
- **FR-004**: El perfil planificador MUST estar restringido a usuarios autorizados: una lista de seudónimos o el
  acceso de la web técnica configurado fuera del repositorio. Durante la jornada de sustentación, MAY habilitarse
  para los números emparejados que el equipo apruebe.
- **FR-005**: Los perfiles cliente, proveedor y colaborador MUST responder solo con información pública citada de la
  capa oro. Si la pregunta requiere información interna (precios, inventarios reales, datos de personas), el agente
  MUST decirlo y ofrecer el canal oficial o un asesor humano.
- **FR-006**: El perfil cliente B2B MUST canalizar las cotizaciones y compras por la solicitud de contacto humano
  existente, con aprobación «SÍ». MUST NOT dar precios ni condiciones comerciales.
- **FR-007**: El perfil proveedor MUST limitar sus recomendaciones agronómicas a lo que dicen los documentos públicos,
  con cita. MUST aclarar que no reemplaza la asistencia técnica de campo. La respuesta por voz es opcional y reutiliza
  la voz existente.

**Agente de planificación industrial (idea 7.4; ítems 1.1, 1.2)**

- **FR-008**: El sistema MUST incluir un **conjunto de datos sintéticos de planificación** para una planta de caña:
  - capacidades (molienda, vapor, destilería, cogeneración);
  - coeficientes de rendimiento por calidad de caña;
  - inventarios y estado de equipos;
  - contratos semanales de azúcar, etanol y energía;
  - márgenes unitarios;
  - un pequeño corpus de procedimientos operativos.

  Estos datos se generan con un script determinista y semilla fija, se versionan con su ficha de datos y se marcan
  como **sintéticos** en cada respuesta. MUST NOT mezclarse con el corpus público ni presentarse como datos de
  Manuelita. Sus valores de orden de magnitud MAY inspirarse en cifras públicas del oro (por ejemplo, la
  cogeneración del Informe 2023-2024), citándolas en la ficha.
- **FR-009**: El catálogo único MUST sumar al menos estas herramientas tipadas, con esquema estricto, descripción y
  ruta:
  - **lectura**: estado de planta, compromisos, búsqueda de procedimientos operativos (con citas propias,
    distinguibles de las públicas), simulación de un escenario y optimización del plan;
  - **escritura con aprobación**: guardar una propuesta de programación.

  Con ellas el catálogo pasa de 20 a 26 herramientas. El catálogo generado (`docs/herramientas.md`, `GET /api/tools`)
  MUST reflejarlas.
- **FR-010**: El **simulador** MUST calcular, para un escenario dado (caña disponible, calidad y reparto entre azúcar
  y etanol):
  - el balance de masa y energía: azúcar, etanol, bagazo, vapor y energía exportable;
  - el margen total;
  - las restricciones que se violan.

  Todo se calcula en código de forma determinista y sin el LLM.
- **FR-011**: El **optimizador** MUST encontrar, con programación lineal, el plan de máximo margen sujeto a:
  - las capacidades;
  - el vapor;
  - los contratos mínimos;
  - el suministro energético comprometido.

  MUST devolver el plan, la restricción que limita el resultado y la sensibilidad (cuánto cambia el margen al
  relajar cada restricción activa). Si no hay solución factible, MUST identificar el conflicto y devolver la
  alternativa de menor incumplimiento.
- **FR-012**: La respuesta de planificación MUST incluir:
  - el plan recomendado y al menos una alternativa con sus consecuencias;
  - los supuestos;
  - la etiqueta de datos sintéticos;
  - la frase de que el agente recomienda y el equipo de planta decide.

  Las cifras MUST salir de las herramientas, nunca del texto del modelo, igual que el resto de cálculos del proyecto.
- **FR-013**: El agente MUST registrar en la traza el plan de pasos de la solicitud (consulta, recuperación,
  simulación u optimización, comparación) y cada invocación con sus argumentos validados, su duración y su resultado.
- **FR-014**: Guardar una propuesta MUST pedir «SÍ/NO» con vencimiento de 10 minutos, igual que las demás escrituras.
  La propuesta MUST guardarse en el directorio de estado, fuera del repositorio, con los supuestos y la versión de
  los datos. MUST NOT conectarse con ningún sistema real de planta.
- **FR-015** (P3): El modelo de planificación MAY extenderse a una planta de palma (aceite crudo, refinado, biodiésel
  y derivados) con los mismos contratos de herramienta.

**Canal, seguridad y operación (ítems 3.x, 4.2; reglas de la spec 024 vigentes)**

- **FR-016**: Todo lo anterior MUST funcionar por WhatsApp a través del mismo `ChatService`, con formato de canal: un
  plan resumido en pocas líneas, con el detalle a pedido o en la web.
- **FR-017**: El servidor MCP de solo lectura MAY exponer las herramientas de lectura de planificación. El **modo
  degradado** MUST NOT simular, optimizar ni guardar propuestas.
- **FR-018**: El workspace de OpenClaw (`AGENTS.md`) MUST añadir las líneas rojas de la plataforma:
  - nada de precios ni condiciones comerciales;
  - nada de datos internos reales;
  - la planificación solo para autorizados y siempre marcada como sintética;
  - el agente recomienda y no ejecuta cambios de operación.
- **FR-019**: La evaluación de blindaje por el canal MUST incluir intentos de forzar el perfil planificador y de hacer
  que el agente afirme que los datos sintéticos son reales.

**Evaluación y documentación (ítems 2.3, 4.1, 4.3)**

- **FR-020**: MUST existir una **batería de planificación** fijada antes de evaluar: 12 escenarios sintéticos con
  semilla, que incluyen al menos 2 sin solución factible. Su óptimo de referencia MUST calcularse con un método
  independiente del optimizador del agente (por ejemplo, una búsqueda exhaustiva en una malla fina) y versionarse con
  la batería.
- **FR-021**: MUST existir una **batería de perfiles** de 20 consultas etiquetadas (al menos 4 por perfil) que mida el
  perfil detectado y el subconjunto de herramientas ofrecido.
- **FR-022**: Las evaluaciones existentes MUST volver a correrse y documentarse sin bajar de su último valor
  publicado: la exactitud de herramientas (88,4 %), las 0 búsquedas en triviales, el blindaje y el retrieval.
- **FR-023**: La documentación final MUST actualizarse:
  - README;
  - `docs/herramientas.md`;
  - `docs/rubrica_modulo3.md` (pitch y demo reenfocados);
  - ADR 0029;
  - la ficha de los datos sintéticos;
  - el diagrama de arquitectura con el componente de planificación.

### Key Entities

- **Perfil**: nombre, instrucciones de foco, herramientas permitidas, si requiere autorización. Se guarda por usuario
  en la memoria de largo plazo, con consentimiento.
- **Planta (sintética)**: identificador, tipo (caña o palma), capacidades, coeficientes de rendimiento, equipos y su
  estado, versión de los datos.
- **Compromiso**: producto (azúcar, etanol o energía), cantidad mínima por semana, prioridad.
- **Escenario**: caña disponible, calidad, reparto entre productos, restricciones adicionales (por ejemplo, vapor).
- **Resultado de simulación**: balances, margen, restricciones violadas.
- **Plan recomendado**: mezcla de producción, margen, restricciones activas, sensibilidad, alternativas, supuestos,
  versión de los datos.
- **Propuesta guardada**: plan recomendado, usuario (seudónimo), fecha, aprobación.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: En la batería de planificación, el plan recomendado alcanza al menos el 99 % del margen óptimo de
  referencia en los 10 escenarios con solución factible. Ningún plan viola restricciones duras (0 de 12). Los 2
  escenarios sin solución factible se detectan y explican (2 de 2).
- **SC-002**: En al menos 10 de los 12 escenarios, la traza muestra la secuencia completa (estado o compromisos,
  luego simulación u optimización, luego comparación), y el 100 % de las respuestas lleva la etiqueta de datos
  sintéticos y la frase de decisión humana.
- **SC-003**: En la batería de perfiles, el perfil correcto se detecta o aplica en al menos el 90 % de las consultas,
  y el subconjunto de herramientas ofrecido corresponde al perfil en el 100 %.
- **SC-004**: Una solicitud de planificación por WhatsApp se responde en 20 s o menos en el p95 de la batería. Las
  consultas de los otros perfiles mantienen el objetivo conversacional de la spec 024.
- **SC-005**: Sin regresión:
  - la exactitud de herramientas se mantiene en 88,4 % o más, medida con la batería vigente más los casos nuevos;
  - siguen las 0 búsquedas en consultas triviales;
  - el blindaje por el canal no tiene fugas, incluidos los casos nuevos de FR-019.
- **SC-006**: El ensayo del viernes 27 completa la demo reenfocada en 15 minutos o menos con un teléfono ajeno al
  equipo, y la secuencia de respaldo de la spec 024 también funciona.
- **SC-007**: `make check` en verde. Las pruebas del simulador, el optimizador, las herramientas nuevas y los
  perfiles corren sin red.

## Alineación con la rúbrica del Módulo 3

Cómo refuerza cada requerimiento los 15 ítems (`docs/rubrica_modulo3.md`, `CONSTITUTION.md` §8.4):

| Ítem | Peso | Aporte de esta spec |
|------|-----:|---------------------|
| 1.1 Function calling y 20 tools | 10 % | 26 herramientas tipadas, entre ellas simulador y optimizador con lógica real (FR-009 a FR-011) |
| 1.2 Razonamiento, planificación y router | 8 % | Planificación de varios pasos visible en la traza; herramientas por perfil y por ruta (FR-002, FR-013) |
| 1.3 Memoria por capas | 7 % | Perfil persistente entre hilos con consentimiento y `/olvidar` (FR-003) |
| 2.1 Pipeline del M1 | 5 % | Sin cambios; los datos sintéticos tienen su propio generador reproducible (FR-008) |
| 2.2 RAG sobre Qdrant | 6 % | Procedimientos operativos recuperables con citas propias, separados del corpus público (FR-009) |
| 2.3 Evaluación del conocimiento | 4 % | Retrieval sin regresión (FR-022), más las baterías de planificación y perfiles (FR-020, FR-021) |
| 3.1 Gateway OpenClaw | 8 % | Sin cambios de configuración; mismo gateway |
| 3.2 WhatsApp en producción | 10 % | `/perfil` y la planificación por WhatsApp (FR-003, FR-016) |
| 3.3 Workspace operativo | 7 % | Reglas por perfil y líneas rojas nuevas en `AGENTS.md` (FR-018) |
| 3.4 Skills/plugins/MCP | 5 % | MCP con las lecturas de planificación y modo degradado sin escrituras (FR-017) |
| 4.1 Código y pruebas | 7 % | Módulos de simulación y optimización con pruebas sin red (SC-007) |
| 4.2 Seguridad y hardening | 7 % | Planificador restringido, aprobación humana para guardar, blindaje con casos nuevos (FR-004, FR-014, FR-019) |
| 4.3 Documentación final | 6 % | ADR 0029, ficha de datos sintéticos, rúbrica y README reenfocados (FR-023) |
| 5.1 Elevator pitch | 6 % | Propuesta de valor de la idea 7: plataforma de agentes y planificación industrial (historia 3) |
| 5.2 Discusión técnica | 4 % | Simulador, optimizador, sensibilidad y diseño por perfiles como tema técnico propio |

Los «no se acepta» del Anuncio 007 siguen cubiertos:

- hay 20 herramientas o más;
- el canal es WhatsApp real;
- el modelo está en la nube;
- no hay claves en el repositorio.

Los datos sintéticos no son un «mock» del canal: son el insumo declarado de una capacidad de demostración.

## Assumptions

- No hay acceso al ERP, a los históricos de planta ni a documentos internos de Manuelita antes del sábado. Por eso,
  el agente de planificación es un MVP demostrativo sobre datos sintéticos. Su paso a un piloto real (idea 7.4:
  «una planta y una decisión concreta») queda como trabajo posterior a la sustentación.
- El modelo de planta es lineal y semanal. Rendimientos, vapor y energía son proporcionales a la caña procesada y a
  su reparto. Es suficiente para la decisión de mezcla y explicable en la discusión técnica, y no pretende
  representar la dinámica real de una fábrica.
- La programación lineal se resuelve con una biblioteca científica estándar que ya está en el entorno como
  dependencia transitiva y que se declarará de forma explícita.
- Las reglas de la spec 024 y la constitución 1.16.0 sobre WhatsApp, OpenClaw, seudónimos, catálogo único, MCP de
  solo lectura, SQLite y hardening siguen vigentes sin cambios.
- Calendario:
  - martes 24: requerimientos y plan;
  - miércoles 25: datos sintéticos, simulador, optimizador y herramientas;
  - jueves 26: perfiles, canal y evaluaciones;
  - viernes 27: ensayo y documentación;
  - sábado 28: sustentación.

  Si el miércoles por la noche el optimizador no está en verde, la planificación pasa a «demostración en la web» y
  la secuencia de WhatsApp vuelve a la de la spec 024.
- **Planta de palma (historia 4, P3): pendiente.** Se priorizaron las historias P1. El esquema de las herramientas
  acepta solo `plant_id="cana"`; la palma (aceite crudo, refinado, biodiésel y palmiste) queda para después de la
  sustentación con el mismo contrato (research R18, tareas T058–T059).

## Out of Scope

- Conexión con sistemas reales de Manuelita (ERP, historiadores de planta, SCADA) o con su corpus interno.
- Gemelo digital dinámico de la planta (idea 2), pronóstico de rendimiento de campo (idea 1) y optimización no
  lineal o estocástica.
- Precios, cotizaciones automáticas o condiciones comerciales.
- Ejecución de cambios de operación: el agente solo recomienda.
