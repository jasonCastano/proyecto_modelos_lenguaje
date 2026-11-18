# ADR 0023 — Habilidades de atención de call center para Valer-IA Caña

- **Estado**: aceptada
- **Fecha**: 2026-11-17
- **Autor**: Jason Alejandro Castaño
- **Relacionadas**: ADR 0019 (blindaje), ADR 0020 (voz), ADR 0022 (Valer-IA Caña);
  `specs/019-callcenter-skills/` (spec, plan, research R1–R16, contracts, tasks).

## Contexto

Desde la spec 018, Valer-IA respondía con **una frase fija por motivo** a todo lo que estaba fuera de Manuelita.
Quien preguntaba por el clima, por una receta o por un medicamento recibía el mismo texto, sin que se reconociera
qué había pedido ni cómo se sentía. Tampoco quedaba registro de lo que pasaba en cada contacto.

El equipo pidió que Valer-IA manejara esas situaciones de forma natural, como un agente de call center:
- empatía, paciencia, resiliencia y amabilidad;
- escucha activa, claridad verbal y asertividad;
- capacidad de aprendizaje, multitarea y organización (registro en un CRM).

## Decisión

1. **Composición determinista desde guiones versionados** (`prompts/care.md` 1.0, `agent/care.py`):
   - las respuestas a temas ajenos, consejos profesionales y pedidos no atendibles se arman con piezas:
     apertura según la emoción, reconocimiento del tema, límite cordial, puente a Manuelita con cita al oro y
     pregunta de cierre;
   - cada pieza tiene variantes que rotan en el hilo sin repetirse;
   - no pasan por el modelo, así que no pueden aportar hechos externos.
2. **Análisis del mensaje por reglas**:
   - emoción (neutral, satisfecho, confundido, frustrado, molesto, angustiado), rechazo, sarcasmo, crítica,
     hostilidad y crisis;
   - división en hasta cinco solicitudes, con un catálogo de 14 temas ajenos y tres tipos de pedido no atendible
     (precio, compromiso, hablar con una persona).
3. **Apertura empática antepuesta en `finalize`**, igual que el aviso de datos sensibles de la spec 018. El prompt
   del agente (1.5) le indica al modelo que no abra con su propia frase empática.
4. **Crisis primero**: los mensajes de angustia grave reciben una respuesta de apoyo con la **Línea 106** (línea
   nacional de salud mental del Ministerio de Salud, gratuita y 24 horas) y el **123**. No llevan puente ni
   contenido comercial y se evalúan antes que cualquier otra regla.
5. **Insultos**: la respuesta fija de la spec 018 solo se usa si el mensaje es únicamente hostil. Si trae una
   consulta, se responde con un límite cordial antepuesto. Los límites escalan en tres niveles sin cerrar la
   atención.
6. **Varias solicitudes**: la cadena busca por cada parte de Manuelita y fusiona la evidencia. El modelo recibe un
   brief «Atención:» con las solicitudes en orden, y las partes ajenas se declinan al final de la respuesta.
7. **Canales solo del corpus**: sitio web oficial, Línea Ética y `protecciondedatos@manuelita.com`, cada uno con
   cita. Un teléfono o correo de la respuesta que no salga de un canal citado ni de la evidencia se reemplaza por
   el sitio oficial.
8. **Registro del contacto (CRM)** en el estado del hilo:
   - guarda solicitudes con categoría, tema y estado, la evolución emocional, el motivo, si quedó resuelto, la
     hostilidad y la crisis;
   - usa solo etiquetas controladas, sin texto del visitante ni `user_id`, así que no puede contener datos
     personales;
   - se ve únicamente en la vista técnica.
9. **Evaluación**: la batería `agent care` (36 casos) mide SC-001 a SC-010 en modo demo y real, con línea base de
   latencia (`[care] enabled = false`) y una sección para la calificación humana.

## Alternativas consideradas

- **LLM que redacta la declinación, con un validador de salida**: suena más natural, pero detectar "hechos
  externos" en texto libre no es verificable al 100 %. Además suma una llamada por turno y rompe la paridad del
  modo demo. Queda como mejora futura.
- **Clasificador de sentimiento entrenado**: añade dependencias y peso al servidor sin una ganancia clara para
  seis clases en un chat corto (Principio VII).
- **CRM en el Store por usuario o resumen libre del LLM**: liga el registro al visitante y puede filtrar datos
  personales.

## Consecuencias

- Las respuestas fuera de alcance nombran el tema y varían, pero su naturalidad depende de la calidad de los
  guiones. Mejorarlas es editar `prompts/care.md` sin tocar código.
- Las reglas de emoción y de temas son léxicas: no captan todo matiz, y lo que no reconocen lo decide el
  enrutador LLM con `topic` y `sentiment` opcionales y saneados.
- La batería de conducta de la spec 018 verifica `off_topic` y `advice` por contenido y motivo, no por texto
  exacto. Los motivos de seguridad conservan su texto.
- `[care] enabled = false` en `config/agent.toml` devuelve el comportamiento de la spec 018 (línea base).
