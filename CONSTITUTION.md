# Constitución del Proyecto — RAG Ingenio Manuelita

**Versión**: 2.11.1 | **Ratificada**: 2026-10-29 | **Última enmienda**: 2026-11-28

**Equipo**: Jason Alejandro Castaño · Roberto José Guerrero

**Curso**: Técnicas Avanzadas de IA aplicadas en Modelos de Lenguaje — Maestría en IA y Ciencia de Datos,
Universidad Autónoma de Occidente, 2026-2S

**Docente**: Jan Polanco Velasco

**Empresa**: Ingenio Manuelita S.A. — Valle del Cauca, Colombia — https://www.manuelita.com/

**Repositorio**: https://github.com/jasonCastano/proyecto_modelos_lenguaje

**Mantenedor**: Jason Alejandro Castaño — GitHub `@jasonCastano` — `jasonale3007@gmail.com`

**Alcance**: proyecto de curso organizado en fases (Módulo 1, Módulo 2 y módulos siguientes). Esta constitución
rige la creación, ejecución, evaluación y entrega de cada fase.

> **Prevalencia**: este es el documento canónico del proyecto para el curso. `.specify/memory/constitution.md`
> es la constitución operativa de la herramienta Spec Kit y debe mantenerse alineada; ante conflicto, prevalece
> este documento. Toda enmienda debe reflejarse en ambos antes de iniciar una fase.

---

## 1. Propósito y alcance

El proyecto construye un asistente de preguntas y respuestas sobre información pública de Ingenio Manuelita,
con un corpus trazable y una arquitectura que evoluciona desde una base de conocimiento con Prompt Engineering
(Módulo 1) hacia un sistema RAG con embeddings, memoria y recuperación (Módulo 2), y finalmente un chatbot
evaluado y desplegable.

La cátedra define el Proyecto Integrador en tres fases con pesos **30 % · 30 % · 40 %**:
**Fase 1** ingesta y base semántica; **Fase 2** agente con memoria y enrutador (base vectorial/RAG, memoria
multi-turno y enrutamiento documental vs. estructurado SQL/CSV); **Fase 3** productización y despliegue (FastAPI /
Agent OS, persistencia de estado y canales reales como WhatsApp o Telegram).

Esta constitución es obligatoria para los dos integrantes. Aplica a código, datos, prompts, modelos,
interfaces, pruebas, documentación, repositorio, presentación y uso de herramientas de IA.

**Producto final** (enmienda 2.0.0, spec 025, ADR 0029): Valer-IA es la **plataforma de agentes de Manuelita**
de la idea 7 de [`docs/alucinaciones/ideas_negocio_ia_manuelita.md`](docs/alucinaciones/ideas_negocio_ia_manuelita.md).
Es un solo agente con perfiles:

- **visitante**: la conducta evaluada en los Módulos 2 y 3;
- **cliente B2B**;
- **proveedor**;
- **colaborador**;
- **planificador industrial**: recomienda el mejor destino de la materia prima entre azúcar, etanol y energía, con
  un simulador y un optimizador sobre datos sintéticos declarados.

Los perfiles públicos responden solo con información pública citada. La planificación demuestra la capacidad y no
afirma resultados sobre la operación real de Manuelita.

**Criterio de éxito**: cumplir la rúbrica del curso, demostrar el sistema en vivo y poder explicar cada
decisión técnica sin depender de diapositivas ni de la memoria de una sola persona.

---

## 2. Principios no negociables

### I. Integridad académica y autoría

- Todo entregable DEBE ser producido por Jason Alejandro Castaño y Roberto José Guerrero, o declarar
  explícitamente la herramienta de IA utilizada como asistencia.
- La autoría en Git y GitHub (autor, coautor y firma de commits y PRs) DEBE corresponder solo a los integrantes
  del equipo (§4.3). Ningún asistente de IA ni bot DEBE figurar como autor, committer ni contribuidor; el uso
  de asistentes se declara en la documentación (principio IX).
- NO SE DEBE inventar información, citas, métricas, resultados, fuentes ni retroalimentación.
- Toda idea, dataset, imagen o fragmento externo DEBE citarse con su fuente y licencia.
- Los resultados reportados DEBEN provenir de ejecuciones reales del sistema, no de ejemplos escritos a mano.
- NO SE DEBE copiar el trabajo de otro equipo ni reutilizar entregables de cursos anteriores sin declararlo.

**Razón**: la evaluación premia la solvencia técnica y la honestidad; un resultado fabricado invalida el
aprendizaje y la sustentación.

### II. Reproducibilidad y entorno único

- El proyecto DEBE reconstruirse con `uv sync --frozen` desde un clon limpio.
- `pyproject.toml`, `uv.lock` y `.python-version` DEBEN estar versionados y ser consistentes.
- NO SE DEBE usar `pip`, `conda` ni entornos manuales para el flujo oficial.
- Toda ejecución relevante DEBE registrar comando, configuración, versión del modelo, semilla (si aplica) y
  fecha.
- Los datos y artefactos pesados se versionan por **Git LFS** (bronce, plata y oro); la cuarentena,
  cachés y artefactos temporales quedan fuera. Todo conjunto se referencia por manifiesto y hash.
- La app DEBE correr con el comando documentado, sin pasos manuales no registrados.

**Razón**: la rúbrica exige un repositorio que corra desde cero; la reproducibilidad es la condición mínima
para defender el proyecto.

### III. Procedencia, ética y legalidad de los datos

- Solo se recolecta información pública y accesible sin autenticación ni elusión de controles.
- El scraping DEBE respetar `robots.txt`, `sitemap.xml`, los términos de servicio, el `User-Agent`
  identificable, el timeout y el rate limit.
- NO SE DEBE recolectar datos personales sensibles ni contenido privado; los nombres y cargos corporativos
  públicos se admiten con fines académicos.
- Cada artefacto DEBE conservar URL, título, sección, fecha de captura en UTC, hash SHA-256, fuente, tipo de
  contenido e idioma.
- Los datos crudos son inmutables; toda limpieza o transformación DEBE ser un paso versionado y reversible.
- El contenido retirado por solicitud legítima DEBE excluirse del corpus activo sin borrar el registro de
  procedencia.

**Razón**: el proyecto trabaja con contenido de terceros; la trazabilidad y el uso legítimo protegen la
validez académica y a las personas representadas en los datos.

### IV. Generación anclada al contexto y trazabilidad de fuentes

- El sistema DEBE responder únicamente con base en el contexto recuperado del corpus de Manuelita.
- Toda respuesta factual DEBE citar la fuente o el fragmento que la sustenta.
- Si no hay evidencia suficiente, el sistema DEBE responder que no cuenta con información y NO DEBE inventar.
- Los prompts DEBEN incluir instrucciones explícitas contra alucinaciones, uso de contexto y formato de
  citación.
- El contenido scrapeado es dato no confiable: DEBE delimitarse como contexto y nunca ejecutarse como código
  ni como instrucción del sistema.
- Cada Prompt DEBE tener versión, fecha, modelo, parámetros y resultado observado.

**Razón**: el valor del asistente depende de que sus respuestas sean verificables; una respuesta sin fuente no
es evidencia.

### V. Evaluación empírica antes de afirmar

- Ninguna mejora de modelo, prompt, chunking o recuperación se declara exitosa sin una medición previa.
- El Módulo 1 DEBE evaluarse con al menos 20 preguntas del alcance definido.
- Cada evaluación DEBE registrar pregunta, respuesta, fuente citada, corrección, coherencia y presencia de
  alucinaciones.
- Las comparaciones de prompts DEBEN incluir una línea base (por ejemplo, zero-shot) y la variante mejorada.
- Los resultados DEBEN reportar media y dispersión cuando el proceso sea estocástico.
- Las limitaciones y fallos DEBEN documentarse; ocultarlos invalida el análisis.

**Razón**: la rúbrica evalúa la calidad del Prompt Engineering y la documentación del proceso, no solo el
resultado final.

### VI. Repositorio, licencia y trazabilidad como producto

- El repositorio DEBE ser público en GitHub y contener `LICENSE` MIT con año 2026 y titulares Jason Alejandro
  Castaño y Roberto José Guerrero.
- La licencia DEBE declararse en `README.md` y en `pyproject.toml`.
- El historial DEBE usar Conventional Commits, commits atómicos y mensajes que expliquen el porqué.
- NO SE DEBEN versionar binarios, datos, `.env`, credenciales ni artefactos generados.
- Cada cambio DEBE integrarse por Pull Request revisado por el otro integrante; el autor no aprueba su propio
  PR.
- Antes de la sustentación del Módulo 1 DEBE haber al menos 2 PR fusionados con descripción, revisión y checks
  verdes.

**Razón**: la rúbrica asigna 45% a repositorio, commits, README y licencia; el repositorio es parte del
producto evaluado.

### VII. Simplicidad, incrementalidad y alcance

- Cada fase DEBE entregar el producto mínimo que cumpla la rúbrica, sin infraestructura innecesaria.
- NO SE DEBE añadir una dependencia, servicio o abstracción sin justificar el problema que resuelve.
- El alcance del Q&A DEBE definirse por escrito antes de implementar y mantenerse acotado.
- Los compromisos de diseño DEBEN registrarse en una decisión de arquitectura.
- Una fase no inicia si la anterior no ha pasado su puerta de calidad.

**Razón**: el curso evalúa comprensión y ejecución, no complejidad; el alcance acotado protege la fecha de
entrega y la calidad de la demostración.

### VIII. Colaboración, revisión cruzada y bus factor 2

- Ambos integrantes son coautores y responsables de todos los entregables.
- Cada PR DEBE ser revisado por el integrante distinto al autor.
- Ninguna persona puede ser el único punto de conocimiento de un componente.
- Las decisiones de alcance, modelo, arquitectura y evaluación se toman por consenso y se registran.
- Las tareas y su responsable DEBEN estar visibles en el repositorio o en el tablero del equipo.

**Razón**: la sustentación es individual y en vivo; ambos deben poder explicar cualquier parte del sistema.

### IX. Transparencia en el uso de IA y en las decisiones

- El uso de asistentes de IA DEBE declararse en el README o en la documentación del proyecto.
- Las respuestas, prompts y código generados con IA DEBEN revisarse, probarse y adaptarse; no se aceptan como
  verdades sin verificación.
- Las decisiones técnicas relevantes DEBEN quedar en `docs/decisions/` o en Engram, con contexto y alternativas.
- Los experimentos de prompting DEBEN conservar el historial de versiones y resultados.

**Razón**: la transparencia permite defender el trabajo y distinguir la asistencia legítima de la fabricación.

---

## 3. Estándares técnicos obligatorios

### 3.1 Entorno y dependencias

- Python 3.14 o superior, gestionado exclusivamente con `uv`.
- Node.js 24 para el frontend web; `package-lock.json` versionado y `npm ci` reproducible.
- Estructura `src/` para el paquete `proyecto_modelos_lenguaje` y `web/` para React/Vite.
- API con FastAPI + Uvicorn; Ruff para lint/formato y `pytest`/Vitest para pruebas.
- Voz del agente con **Phonon** (paquete `ptts`, runtime local sin PyTorch; modelo `gradium/phonon-40m-es`).
  El modelo y sus voces son **CC BY-NC 4.0** (uso académico, no comercial) y el motor es MIT/Apache-2.0; el
  modelo se descarga a la caché de Hugging Face, nunca al repositorio (spec 016, ADR 0020).
- Dictado por voz con **faster-whisper** (CTranslate2 en CPU, modelo `base` `int8`, Silero VAD) en el servidor; sin
  servicios de terceros. Motor, pesos y VAD con licencia MIT; el modelo se descarga a la caché de Hugging Face,
  nunca al repositorio (spec 023, ADR 0027).
- **Canal y gateway** (spec 024, ADR 0028): **OpenClaw** (`npm i -g openclaw`, plugin `@openclaw/whatsapp`) y
  Docker Desktop (Qdrant servidor y sandbox) se instalan en el PC servidor, fuera del paquete. **TypeScript
  sobre Node ≥ 24.16 solo para el plugin puente** `openclaw/plugins/valeria-bridge` (lógica pura, pruebas
  `node --test`); el backend sigue siendo solo Python.
- Dependencias Python añadidas en la Fase 3: `mcp` (SDK oficial del servidor MCP), `scikit-learn` (t-SNE) y
  `matplotlib` (figura de la proyección). UMAP queda descartado por compatibilidad con Python 3.14.
- Dependencias de runtime y desarrollo separadas; versiones fijadas en `uv.lock` y `package-lock.json`.
- Variables de entorno para claves y configuración sensible; `.env` fuera del repositorio.

### 3.2 Estructura del repositorio

```text
web/                           # frontend React + Vite + TypeScript
src/proyecto_modelos_lenguaje/ # paquete: API FastAPI, datos, prompts, LLM, RAG
scripts/                       # entradas operativas reproducibles y auditoría visual
config/                        # fuentes, reglas y parámetros versionados
openclaw/                      # gateway OpenClaw: configuración sin secretos, workspace y plugin puente
data/                          # capas medallion versionadas por Git LFS
specs/                         # especificaciones, planes y contratos
tests/                         # unitarias, integración, contrato y visuales
docs/                          # alcance, decisiones, arquitectura, informe, prompt log
.github/                       # PR/issue templates, CI y labels
.opencode/                     # comandos y skill de bitácora (generador compartido)
.claude/skills/                # skills de Claude Code (speckit-*, bitacora)
AGENTS.md                      # contexto para asistentes LLM
CONTRIBUTING.md                # guía de contribución
Makefile                       # interfaz de comandos
README.md
CONSTITUTION.md
LICENSE
pyproject.toml
uv.lock
.python-version
```

### 3.3 Datos y capas medallion

| Capa | Ruta del proyecto | Equivalente en la rúbrica | Contenido |
|------|-------------------|---------------------------|-----------|
| Bronce | `data/bronze/` | `data/raw/` | Bytes originales, inmutables, con metadata y hash |
| Plata | `data/silver/` | `data/processed/` | Texto limpio, normalizado y chunks |
| Oro | `data/gold/` | `data/gold/` | Base de conocimiento consolidada y material listo para el LLM |

- La equivalencia DEBE explicarse en `README.md` o en `data/README.md`.
- Cada artefacto DEBE incluir: `url`, `title`, `section`, `retrieved_at` (UTC), `content_hash`, `source_id`,
  `media_type`, `language` y nota de licencia/uso.
- Los outputs DEBEN ser JSONL y/o Markdown con frontmatter YAML.
- La deduplicación DEBE ser por hash de contenido; las URL alternas se conservan como alias.
- El corpus activo DEBE excluir contenido irrelevante o retirado; los retiros conservan auditoría.
- El presupuesto de almacenamiento de la capa bronce es 10 GB. Bronce, plata y oro se versionan por
  Git LFS; la cuarentena, cachés y temporales no se versionan.

### 3.4 Pipeline de scraping

- Framework principal: `scrapling`, decisión registrada como equivalente a `requests`/BeautifulSoup/Selenium.
  La cátedra sugiere esas librerías; el proyecto usa `scrapling` por decisión registrada y cumple los mismos
  requisitos de robots, sitemap, User-Agent, timeout, rate limit y trazabilidad.
- Etapas obligatorias y visibles: **descubrir → extraer → limpiar → deduplicar → enriquecer**.
- DEBE respetar `robots.txt`, `sitemap.xml`, `User-Agent`, timeout, reintentos y rate limit por host.
- DEBE producir métricas: URLs descubiertas, páginas extraídas, tokens, descartes y bytes almacenados.
- DEBE exponer una entrada canónica `scripts/scrape_empresa.py` ejecutable con
  `uv run python scripts/scrape_empresa.py`. Puede ser un wrapper del pipeline existente.
- La ejecución DEBE ser idempotente y reanudable; los fallos se registran sin abortar todo el corpus.
- La capa bronce no se modifica in situ; la limpieza ocurre en plata/oro.

### 3.5 Modelo, framework y tareas del Módulo 1

- LangChain es el framework obligatorio para las tres tareas del Módulo 1: **Resumen**, **FAQ** y **Q&A**.
  Cualquier alternativa requiere justificación escrita y aprobación del docente.
- El proveedor del Módulo 1 es **DeepSeek por API**, con modo demostración offline. La elección se justifica
  por costo, latencia, calidad, idioma y disponibilidad.
- La configuración del modelo (nombre, versión, temperatura, límite de contexto, tokens) DEBE estar en
  `config/` o variables de entorno documentadas.
- Las claves de API NO se versionan; se leen de `.env` o del gestor de secretos y nunca llegan al navegador.
- El texto limpio consolidado DEBE residir en `data/gold/` y caber en la estrategia de contexto definida; si
  excede la ventana, se aplica chunking/recuperación documentada.

### 3.6 Prompt Engineering

- Todo prompt DEBE declarar: rol, tarea, contexto delimitado, reglas de respuesta, formato de citación y
  comportamiento ante falta de información.
- El prompt de Q&A DEBE prohibir el uso de conocimiento externo al contexto y exigir cita de fuente.
- Se DEBE mantener un `docs/prompt_log.md` con versión, fecha, modelo, parámetros, prompt completo, resultado
  observado y decisión.
- Se DEBEN documentar al menos: línea base zero-shot, variante con formato estructurado y variante con
  instrucciones anti-alucinación.
- Los prompts DEBEN versionarse en el repositorio; no se aceptan prompts solo en la memoria del equipo.

### 3.7 Aplicación web

- La entrada del producto es una página React/Vite servida por FastAPI; Streamlit, Gradio y los notebooks NO DEBEN
  ser la interfaz de ninguna pantalla.
- **Video pitch** (specs 028 y 029, ADR 0032 y 0033): la entrada abre con un video de 60 s o menos que explica
  Valer-IA y cómo usarla. Desde la v2, lo que se ve sigue a la narración: cada escena dura su narración más una
  pausa, y los iconos y perfiles son gráficos del montaje que entran con su palabra. Es el primer elemento; arranca sin sonido y con subtítulos en español; se salta en un paso; no se impone
  dos veces en la misma sesión; con movimiento reducido no arranca solo. La web DEBE funcionar sin el video
  (portada y transcripción).
- **Plataforma en cuatro áreas** (spec 026, ADR 0030): `/` entrada pública, `/agente` espacio de trabajo por perfil,
  `/planificacion` consola del planificador y `/evidencia` panel técnico del Módulo 3, cada una con su dirección.
  - Los servicios nuevos viven bajo `/api/v1/` (`api_planning.py`, `api_evidence.py`); las rutas sin versión que
    usan el canal y la web NO DEBEN cambiar de forma.
  - En la web, los cinco perfiles y `/api/v1/planning/*` son de libre elección (spec 027, ADR 0031). La
    autorización por canal vive en el backend (`profiles.is_authorized`) y la UI NO DEBE reemplazarla ni bloquear
    perfiles por su cuenta. Cada llamada de la consola DEBE registrar el seudónimo de la sesión.
  - Las cifras de planta NO DEBEN calcularse en el navegador: la consola dibuja lo que devuelve el mismo optimizador
    del agente y del CLI, y una prueba de paridad lo verifica en la batería de 12 escenarios.
  - Guardar una propuesta desde la consola exige confirmación en dos pasos con vencimiento de 5 minutos.
  - Identidad visual (`specs/026-plataforma-web-manuelita/design.md`): una sola familia tipográfica (Archivo
    variable, el ancho marca el rol), un color fijo de la paleta de Manuelita por producto (caña, azúcar, etanol,
    energía), pictogramas propios sin piezas de la marca, contraste AA y sin desplazamiento horizontal de 360 a
    1920 px.
  - Sitio de producto (spec 031, ADR 0035): la entrada es una página de una sección por pantalla con el video
    pitch como visual del hero, hecha con la skill `design-taste-frontend` sin copiar su kit (no tiene licencia):
    sus reglas se reimplementan en `web/src/styles/` y sus scripts (gate, copy-lint, fotos) se usan como
    herramientas externas. Paleta de marca con los colores del logotipo de Manuelita (verde `#497536` para las
    acciones; rojo anaranjado, naranja y amarillo en filetes y hojas), nunca su logotipo, figura ni tipografía.
    Las fotos son sustitutas de Wikimedia Commons con licencia libre (CC0, dominio público, CC BY o CC BY-SA),
    sin marca ni personas reconocibles, nunca presentadas como de Manuelita, con autor y licencia en
    `web/public/media/fotos/CREDITOS.md` y una línea de créditos en el pie. Un solo momento animado, dentro de
    su sección y quieto con «reducir movimiento».
  - Pestaña WhatsApp (spec 032, ADR 0038): quinta área `/whatsapp` con el enlace al chat de Valer-IA (WhatsApp
    Web en computador, la aplicación en teléfono, siempre en una pestaña nueva) y un QR generado en el servidor
    con `segno`, sin servicios externos. El número sale solo de `VALERIA_WHATSAPP_NUMBER` en el `.env` del
    proyecto (E.164 con indicativo, fuera de Git) y lo expone `GET /api/channels/whatsapp`, público y de solo
    lectura, únicamente dentro del enlace y el QR. Sin número válido no hay enlace ni QR: la pestaña lo dice y
    lleva al Agente. El número no se registra (regla 10).
- La app DEBE ejecutarse con `make app` o `uv run python -m proyecto_modelos_lenguaje.webbuild --serve` desde un
  clon limpio. `web/dist` no se versiona: ambos compilan la web si falta o si sus fuentes cambiaron (huella en
  `web/dist/.build-stamp`) y repiten `npm ci` si cambió `package-lock.json`. Arrancar `uvicorn` a mano con una
  compilación vieja DEBE advertirlo en la consola. `make app` NO DEBE arrancar sobre un puerto ocupado por otra
  versión: compara con `GET /api/version` (commit y compilación web) y explica cómo cerrarlo o usar `PORT`. Las
  páginas se sirven con `Cache-Control: no-cache` y los recursos con hash como inmutables.
- DEBE mostrar tres funcionalidades: Consulta, Resumen y FAQ, con citas y fallback.
- DEBE incluir una página del Módulo 1 con datos, arquitectura, prompts, app, métricas y límites.
- DEBE incluir modo demostración explícito, estados de carga y errores accionables.
- El chat del agente lee sus respuestas en voz alta en español, por oraciones y mientras se generan
  (`POST /api/tts`, `GET /api/voice`). El visitante puede silenciarla, detenerla y volver a escucharla; si la
  voz no está disponible, el chat sigue igual por texto (spec 016).
- El visitante puede **hablarle** a la asistente con el micrófono (spec 023, ADR 0027): la voz se convierte en texto
  en el servidor (`POST /api/stt`) y entra al campo del mensaje para revisarlo, o se envía sola en el modo
  opcional manos libres. El permiso se pide al pulsar el micrófono, nunca al cargar. Un mensaje dictado sigue el
  mismo camino que uno escrito; si el dictado no está disponible, el chat y la voz siguen igual.
- La asistente se presenta como **Valer-IA Caña** (spec 018, ADR 0022): da la bienvenida al entrar, se declara
  inteligencia artificial y NO DEBE presentarse como canal oficial ni autorizado de Manuelita (§10). La vista
  normal es para visitantes; la vista técnica (`?vista=tecnica`) conserva la demostración de la rúbrica.
- Cada visita empieza con un cliente anónimo limpio. El reconocimiento por correo es opcional, conversacional y
  determinista (huella HMAC más el nombre registrado); el correo en claro NO DEBE persistirse ni enviarse al modelo.
- Valer-IA atiende como un agente de call center (spec 019, ADR 0023). Los temas ajenos, los consejos
  profesionales y los pedidos que no puede cumplir (precios, compromisos, hablar con una persona) se responden
  desde guiones versionados (`prompts/care.md`): nombran el tema, ponen un límite cordial y ofrecen un puente a
  Manuelita con cita. Esas respuestas NO DEBEN aportar hechos externos. La emoción del visitante se reconoce al
  inicio, los insultos reciben un límite cordial sin cerrar la atención y los canales oficiales solo se mencionan
  si están en el corpus con su cita.
- Conversación guiada (spec 020, ADR 0024): fuera de los casos de seguridad, Valer-IA **redacta** cada respuesta
  sin búsqueda con el modelo, guiada por un plan del turno determinista, y la respuesta DEBE pasar una revisión
  por reglas antes de mostrarse (hechos externos, contactos, promesas, citas, repetición y opiniones). Si la
  revisión falla dos veces o el modelo no responde, se usa la composición de los guiones como respaldo. Esas
  respuestas NO DEBEN transmitirse token a token antes de revisarse. Las recomendaciones de temas de Manuelita
  son opcionales, con cuota, citadas y sin repetirse en el hilo. Las respuestas de crisis, datos de terceros,
  extracción de instrucciones, daño, insulto solo, identidad y perfil conservan su texto fijo.
  `[conversation] mode = "scripted"` restablece los guiones de la spec 019 como línea base.
- Entrega por frases revisadas (spec 021, ADR 0025): las respuestas redactadas por el modelo (conversación y
  búsqueda) se entregan frase por frase, y cada frase DEBE pasar la revisión antes de mostrarse. Lo mostrado NO
  DEBE retirarse ni reemplazarse: la respuesta final es la secuencia de frases entregadas, más las frases de cierre
  que haga falta agregar. `[conversation] delivery = "complete"` restablece la entrega completa de la spec 020.
- Gatekeeper System One (spec 022, ADR 0026): el enrutador puede consultar a **Jev** (TypeSafe) entre las reglas y el
  clasificador LLM, con **una** solicitud por turno y versión fija (`jev-1.14.0`). Las reglas siempre ganan; Jev
  decide la ruta solo si su probabilidad alcanza `[jev].route_threshold`. Cualquier fallo de Jev DEBE resolverse con
  el clasificador sin afectar la respuesta. Jev puede **sumar** una crisis a la detección determinista, nunca
  quitarla. El texto enviado se enmascara (correos, teléfonos, documentos) y la clave `TYPESAFE_API_KEY` solo vive
  en `.env`. Está **desactivado por defecto** (`[jev].enabled = false`) mientras no cumpla la tolerancia de
  exactitud de su spec; las instrucciones viven en `prompts/jev.md`.
- Un mensaje de angustia grave o de autolesión DEBE recibir primero una respuesta de apoyo con la Línea 106
  (salud mental, Ministerio de Salud) y el 123, sin contenido comercial, por encima de cualquier otra regla.
- El registro del contacto (CRM) de cada conversación guarda solo etiquetas controladas (categoría, tema,
  estado y emoción). NO DEBE contener texto del visitante, nombres, correos ni el identificador del cliente, y
  solo se muestra en la vista técnica.
- Junto al chat hay un **avatar ilustrado** del agente que mueve la boca con el audio de la voz, analizado en el
  navegador sin servicios externos (spec 017, ADR 0021). La ilustración DEBE ser original: no imita a personas
  reales ni usa la marca de Manuelita. Respeta `prefers-reduced-motion` y se puede ocultar.
- DEBE usar la paleta corporativa y motivos de producto definidos en el contrato UI.
- NO DEBE exponer claves, rutas absolutas ni datos sensibles; la API no devuelve la clave.

### 3.8 Pruebas y calidad

- `uv run pytest` DEBE pasar sin red para las pruebas unitarias y de contrato. Las pruebas que requieren red o
  claves se marcan `network` y las que requieren el modelo de voz se marcan `voice`; ambas quedan fuera por
  defecto y en la CI.
- `make check` DEBE ejecutar Ruff (lint + formato), `pytest` y la verificación web (Vitest + build); el CI corre ambos jobs.
- La app DEBE auditarse con `make e2e` (Playwright) en los perfiles responsive definidos por la feature 012.
- Cada módulo crítico (scraping, chunking, prompts, recuperación, app) DEBE tener al menos una prueba.
- `uv run ruff check .` DEBE pasar sin errores.
- Un PR no se fusiona con pruebas fallidas, lint pendiente o conflictos sin resolver.
- La app y el pipeline DEBEN probarse desde un clon limpio antes de cada entrega.

### 3.9 Seguridad

- `.env`, credenciales, tokens y claves NO se versionan; `.gitignore` los cubre. Esto incluye `MANUELITA_IDENTITY_KEY` (clave HMAC del reconocimiento por correo) y `HF_TOKEN`, que
  solo sirve para descargar el modelo de voz.
- Lo mismo aplica a `OPENCLAW_GATEWAY_TOKEN`, `VALERIA_CHANNEL_TOKEN`, `VALERIA_CHANNEL_SALT`, los números
  `WA_ALLOW_*` y la sesión de WhatsApp (`%USERPROFILE%\.openclaw-valeria`): las plantillas versionadas
  (`openclaw/openclaw.json5`, `openclaw/.env.example`) solo usan `${VAR}`. El job `secretos` de CI corre
  `gitleaks` sobre el historial completo.
- No se ejecuta código arbitrario proveniente del scraping.
- Las dependencias se mantienen actualizadas y fijadas; se revisan vulnerabilidades antes de la entrega.
- Los datos de terceros se citan y se usan dentro de lo permitido por su licencia.

---

## 4. Gobernanza del repositorio y Git

### 4.1 Repositorio, licencia y README

- Repositorio público en GitHub con visibilidad abierta.
- `LICENSE` MIT, año 2026, titulares Jason Alejandro Castaño y Roberto José Guerrero.
- Licencia declarada en `README.md` y en `pyproject.toml`.
- `README.md` DEBE incluir: badges, problema y solución, arquitectura, instalación con `uv sync`, uso,
  estructura, capturas de la app, fuentes de datos, limitaciones, licencia y créditos.
- `README.md` DEBE enlazar el diagrama interactivo `docs/arquitectura.html` y su fuente
  `docs/arquitectura.json`, regenerados con Archify.
- Todo diagrama de arquitectura o de flujo del README DEBE generarse con Archify (fuente JSON en
  `docs/diagramas/`, HTML validado con `finalize --quality showcase` y captura en
  `docs/capturas/diagramas/`); no se usan bloques Mermaid.
- La gobernanza visible (PR/issue templates, labels, pre-commit y Makefile) DEBE estar
  versionada y enlazada desde el README.
- Los créditos DEBEN nombrar a ambos integrantes y al curso.

### 4.2 Ramas, Pull Requests y revisión

- `main` es la rama protegida y desplegable.
- El trabajo se hace en ramas `feat/...`, `fix/...`, `docs/...` o `chore/...`.
- Todo cambio llega a `main` por Pull Request; no se permite push directo.
- Cada PR DEBE incluir: qué cambia, por qué, cómo se probó, capturas si aplica y riesgos.
- El PR DEBE ser aprobado por el integrante distinto al autor; en G3/G4, por el docente cuando corresponda.
- Los checks de CI DEBEN estar verdes antes de fusionar.
- Antes de la sustentación del Módulo 1 DEBEN existir al menos 2 PR fusionados y trazables.

### 4.3 Commits

- Formato Conventional Commits: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`.
- Commits atómicos, con cuerpo cuando la decisión no sea obvia.
- NO se versionan binarios, datos, `.env`, capturas temporales ni artefactos de build.
- El historial DEBE permitir reconstruir la evolución del pipeline, los prompts y la app.
- **Autoría permitida**: todo commit DEBE tener como autor (y, si aplica, coautor `Co-authored-by` o firmante
  `Signed-off-by`) a una de estas dos identidades, y a ninguna otra:
  - `jasonCastano` — Jason Alejandro Castaño;
  - `Robertto48` — Roberto José Guerrero Criollo.
- **Prohibido contribuir a bots y asistentes**: ninguna herramienta (Claude Code, OpenCode, Copilot, Dependabot,
  `github-actions[bot]` u otra) PUEDE crear commits, PRs, tags ni releases en el repositorio. Las herramientas
  solo asisten en local; el commit y el PR los hace un integrante con su cuenta.
- GitHub (`noreply@github.com`) solo se acepta como *committer* de los merges que un integrante hace desde la
  web.
- NO SE DEBEN incluir trailers `Co-authored-by` de asistentes de IA ni firmas del tipo «Generated with …» en
  commits, PRs, tags o releases. Los asistentes se configuran para no añadirlos (`.claude/settings.json` con
  `"includeCoAuthoredBy": false` y `"attribution": {"commit": "", "pr": ""}`).
- **Dependencias**: las actualizaciones las hace un integrante (`uv lock --upgrade-package <pkg>` y PR). Las
  actualizaciones de versión de Dependabot están desactivadas (no hay `.github/dependabot.yml`); las alertas de
  seguridad de GitHub siguen activas porque no crean commits.
- Verificación: el hook `commit-msg` de pre-commit y el job `autoria` del CI ejecutan
  `scripts/check_commit_authors.py`; la lista de identidades vive en `src/proyecto_modelos_lenguaje/authorship.py`
  y debe coincidir con esta sección. Decisión y procedimiento de limpieza del historial en
  `docs/decisions/0017-autoria-commits.md`.

### 4.4 Integración continua

- GitHub Actions DEBE ejecutar `uv sync --frozen`, `uv run ruff check .` y `uv run pytest`.
- La interfaz local `make check` DEBE reflejar el mismo lint, formato y pruebas que el CI.
- El badge de CI DEBE mostrarse en el README.
- Un fallo de CI bloquea la fusión.
- Se recomienda publicar cobertura y un artefacto de ejemplo del corpus.

### 4.5 Versionado y entregas

- Cada entrega se etiqueta: `v0.1.0-modulo1`, `v0.2.0-modulo2`, etc.
- El tag debe apuntar a un commit con CI verde y README actualizado.
- Las releases incluyen notas de cambios y limitaciones conocidas.

### 4.6 Estándares de gobernanza y documentación viva

- **Makefile**: interfaz única para `install`, `dev`, `lint`, `format`, `test`, `check`, `app`, `audit`,
  `build` y `clean`.
- **Pre-commit**: higiene de archivos, Ruff, sincronización de `uv.lock` y autoría de commits (`commit-msg`);
  se instala con `make dev`.
- **GitHub**: plantilla de PR, formularios de issue, labels declarativas y workflow de labels (sin Dependabot
  de versiones, §4.3).
- **Contribución**: `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md` y `AGENTS.md` describen el flujo y el contexto.
- **Arquitectura**: `docs/arquitectura.json` es la fuente; `docs/arquitectura.html` se regenera con
  Archify y se enlaza desde el README. Los diagramas del agente (grafo, nodo, memoria, router y
  trazas) viven en `docs/diagramas/*.json` con su HTML. El HTML no se edita a mano.
- **Identidad**: el mantenedor y la cuenta de GitHub se declaran en README y constitución; no se usan
  credenciales ni rutas absolutas en la documentación.

**Razón**: un proyecto académico defendible debe poder auditarse y reproducirse sin conocimiento tácito.

---

## 5. Reglas por fase

### Fase 0 — Preparación (transversal)

**Objetivo**: dejar el proyecto listo para trabajar y evaluar.

Entregables mínimos:

- Repositorio público, licencia MIT, README inicial y `.gitignore`.
- Entorno `uv` reproducible, Ruff y pytest configurados.
- Esta constitución, la especificación de la fase y el plan técnico.
- Capas de datos definidas y equivalencia con la rúbrica documentada.
- Convención de ramas, PRs y commits acordada.

Puerta: `uv sync`, lint y pruebas pasan; el repositorio se entiende desde el README.

---

### Fase 1 — Módulo 1: Base de conocimiento y Q&A

**Objetivo**: construir la base de conocimiento semántico de Manuelita y un sistema Q&A con Prompt Engineering,
LangChain y una experiencia web React/FastAPI.

**Alcance obligatorio**:

1. **Investigación y alcance** (`docs/alcance.md`):
   - Fuentes oficiales, redes y medios.
   - 5–10 categorías de preguntas de un cliente primerizo: identidad, historia, sedes, productos, contacto,
     sostenibilidad, certificaciones, noticias, compras, empleo.
   - Al menos 20 preguntas de prueba derivadas del alcance.
2. **Adquisición y preparación de datos**:
   - Pipeline reproducible con las etapas descubrir → extraer → limpiar → deduplicar → enriquecer.
   - Corpus con metadata completa y hash.
   - Texto limpio consolidado en `data/gold/`; chunks en `data/silver/`.
   - Métricas de URLs, páginas, tokens y descartes.
   - Ficha de datos (`docs/data_card.md`) con fuentes, licencias, fechas y limitaciones.
3. **Tareas de LLM con LangChain**:
   - Resumen del corpus.
   - Generación de FAQ.
   - Q&A con contexto y citas.
   - Prompts versionados en `docs/prompt_log.md`.
4. **Aplicación web**:
   - Frontend React/Vite con Consulta, Resumen, FAQ y showcase del Módulo 1.
   - API FastAPI con citas, fallback y modo demostración.
   - Ejecutable con `make app` o `uv run python -m proyecto_modelos_lenguaje.webbuild --serve`.
   - Verificación E2E con `make e2e`.
5. **Evaluación**:
   - 20 preguntas como mínimo, con respuesta, fuente, corrección, coherencia y alucinación.
   - Comparación zero-shot vs. prompt final.
   - Análisis de errores y limitaciones.
6. **Informe** con las cinco secciones exigidas: descripción del problema, planteamiento de la solución,
   preparación de los datos, modelado (LLM, modelo de embedding previsto, base vectorial prevista y diseño del
   prompt) y resultados.
7. **Sustentación**: 12 minutos de demostración + 3 de preguntas, sin diapositivas, con app, repositorio e IDE
   abiertos; el pipeline se ejecuta en vivo. Fecha oficial: sábado 31 de octubre de 2026, 8:00–11:00 a.m.,
   8.ª sesión del curso.

**Puerta de la Fase 1**:

- [ ] Corpus limpio, deduplicado y con metadata.
- [ ] `data/silver/` y `data/gold/` poblados y documentados.
- [ ] Tres tareas LangChain funcionando.
- [ ] App con tres funcionalidades y citas.
- [ ] 20 preguntas evaluadas y tabuladas.
- [ ] Informe completo.
- [ ] ≥2 PR fusionados con revisión.
- [ ] README, licencia, CI y capturas actualizados.
- [ ] Demo ensayada de 12+3 minutos.
- [ ] Tag `v0.1.0-modulo1`.

**No se acepta como entrega**:

- Solo diapositivas o un video pregrabado.
- Datos inventados o copiados a mano sin pipeline.
- Claves de API o `.env` dentro del repositorio.
- Un notebook único sin script reproducible.
- Ausencia de licencia, o una licencia que prohíba el uso académico.

---

### Fase 2 — Módulo 2: Agente con memoria y enrutador (30 %)

**Objetivo**: evolucionar el Q&A a un **agente RAG** con base vectorial, memoria multi-turno y enrutamiento
documental vs. estructurado (SQL/CSV), blindado contra inyección indirecta y con Human-in-the-Loop.

**Especificaciones**: `specs/013-semantic-rag-chatbot/` (recuperación semántica e híbrida; PR #34, ADR
`0014-semantic-rag.md`) y `specs/014-rag-agent-memory-router/` (memoria, enrutador, agente, blindaje y evaluación
ampliada; ADR `0015-module2-scope.md`). Fuentes: diapositiva «Proyecto Integrador», Clases 6, 7 y 9; análisis
del 2026-11-07.

**Estado de la implementación (2026-11-07)**: el PR #34 implementa la recuperación semántica en
`src/proyecto_modelos_lenguaje/rag/` con `intfloat/multilingual-e5-small` (384 d, 512 tokens, ONNX vía
`fastembed`), índice `numpy` + SQLite con manifiesto en `data/module2/` (no versionado), fusión híbrida con
respaldo léxico, traza visible en API e interfaz y evaluación Recall@5/MRR en `docs/evaluacion_modulo2.md`.
Memoria, enrutador, agente y HITL siguen pendientes (spec 014).

**Avance de la spec 014 (2026-11-10)**: plan y 77 tareas en `specs/014-rag-agent-memory-router/`; fundamentos
implementados en `src/proyecto_modelos_lenguaje/agent/` (configuración `config/agent.toml`, estado en
`MANUELITA_STATE_DIR` fuera del repositorio, modelos tipados, aislamiento XML y modo demo). Dependencias
nuevas: `langgraph` y `langgraph-checkpoint-sqlite`. Ragas queda diferido: no instala en Python 3.14
(`specs/014-rag-agent-memory-router/research.md` §12). US3 (medir): Recall@10, nDCG@10, abstención y
calentamiento en `rag/evaluate.py`; conjunto de 30 consultas con ruta esperada; troceo 400/60 en el manifiesto;
línea base en `docs/evaluacion_modulo2.md` (híbrido ≥ léxico; ningún modo se abstiene fuera de corpus).
US2 (enrutar): tabla SQLite de solo lectura derivada del oro (`agent build-structured`) y enrutador en dos
etapas (reglas + DeepSeek, `prompts/router.md`): 35/36 rutas correctas y abstención fuera de corpus por
enrutamiento. US1 (conversar, MVP): hilos con `thread_id` persistidos en `checkpoints.sqlite3`
(`SqliteSaver`, fuera del repositorio), variantes cadena y agente (`create_agent` con límites de búsquedas y
llamadas), resumen de memoria (`prompts/memory_summary.md`), `POST /api/chat`, `GET /api/threads/{id}`,
`agent chat` y pestaña «Conversación» en la web; verificado en demo y con DeepSeek. US4 (blindar):
fragmentos con instrucciones embebidas marcados y reportados en `anomalies[]`, respuestas que copian el
system prompt descartadas, y acciones de escritura (`save_preference`, `forget_memory`,
`export_conversation`) detenidas por `interrupt()`/`HumanInTheLoopMiddleware` hasta una decisión humana
(`POST /api/threads/{id}/resume`), que queda registrada y sobrevive al reinicio; memoria larga en
`memory.sqlite3` (`SqliteStore`) dentro de `MANUELITA_STATE_DIR`. US5 (preferencias): lista cerrada
(`response_format`, `topics_of_interest`, `language`), valores ≤ 200 caracteres, expiración a 30 días,
datos personales redactados antes de persistir (mensajes, preferencias y entrada del agente con
`PIIMiddleware`), preferencias aplicadas al system prompt de ambas variantes, `GET|DELETE /api/memory/{user_id}`
(el borrado pasa por aprobación) y política en `docs/memoria.md`.

**Cierre de la Fase 2 (2026-11-11, en revisión)**: comparación cadena vs. agente con DeepSeek en
`docs/evaluacion_modulo2.md` (citas 100 %, abstención fuera de corpus 4/4, < 10 s: cadena 100 % y agente 94 %;
repreguntas con métrica estricta 3/6 y 4/6, por debajo de SC-006); juez propio con definiciones de Ragas porque
Ragas no instala en Python 3.14; ADR 0016, informe `docs/informe_modulo2.md`, guion actualizado, E2E de la
conversación y arquitectura regenerada. Pendientes antes del tag `v0.2.0-modulo2`: calificación humana de las
repreguntas, repetir la fidelidad del juez y la revisión de `module2_queries.jsonl` por Jason.

**Rúbrica oficial (2026-11-13)**: el Anuncio 006 publica la rúbrica de sustentación (13 ítems; ver §8.3).
La ADR `0018-qdrant-y-rubrica-modulo2.md` cierra sus brechas: Qdrant como base vectorial, perfil en el Store,
ruta mixta, streaming SSE, observabilidad por turno y herramienta estructurada con esquema Pydantic y conteo
exacto. El mapa de evidencias y el guion están en `docs/rubrica_modulo2.md`.

**Reglas mínimas**:

1. **Embeddings**: modelo multilingüe elegido con evidencia de **retrieval en español** (MTEB filtrado por
   Retrieval/español; un promedio general alto no basta), costo y latencia. Registrar modelo, versión, dimensión,
   normalización, prefijos de consulta/documento y límite de tokens. El embedding **no es intercambiable**: cambiar
   de modelo obliga a reindexar.
2. **Base vectorial**: **Qdrant** (ADR 0018), con colección coseno, índice HNSW y filtro por *payload* en una
   sola etapa.
   - Con `QDRANT_URL` usa el servidor (ANN); sin ella, el modo local embebido en `data/module2/qdrant`, fuera
     de Git.
   - La colección se carga desde el índice versionado de la spec 013 (`rag qdrant build`). Si falta, la
     recuperación vuelve a la matriz `numpy` y lo anota.
   - El índice y la colección son **vistas derivadas** del oro: se reconstruyen con un comando y no se
     versionan como fuente; su manifiesto (modelo, fragmentación, fecha, hash del oro) sí.
3. **Chunking**: tamaño, solapamiento (10–20 %) y metadatos definidos y medidos; parámetros ANN (`ef_search`,
   `nprobe`) calibrados con datos del proyecto y documentados en la arquitectura.
4. **Recuperación híbrida**: comparar denso, léxico (BM25 del Módulo 1) e híbrido con pesos calibrados.
5. **Memoria a corto plazo**: estado por `thread_id` con checkpointer persistente (SQLite en local);
   recorte/resumen de hilos largos.
6. **Memoria a largo plazo** (obligatoria desde la rúbrica, ítem 1.3): Store entre hilos con namespace por
   usuario.
   - Se guardan el perfil (`("users", id, "profile")`: nombre, trabajo, cargo y ciudad) y las preferencias
     (`("users", id, "preferences")`).
   - Solo se escribe con aprobación humana y se recupera con `search()` desde cualquier hilo.
   - Se declaran qué se guarda, la retención y el borrado (`docs/memoria.md`); nunca datos sensibles.
7. **Enrutador**: puerta de decisión que clasifica cada mensaje en directo, documental, estructurado, **mixto**
   (tabla y documentos en el mismo turno) o fuera de alcance, con confianza; con confianza baja pide aclaración.
   Las herramientas exponen esquemas Pydantic y la aritmética (conteos, sumas, promedios, máximos,
   mínimos y variaciones) la hace la herramienta, nunca el modelo. Hay dos orígenes estructurados de
   **solo lectura**: la tabla SQLite derivada de hechos y entidades del oro, y el CSV **curado y
   versionado** `data/curated/series_anuales.csv` con cifras anuales de los informes de sostenibilidad
   (una fila por cifra, con `unit_id`, URL y página; una prueba verifica cada valor contra su unidad
   de oro). Los informes son anuales: una pregunta por trimestre se responde declarando ese límite.
8. **RAG Chain vs. RAG Agent**: implementar ambas variantes (recuperar siempre vs. retriever como `@tool` con
   `create_agent`) y compararlas en calidad, latencia y número de llamadas.
9. **Blindaje**: contexto recuperado aislado con etiquetas XML como dato; las oraciones con instrucciones
   dirigidas al asistente se neutralizan antes de llegar al modelo; prueba adversarial con documentos maliciosos
   que DEBE pasar sin red y medirse con el modelo real (`agent shield`, línea base sin neutralización,
   `docs/evaluacion_blindaje.md`; spec 015, ADR 0019). Regla de oro HITL: **lectura automática, escritura con aprobación**
   (`HumanInTheLoopMiddleware` / `interrupt()` + `Command(resume=...)` con el mismo `thread_id`).
10. **Evaluación de retrieval**: 20–30 consultas reales con documento correcto y ruta esperada etiquetados; comparar
    al menos dos configuraciones con **Recall@10, nDCG@10** y MRR, más precisión del enrutador, fidelidad de citas,
    latencia y llamadas. Línea base: BM25 del Módulo 1.
11. **Evaluación de generación y observabilidad**: fidelidad y relevancia con Ragas (o un juez con sus
    definiciones) y trazas con LangSmith (`run_name`, etiquetas y metadatos por turno), sin enviar claves ni
    datos sensibles. Sin LangSmith, un log estructurado por turno en `$MANUELITA_STATE_DIR/logs/turns.jsonl`.
    Las pruebas offline siguen pasando sin red.
12. **Integración**: la app muestra por turno pregunta, ruta, fragmentos con puntaje, respuesta, fuentes e
    historial, con la respuesta en **streaming** (`POST /api/chat/stream`, SSE). El modo demostración cubre
    todo sin red ni clave. El corpus adversarial (`MANUELITA_DEMO_CORPUS=malicious`) muestra el blindaje en modo
    demo y con el modelo real, con un aviso visible en la interfaz.
13. **Prompts** nuevos (enrutador, agente, resumen de memoria) versionados en `prompts/` y `docs/prompt_log.md`.
14. **Informe y demo** actualizados; tag `v0.2.0-modulo2`.

**Opcionales que suman**: puerta System One (Jev `Noul`/`Choice`) para screening/routing — implementada en la
spec 022 (Choice, Score y Noul; desactivada por defecto, evidencia en `docs/evaluacion_jev.md`); exportar el oro
como bundle Open Knowledge Format (LLM Wiki).

**Puerta de la Fase 2**:

- [ ] Índice vectorial reconstruible desde un clon limpio, con manifiesto.
- [ ] Conjunto de 20–30 consultas etiquetadas y reporte comparativo (Recall@10, nDCG@10, MRR) vs. Módulo 1.
- [ ] Memoria multi-turno por `thread_id` persistente entre reinicios.
- [ ] Enrutador documental/estructurado/directo/fuera de alcance con ≥90 % de acierto en el conjunto.
- [ ] Chain vs. Agent comparados en latencia y llamadas.
- [ ] Prueba de inyección indirecta y flujo HITL en verde.
- [ ] App con fragmentos, ruta y fuentes; modo demo completo; `make check` y CI verdes.
- [ ] Informe, prompt log, ADRs y demo actualizados; tag `v0.2.0-modulo2`.

**Nota**: la rúbrica oficial se publicó el 2026-11-13 y esta constitución se enmendó el mismo día (1.5.0). Una
rúbrica nueva vuelve a exigir enmienda antes de continuar; no se improvisa sobre la marcha.

---

### Fase 3 — Módulo 3: Productización y despliegue (40 %)

**Objetivo**: convertir el agente RAG en un producto desplegado: FastAPI / Agent OS, persistencia de estado y
canales reales (WhatsApp o Telegram), evaluado y observable.

**Reglas mínimas**:

0. **Canal real**: al menos un canal de mensajería (WhatsApp o Telegram) además de la web, con persistencia de
   estado productiva (p. ej. PostgreSQL) y secretos fuera del repositorio.
1. **Conversación**: manejo de contexto, memoria, turnos y fallback.
2. **Guardrails**: rechazo de preguntas fuera de alcance, protección contra prompt injection y contenido
   dañino.
3. **Evaluación**: conjunto de evaluación con métricas de fidelidad, relevancia, latencia y costo; pruebas de
   regresión.
4. **Despliegue**: FastAPI / Agent Server en contenedor, Hugging Face Spaces u otro entorno reproducible;
   variables de entorno seguras.
5. **Observabilidad**: logs sin datos sensibles, trazabilidad de fuentes y monitoreo de errores.
6. **Documentación final**: README, informe, arquitectura, limitaciones y créditos.
7. **Demo final** y tag de release.

**Concreción para el Anuncio 007** (enmienda 1.16.0, spec 024, ADR 0028):

8. **Canal**: WhatsApp es obligatorio y llega por **OpenClaw** (gateway con `bind: "loopback"` y token, modelo
   DeepSeek en la nube con respaldo, nunca un modelo local en la demo). Telegram u otro canal es un extra,
   nunca un reemplazo. Hay **un solo agente**: el plugin `valeria-bridge` (hook `before_dispatch`) envía cada
   mensaje admitido al mismo `ChatService` de la web por `POST /api/channels/messages` (loopback +
   `X-Channel-Token`). Mientras no exista la corrección oficial, un **parche versionado** puede corregir un
   defecto del componente de WhatsApp (enmienda 2.11.0, spec 033, ADR 0039): anclado en texto exacto y
   limitado a una versión, idempotente, aplicado solo por `scripts/openclaw_env.ps1 -Install` (nunca a mano) y
   verificado por `ops check` (`soporte-lid`, `soporte-sticker`). Hoy existen dos:
   `openclaw/patches/whatsapp-lid.mjs`, para las cuentas que WhatsApp entrega solo con su ID (`…@lid`), y
   `openclaw/patches/whatsapp-sticker.mjs` (enmienda 2.11.1, spec 037, ADR 0040), que expone `sendSticker` en
   el listener activo y envía como sticker nativo los archivos `valeria-*.webp`, con la misma sesión.
9. **Número** (enmiendas 2.8.0 y 2.9.0, specs 028 y 031): una **SIM dedicada** a Valer-IA, vinculada como
   dispositivo y desactivada después de la sustentación. Solo chats individuales (`groupPolicy: "disabled"`,
   `selfChatMode: false`). `dmPolicy` se lee de una variable: modo cerrado (`"allowlist"` con números de
   prueba E.164 desde variables de entorno) y modo abierto (`"open"` con `allowFrom: ["*"]`; cualquier número,
   sin códigos de emparejamiento), que se usa hasta el fin del proyecto. Se cambia con
   `scripts/openclaw_env.ps1 -Mode`, que edita solo el `.env` externo; ningún número entra al repositorio, y
   `ops check` muestra el modo y advierte cuando está abierto. Con el canal abierto, el backend aplica por
   seudónimo un límite por ventana corta y un tope diario (`[channels]` de `config/agent.toml`; un único
   aviso natural y luego silencio), permite bloquear seudónimos (`pml channels block`) y reserva los atajos
   ocultos a los operadores de `VALERIA_OPERATORS` (seudónimos, sin límites).
10. **Seudónimos**: el número NO DEBE guardarse ni registrarse. Se convierte en `wa-<16 hex>` con HMAC-SHA256
    y `VALERIA_CHANNEL_SALT`. El ID interno de WhatsApp (`…@lid`) se trata igual (enmienda 2.11.0): se
    normaliza a `lid:<dígitos>`, se seudonimiza con la misma sal y nunca se registra; el registro solo guarda el
    tipo de remitente. Los registros (`channels.jsonl`, `mcp.jsonl`, bitácora `memory/YYYY-MM-DD.md`)
    no llevan texto de mensajes ni números, y los archivos versionados del workspace no llevan datos de
    personas.
11. **Catálogo único**: las herramientas del agente se declaran en `agent/catalog.py` (mínimo 20, esquema
    Pydantic con `extra="forbid"`, `requires_approval ⇔ write`). De ahí salen el agente, el servidor MCP,
    `GET /api/tools` y `docs/herramientas.md`; no se declaran herramientas en otro lugar. Toda escritura pide
    la confirmación de la persona también en WhatsApp, dicha con sus palabras («dale», «mejor no»;
    una respuesta ambigua se vuelve a preguntar y nunca se ejecuta), y vence a los 10 minutos.
12. **MCP de solo lectura**: el servidor propio `valeria-tools` expone únicamente las herramientas de lectura.
    Lo usa el agente nativo de OpenClaw en el **modo degradado** (backend caído o > 90 s, para cubrir la cola
    por persona y la voz), sin escrituras ni planificación: expone 15 herramientas de lectura de atención.
13. **Persistencia**: `SqliteSaver`, `SqliteStore` y `channels.sqlite3` (WAL) en `$MANUELITA_STATE_DIR` se
    aceptan como el «equivalente» a PostgresSaver de la regla 0: un proceso, ≤ 20 usuarios simultáneos y
    candado por usuario. Escalar a varios procesos obliga a revisar esta regla.
14. **Hardening** (enmienda 2.8.0): si el servidor permite virtualización, sandbox Docker sin red; si no (caso
    del portátil servidor, spec 028 R12), sandbox apagado con `tools.deny` que retira al agente nativo todas
    sus herramientas propias salvo el MCP de lectura, como riesgo aceptado (ADR 0037). Siempre `tools.deny`,
    `fs.workspaceOnly`, `exec` denegado;
    `openclaw security audit` sin hallazgos críticos antes de la sustentación.
15. **Despliegue**: PC del equipo como servidor (servicios con reinicio automático), reproducible con
    `docs/despliegue.md`. WhatsApp no usa túnel (conexión saliente); el túnel, si existe, solo publica la web.

**Plataforma de agentes de la idea 7** (enmienda 2.0.0, spec 025, ADR 0029). Las reglas 8–15 siguen vigentes, y se
añaden:

16. **Perfiles**:
    - Los perfiles (visitante, cliente B2B, proveedor, colaborador, planificador) se declaran en un solo lugar,
      con su foco y su subconjunto del catálogo.
    - El router combina ruta y perfil, y la traza muestra el perfil activo.
    - El perfil se guarda en la memoria de largo plazo solo con aprobación y se borra cuando la persona lo
      pide con sus palabras («olvida lo que sabes de mí»; `/olvidar` queda como atajo del operador).
17. **Información pública**: los perfiles cliente, proveedor y colaborador responden solo con la capa oro y sus
    citas. NO DEBEN dar precios, condiciones comerciales, datos internos ni datos de personas. Las cotizaciones van
    a un humano con «SÍ».
18. **Datos sintéticos**:
    - Solo la planificación industrial puede usar datos sintéticos.
    - Esos datos se generan con un script determinista y semilla, se versionan con su ficha y se etiquetan como
      sintéticos en cada respuesta.
    - NO DEBEN mezclarse con el corpus público, citarse como fuentes de Manuelita ni presentarse como su operación
      real. Sus citas son distinguibles de `[U#]` y `[F#]`.
19. **Cifras de planificación**:
    - Balances, márgenes, sensibilidad y planes salen del simulador y del optimizador (programación lineal), nunca
      del texto del modelo.
    - Si no hay solución factible, se declara el conflicto y no se inventa capacidad.
    - El agente recomienda y el equipo de planta decide.
20. **Autorización**:
    - El perfil planificador es libre en la web y en WhatsApp (enmienda 2.8.0, spec 028, ADR 0037). La ruta
      `planning` la deciden las reglas por contexto, solo en ese turno y su repregunta, sin cambiar el perfil.
    - Guardar una propuesta exige la confirmación de la persona con vencimiento de 10 minutos.
    - Ninguna herramienta se conecta con sistemas reales de planta.
    - El modo degradado no simula, no optimiza ni guarda.
21. **Evaluación**:
    - Las baterías de planificación (12 escenarios con óptimo de referencia independiente) y de perfiles
      (20 consultas) se fijan antes de evaluar.
    - Las evaluaciones vigentes (herramientas, triviales, blindaje y retrieval) no pueden bajar de su último valor
      publicado.
22. **Conversación y voz** (enmienda 2.8.0, spec 028, ADR 0037):
    - En WhatsApp nadie necesita comandos y ningún texto los sugiere; las intenciones del canal se reconocen
      por contexto en español e inglés. Los comandos quedan como atajos ocultos del operador.
    - Las notas de voz se transcriben y se sintetizan localmente (dictado de la spec 023, voz de la spec 016);
      la regla 8 se refiere al modelo de lenguaje, que sigue en la nube.
    - La respuesta escrita conserva citas y fuentes; la nota de voz es un guion conversacional sin citas, URLs
      ni cifras que no estén en la respuesta escrita, en el idioma de la pregunta.
    - Los audios no se registran ni se versionan: los entrantes se procesan en memoria y los generados se
      borran a los 10 minutos.

---

### Reglas transversales de fase

- Ninguna fase inicia sin la puerta de la anterior aprobada por ambos integrantes.
- Cada fase DEBE tener especificación, plan, tareas y pruebas en `specs/`.
- Todo cambio de alcance, modelo o arquitectura DEBE registrarse como decisión y reflejarse en el plan.
- Cada fase termina con retrospectiva breve: qué funcionó, qué falló y qué se corrige.
- Las fechas oficiales del curso prevalecen sobre cualquier plan interno.

---

## 6. Definición de terminado (DoD)

Un entregable está terminado solo si cumple todo lo siguiente:

| Dimensión | Evidencia mínima |
|-----------|------------------|
| Código | PR fusionado, CI verde, Ruff limpio, pruebas pasando |
| Datos | Pipeline reproducible, metadata, hash, deduplicación y ficha de datos |
| LLM | Tres tareas funcionando, prompts versionados, citas y fallback |
| App | `make app` (React + FastAPI) funciona desde un clon limpio |
| Evaluación | 20+ preguntas tabuladas y analizadas |
| Documentación | README, informe, prompt log y decisiones actualizados |
| Repositorio | ≥2 PRs revisados, Conventional Commits, sin secretos ni datos |
| Licencia | MIT declarada en LICENSE, README y `pyproject.toml` |
| Demo | Ensayo cronometrado de 12+3 minutos, sin diapositivas |
| Ética | Sin datos privados, sin alucinaciones no declaradas, fuentes citadas |

---

## 7. Roles, responsabilidades y decisiones

| Rol | Integrante | Responsabilidad principal |
|-----|------------|---------------------------|
| Co-owner / datos y pipeline | Jason Alejandro Castaño | Scraping, capas medallion, calidad y metadata, reproducibilidad |
| Co-owner / LLM y aplicación | Roberto José Guerrero | LangChain, prompts, modelo, app, evaluación de respuestas |
| Revisión cruzada | Ambos | Revisar el PR del otro, probar la demo, validar citas |
| Documentación y demo | Ambos | Informe, README, guion y sustentación |

Reglas:

- Los roles son de referencia y pueden rotar por fase con acuerdo registrado.
- Ninguna decisión de alcance, modelo o arquitectura se toma unilateralmente.
- En caso de empate, decide el responsable de la fase y se registra la justificación.
- Ambos DEBEN poder ejecutar el pipeline, la app y explicar una decisión de código sin leer el README.
- El docente actúa como revisor externo cuando la rúbrica lo indique.

---

## 8. Mapeo a la rúbrica

### 8.1 Rúbrica del Módulo 1

| Criterio | Peso | Evidencia obligatoria en el proyecto |
|----------|------|--------------------------------------|
| Análisis de la empresa y estrategia de datos | 15% | `docs/alcance.md`, ficha de datos, fuentes y cobertura |
| Procesamiento y tareas LLM | 25% | Texto limpio, chunks, Resumen/FAQ/Q&A con LangChain |
| Calidad del Prompt Engineering | 25% | `docs/prompt_log.md`, línea base, anti-alucinación, citas |
| Implementación y calidad de la app | 15% | Frontend React/FastAPI con tres funcionalidades, métricas y citas |
| Documentación escrita | 10% | Informe con las cinco secciones |
| Presentación oral y demostración | 10% | Demo 12+3, sin diapositivas, app/repo/IDE |

### 8.2 Criterios de la sustentación

La sustentación aporta el 10% del Módulo 1; el 90% restante proviene de la rúbrica del Taller 1. Cada criterio
se puntúa de 1.0 a 5.0 y la nota es `1.0 + 4 × (puntos / 100)`.

| Criterio | Peso | Evidencia obligatoria |
|----------|------|-----------------------|
| UI en acción y scraping visible | 20% | Etapas, URLs, páginas, tokens, descartes y Q&A con cita |
| Repositorio y Pull Requests | 15% | Repo público, ≥2 PRs revisados, checks verdes |
| Calidad de los commits | 10% | Conventional Commits, atomicidad, sin binarios ni `.env` |
| README profesional | 15% | Badges, problema/solución, arquitectura, instalación, capturas, licencia, créditos |
| Licencia MIT | 5% | `LICENSE` correcta y declarada |
| Pipeline de scraping | 20% | `uv run`, robots/sitemap, capas, deduplicación, JSONL/Markdown |
| Revisión en el IDE | 15% | Proyecto abierto en VS Code, Cursor o Antigravity; estructura, ejecución, diff y decisión explicada en vivo |

### 8.3 Pesos del Proyecto Integrador y Módulo 2 (provisional)

| Fase | Peso | Evidencia esperada |
|------|------|--------------------|
| Fase 1 — Ingesta y base semántica | 30 % | Rúbrica del Módulo 1 (§8.1 y §8.2) |
| Fase 2 — Agente con memoria y enrutador | 30 % | Puerta de la Fase 2; specs 013 y 014; reporte de retrieval |
| Fase 3 — Productización y despliegue | 40 % | Canal real, despliegue, evaluación y observabilidad |

**Rúbrica del Módulo 2** (Anuncio 006, 2026-11-13). La nota es Σ (peso × puntaje), en escala de 1,0 a 5,0:

| Criterio | Ítems y pesos |
|----------|---------------|
| 1. Memoria (25 %) | 1.1 checkpointer y `thread_id` 10 % · 1.2 contexto multi-turno 8 % · 1.3 Store y namespace 7 % |
| 2. Herramientas, router y blindaje (30 %) | 2.1 herramienta CSV/JSON con `@tool` 8 % · 2.2 RAG con Qdrant y ANN 8 % · 2.3 router 10 % · 2.4 blindaje 4 % |
| 3. Aplicación y código (20 %) | 3.1 frontend propio desacoplado 10 % · 3.2 calidad y gobernanza 10 % |
| 4. Documentación (15 %) | 4.1 diagramas 8 % · 4.2 diseño y evaluación del retrieval 7 % |
| 5. Sustentación (10 %) | 5.1 los cuatro casos en vivo 6 % · 5.2 dominio individual 4 % |

Streamlit, Gradio y los notebooks no se aceptan como interfaz. La evidencia de cada ítem está en
`docs/rubrica_modulo2.md`.

### 8.4 Rúbrica del Módulo 3

Anuncio 007 (2026-11-23): sustentación el sábado 28 de noviembre de 2026, 15 minutos (7 de pitch con la demo
en WhatsApp desde el teléfono de un invitado y 8 de discusión técnica), sin diapositivas. El Módulo 3 vale el
40 % del curso; la nota es Σ (peso × puntaje), en escala de 1,0 a 5,0, y sustentar en inglés suma un bonus.

| Ítem | Peso | Evidencia principal |
|------|-----:|---------------------|
| 1.1 Function calling y 20 tools | 10 % | `agent/catalog.py`, `agent tools`, `docs/herramientas.md`, `docs/evaluacion_herramientas.md` |
| 1.2 Razonamiento, plan y router | 8 % | Subconjuntos por ruta, `plan_steps`, `/traza`, 0 búsquedas en triviales |
| 1.3 Memoria por capas | 7 % | `SqliteSaver`/`SqliteStore`, `channels.sqlite3`, `/nuevo`, `/olvidar`, `agent memory list` |
| 2.1 Pipeline del M1 | 5 % | `pml corpus rebuild` con manifiesto y procedencia |
| 2.2 RAG sobre Qdrant | 6 % | Qdrant servidor (HNSW), filtro por *payload*, híbrida, citas |
| 2.3 Evaluación del conocimiento | 4 % | 30 consultas, Recall@10/nDCG@10, t-SNE (`docs/evaluacion_modulo3.md`) |
| 3.1 Gateway OpenClaw | 8 % | `openclaw/openclaw.json5`, `scripts/openclaw_env.ps1` |
| 3.2 WhatsApp en producción | 10 % | `valeria-bridge`, `/api/channels/messages`, allowlist/pairing, teléfonos reales |
| 3.3 Workspace operativo | 7 % | `openclaw/workspace/` y bitácora `memory/YYYY-MM-DD.md` |
| 3.4 Skills/plugins/MCP | 5 % | `mcp_server.py` (`valeria-tools`), skill `valeria-manuelita`, plugin puente |
| 4.1 Código y pruebas | 7 % | `make check`, pytest sin red, `node --test` del plugin |
| 4.2 Seguridad y hardening | 7 % | Sandbox, `tools.deny`, `fs.workspaceOnly`, HITL, `agent shield --channel`, `security audit` |
| 4.3 Documentación final | 6 % | README, `docs/despliegue.md`, `docs/manual_whatsapp.md`, ADR 0028 |
| 5.1 Elevator pitch | 6 % | Guion de `docs/rubrica_modulo3.md` §2 |
| 5.2 Discusión técnica | 4 % | Reparto y preguntas de `docs/rubrica_modulo3.md` §3–§4 |

No se aceptan: menos de 20 tools, WhatsApp simulado o que no salga de localhost, Ollama como motor, solo
diapositivas o video, ni claves o `.env` en el repositorio. Estado y evidencia de cada ítem:
`docs/rubrica_modulo3.md`.

**Reenfoque a la idea 7** (enmienda 2.0.0): la plataforma de agentes refuerza, sin cambiar la evidencia anterior,
estos ítems:

- **1.1**: 26 herramientas, con simulador y optimizador;
- **1.2**: planificación de varios pasos en la traza y herramientas por perfil;
- **1.3**: perfil persistente;
- **3.3**: líneas rojas por perfil;
- **4.2**: planificador restringido y aprobación;
- **5.1 y 5.2**: el pitch de la plataforma y la discusión del optimizador.

La tabla ítem por ítem está en `specs/025-agentes-manuelita-idea7/spec.md`.

---

## 9. Documentación obligatoria

| Documento | Contenido mínimo | Momento |
|-----------|------------------|---------|
| `README.md` | Badges, problema, solución, arquitectura, instalación, uso, estructura, capturas, licencia, créditos | Siempre actualizado |
| `docs/alcance.md` | Categorías y 20+ preguntas | Inicio del Módulo 1 |
| `docs/data_card.md` | Fuentes, licencias, fechas, volumen, limitaciones | Cierre de datos |
| `docs/prompt_log.md` | Versiones, modelos, parámetros y resultados | Durante todo el proyecto |
| `docs/decisions/` | ADRs de arquitectura y modelo | Por cada decisión relevante |
| Informe del módulo | Cinco secciones: problema, solución, datos, modelado (LLM/embedding/vector DB/prompt) y resultados | Antes de la demo |
| `CONSTITUTION.md` | Reglas del proyecto | Ratificada y versionada |
| `specs/` | Especificaciones y planes por fase | Antes de implementar |
| `docs/demo.md` | Guion de 12+3 minutos y checklist | Antes de la sustentación |
| `docs/evaluacion_modulo2.md` | Conjunto etiquetado, Recall@10, nDCG@10, MRR, enrutador, Chain vs. Agent | Cierre del Módulo 2 |
| `docs/memoria.md` | Qué se persiste, retención, borrado y privacidad | Al implementar memoria |
| `docs/despliegue.md` | Requisitos, variables, gateway, WhatsApp, servicios, verificación y contingencia | Fase 3 |
| `docs/manual_whatsapp.md` | Acceso, ejemplos, comandos, confirmaciones, privacidad y límites | Fase 3 |
| `docs/rubrica_modulo3.md` | 15 ítems con estado y evidencia, guion 7 + 8 min, versión en inglés | Antes de la sustentación |

---

## 10. Ética, privacidad y uso de IA

- Solo se usa información pública; no se eluden autenticaciones, muros de pago ni captchas.
- No se incorporan datos personales sensibles; los cargos y nombres corporativos públicos se usan con fines
  académicos y se citan.
- El contenido de terceros se atribuye; se atienden solicitudes de retiro.
- Las respuestas del sistema no deben presentarse como asesoría oficial de Manuelita.
- **Política de tres niveles** de la asistente (spec 020, ADR 0024): la conversación **social** (saludos,
  cortesía, empatía, comentarios generales) se permite sin afirmar datos verificables; los **hechos externos
  verificables** (pronósticos, resultados, precios, noticias, diagnósticos o asesoría profesional) se declinan sin
  inventarlos; la **información de Manuelita** solo se afirma con evidencia del corpus y su cita. La asistente no
  da opiniones propias ni institucionales sobre temas polémicos.
- **Audio del visitante** (spec 023): el dictado procesa el audio en memoria y lo descarta al terminar; NO DEBE
  guardarse en disco, en `data/`, en registros ni en trazas, ni enviarse a terceros. Solo se conserva el texto
  que el visitante decide enviar. Las grabaciones de evaluación de personas son locales y no se versionan.
- **Video generado con IA** (specs 028 y 029): el pitch se genera **una vez, fuera de la app**, por la API de
  Higgsfield (`pml pitch generate`, con tope de gasto), con el modelo de `config/pitch.toml`: MAGI-2 si responde y,
  si no, Kling 4.0 (`pml pitch probe` lo comprueba sin costo). Todos los planos de una versión usan el mismo
  modelo. La clave vive solo en `.env`, y a Higgsfield solo se suben la imagen sintética, cuadros de planos ya
  aprobados y los prompts de plano. El único texto legible del video son los subtítulos y los gráficos propios
  del montaje, que no llevan la marca de Manuelita. Parte de un guion cuyas afirmaciones de Manuelita citan el oro. La
  entrada DEBE declarar junto al video, como texto visible, que es IA y proyecto académico, no canal oficial; el
  video no lleva rótulo grabado y solo se publica en la web. NO DEBE mostrar la marca de Manuelita ni presentar a
  la presentadora como su vocera. La imagen de referencia tiene ficha de origen y NO DEBE representar a una
  persona real. Solo se montan planos revisados por una persona, y la versión publicada se reemplaza solo con
  `pml pitch publish`, tras el chequeo.
- **Imágenes de perfil de Valer-IA** (spec 030, ADR 0034): la foto de perfil y las portadas para WhatsApp,
  LinkedIn y Facebook (`docs/whatsapp/`) son **composiciones** de la imagen de referencia sintética con ficha,
  hechas en HTML/CSS y exportadas en local (`scripts/whatsapp_images.py`). NO DEBEN usar modelos ni servicios
  de generación de imágenes ni tener costo; la presentadora se usa sin alterar sus rasgos (escala ≤ 1,15×,
  igual en ambos ejes). NO DEBEN mostrar la marca de Manuelita. La declaración de IA (asistente con IA de un
  proyecto académico, no canal oficial de Manuelita) DEBE ir en el texto del perfil de cada red donde se
  publiquen («Info» de WhatsApp, descripción de LinkedIn y Facebook; textos en `docs/whatsapp/README.md`), no
  en la imagen. Las tarjetas del bot (`docs/whatsapp/tarjetas/`) siguen el mismo sistema y la plantilla de
  planificación NO DEBE llevar cifras. Los stickers (`docs/whatsapp/stickers/`) son una ilustración
  vectorial propia de Valer-IA dibujada en código (`fuente/personaje.js`), sin modelos generativos; pueden
  tomar el estilo de otra obra, pero NO DEBEN reproducir sus personajes. Los audios de los stickers
  (`docs/whatsapp/stickers/audios/`, spec 030 US6, ADR 0036) DEBEN usar solo la voz oficial del agente (Phonon,
  spec 016), sintetizada en local y sin costo, sin clonar ni imitar voces reales; son OGG/Opus de 5 s como
  máximo, con el texto exacto de su sticker, y su ficha DEBE llevar la licencia CC BY-NC 4.0 y la atribución
  a Phonon (uso académico, no comercial). Cada pieza
  DEBE tener ficha (referencia, tipografías y licencias, costo 0) y la aprobación de un integrante
  (`approve --by`); `check` lo verifica.
- El uso de asistentes de IA se declara y se verifica; el equipo asume la responsabilidad del código y de las
  afirmaciones. Los asistentes no figuran como autores ni coautores en Git ni en GitHub (§4.3).
- Los prompts y resultados no se inventan ni se editan para simular éxito.

---

## 11. Enmiendas y versionado

- Versión semántica `MAJOR.MINOR.PATCH`.
- **MAJOR**: eliminar o redefinir un principio, cambiar el alcance del proyecto o la licencia.
- **MINOR**: añadir una fase, un estándar técnico o una puerta de calidad.
- **PATCH**: aclaraciones o correcciones sin cambio de reglas.
- Procedimiento: propuesta escrita → revisión de ambos → aprobación por consenso →actualización de
  `CONSTITUTION.md`, README y documentos dependientes → registro en `docs/decisions/`.
- Una enmienda no invalida retroactivamente entregas ya aprobadas; si cambia una regla de evaluación, se
  aplica desde la fase siguiente.
- Revisión obligatoria al cierre de cada fase y antes de cada entrega.

**Historial reciente** (las versiones anteriores se reconstruyen con `git log -- CONSTITUTION.md`):

| Versión | Fecha | Cambio |
|---------|-------|--------|
| 2.1.0 | 2026-11-24 | **MINOR**: plataforma web en cuatro áreas con API v1 de planificación y evidencia (spec 026, ADR 0030); §3.7 amplía la aplicación web (autorización en backend, cifras solo del servidor, identidad visual por producto). |
| 2.1.1 | 2026-11-25 | **PATCH**: la app se abre desde un clon limpio o tras un `git pull` con `make app` o `webbuild --serve`, que compilan la web solo si falta o está desactualizada; el servidor advierte si sirve una compilación vieja (§3.7). |
| 2.2.0 | 2026-11-25 | **MINOR**: perfiles abiertos en la web (spec 027, ADR 0031): la autorización del planificador depende del canal; en la web los cinco perfiles y la consola `/api/v1/planning` son de libre elección, en WhatsApp sigue la lista de autorizados. Se enmiendan §3.7 y la regla 20; se conservan los dos pasos, el registro por seudónimo, las cifras solo del optimizador y el modo degradado sin planificación. Requiere la aprobación de ambos integrantes. |
| 2.2.1 | 2026-11-25 | **PATCH**: `make app` detecta un servidor de otra versión en el puerto y no arranca encima; `GET /api/version`, la versión en el pie de la web y las páginas sin caché (§3.7). |
| 2.3.0 | 2026-11-26 | **MINOR**: video pitch de la entrada generado con MAGI-2 (spec 028, ADR 0032): primer elemento, saltable y sin repetirse en la sesión; producción única con MAGI-2 por la API de Higgsfield (clave solo en `.env`, tope de gasto), guion con fuentes, ficha de la imagen, revisión humana y declaración de IA junto al video (§3.7 y §10). Requiere la aprobación de ambos integrantes. |
| 2.4.0 | 2026-11-26 | **MINOR**: pitch v2 sincronizado (spec 029, ADR 0033): escenas por planos con momentos ligados a palabras (faster-whisper local), gráficos propios del montaje y reajuste acotado de planos; modelo por preferencia (MAGI-2 si responde, si no Kling 4.0, decisión del integrante tras el `403 model_unavailable` de MAGI-2 en Higgsfield); borrador y publicación que conservan la v1 hasta el chequeo (§3.7 y §10). Requiere la aprobación de ambos integrantes. |
| 2.5.0 | 2026-11-27 | **MINOR**: imágenes de perfil de Valer-IA (spec 030, ADR 0034): foto de perfil y portadas de WhatsApp, LinkedIn y Facebook compuestas a partir de la imagen de referencia sintética, sin modelos generativos y sin costo, con la declaración de IA en el texto del perfil de cada red, ficha y aprobación humana por pieza (§10). Requiere la aprobación de ambos integrantes. |
| 2.6.0 | 2026-11-27 | **MINOR**: frontend profesional de Valer-IA (spec 031, ADR 0035): entrada como sitio de producto de una sección por pantalla con el video pitch en el hero; cuatro áreas con un mismo sistema (paleta de marca con los colores del logotipo, Archivo, un botón primario verde); fotos sustitutas de Wikimedia Commons con licencia libre citadas; skill `design-taste-frontend` sin copiar su kit; la consulta de los Módulos 1 y 2 pasa a la evidencia (§3.7). Requiere la aprobación de ambos integrantes. |
| 2.7.0 | 2026-11-27 | **MINOR**: audios de los stickers de Valer-IA (spec 030 US6, ADR 0036): la frase de cada sticker con la voz oficial del agente (Phonon, spec 016), sintetizada en local y sin costo, en OGG/Opus de ≤ 5 s, con licencia CC BY-NC 4.0 y atribución en la ficha, y aprobación de un integrante por audio (§10). Requiere la aprobación de ambos integrantes. |
| 2.8.0 | 2026-11-27 | **MINOR**: Valer-IA natural y con voz por WhatsApp (spec 028, ADR 0037): SIM dedicada con modo cerrado y abierto (regla 9); confirmación de escrituras en lenguaje natural (regla 11); modo degradado a los 90 s y MCP de 15 lecturas sin planificación (regla 12); hardening sin Docker cuando el servidor no permite virtualización, con Qdrant nativo (regla 14); olvido por intención natural (regla 16); planificador libre en WhatsApp y activado por contexto (regla 20); nueva regla 22 (conversación sin comandos y voz local con guion sin citas). Requiere la aprobación de ambos integrantes. |
| 2.9.0 | 2026-11-27 | **MINOR**: canal de WhatsApp abierto a cualquier número (spec 031): el modo abierto se usa hasta el fin del proyecto, con límites por seudónimo (ventana corta y tope diario con un único aviso natural), bloqueo de seudónimos, atajos ocultos solo para operadores (`VALERIA_OPERATORS`) y el modo visible en `ops check`. Se enmienda la regla 9 (antes: modo abierto sin límite y solo en el ensayo y la jornada). Requiere la aprobación de ambos integrantes. |
| 2.10.0 | 2026-11-27 | **MINOR**: pestaña WhatsApp en la web (spec 032, ADR 0038): quinta área `/whatsapp` con el enlace al chat (WhatsApp Web en computador, aplicación en teléfono) y un QR generado con `segno`; el número sale de `VALERIA_WHATSAPP_NUMBER` en el `.env` externo y lo expone `GET /api/channels/whatsapp`, público y de solo lectura (§3.7). Requiere la aprobación de ambos integrantes. |
| 2.11.0 | 2026-11-28 | **MINOR**: respuesta a cuentas de WhatsApp identificadas solo por ID (spec 033, ADR 0039): un parche versionado, anclado y verificado por `ops check` corrige el componente de WhatsApp mientras no exista la corrección oficial (regla 8); los ID `…@lid` se seudonimizan como los números (regla 10); las entregas tardías (más de 15 minutos) se descartan sin responder. Requiere la aprobación de ambos integrantes. |
| 2.11.1 | 2026-11-28 | **PATCH**: segundo parche versionado del componente de WhatsApp bajo la regla 8 (spec 037, ADR 0040): `whatsapp-sticker.mjs` expone `sendSticker` en el listener activo y envía los `valeria-*.webp` como sticker nativo por el adaptador de salida (OpenClaw aísla el runtime por plugin); se verifica con `ops check` (`soporte-sticker`, `stickers-hoy`). Sin cambio de principios. |
| 2.0.0 | 2026-11-24 | **MAJOR**: el producto final se reenfoca en la idea 7 (spec 025, ADR 0029). Valer-IA pasa a ser una plataforma de agentes por perfil (visitante, cliente B2B, proveedor, colaborador y planificador) con un agente de planificación industrial (simulador y optimizador lineal sobre datos sintéticos declarados). §1 producto final; Fase 3 reglas 16–21; §8.4 reenfoque. Las reglas 8–15 siguen vigentes. |
| 1.16.0 | 2026-11-23 | Fase 3 concretada para el Anuncio 007 (spec 024, ADR 0028): WhatsApp por OpenClaw con un solo agente y plugin puente; número de un integrante con allowlist y emparejamiento solo en la jornada; seudónimos HMAC; catálogo único de 20 herramientas; MCP de solo lectura y modo degradado; SQLite como equivalente de PostgresSaver; Node/TypeScript solo para el plugin; dependencias `mcp`, `scikit-learn` y `matplotlib`; §8.4 rúbrica del Módulo 3; documentos de despliegue, manual y rúbrica. |
| 1.15.0 | 2026-11-23 | Dictado por voz local con faster-whisper y privacidad del audio (spec 023, ADR 0027). |

---

## 12. Cumplimiento y revisión

- Todo PR DEBE declarar en su descripción cómo cumple esta constitución.
- La puerta de cada fase DEBE auditarse con evidencia, no con afirmaciones.
- Una violación no justificada bloquea la fusión y la demo hasta corregirse.
- Las excepciones se documentan como decisión, con motivo, alcance y fecha de revisión.
- La revisión de cumplimiento se hace al inicio y al cierre de cada fase, y antes de cada sustentación.

---

## Anexo A — Comandos canónicos

```bash
uv sync
cd web && npm ci && cd ..
uv run python scripts/scrape_empresa.py
make app
make check
make e2e
git log --oneline --graph -20
```

Equivalencias actuales que deben documentarse o envolverse:

- `scripts/scrape_empresa.py` puede delegar en `scripts/run_campaign.py`.
- `uv run pml ...` es la CLI del pipeline; la app no depende de ella en tiempo de ejecución.
- La capa bronce actual se llama `data/bronze/`; equivale a `data/raw/` de la rúbrica.

---

## Anexo B — Checklist obligatorio para la Entrega 1

- [ ] Repositorio público en GitHub.
- [ ] `LICENSE` MIT con año y titulares correctos.
- [ ] README con badges, problema/solución, arquitectura, instalación, uso, estructura, capturas, licencia y
      créditos.
- [ ] `pyproject.toml`, `uv.lock` y `.python-version`.
- [ ] `uv sync` funciona desde un clon limpio.
- [ ] Pipeline ejecutable con `uv run python scripts/scrape_empresa.py`.
- [ ] Capas `data/raw`, `data/processed`, `data/gold` o equivalencia documentada.
- [ ] Corpus con URL, título, sección, fecha y hash.
- [ ] Experiencia web React + FastAPI con Consulta, Resumen, FAQ y showcase.
- [ ] `make app` funciona y `make check` incluye la verificación web.
- [ ] Q&A cita la fuente y declara cuando no hay evidencia.
- [ ] Panel de scraping con URLs, páginas, tokens y descartes.
- [ ] Al menos 2 PR fusionados con revisión y checks verdes.
- [ ] Historial con Conventional Commits y sin binarios ni `.env`.
- [ ] `.env` fuera del repositorio y en `.gitignore`.
- [ ] 20 preguntas evaluadas y tabuladas.
- [ ] Informe con las cinco secciones.
- [ ] CI con Ruff y pytest en verde.
- [ ] Demo de 12+3 minutos ensayada, sin diapositivas.
- [ ] Tag `v0.1.0-modulo1`.

Deseables que suman: `specs/`, `AGENTS.md`, hook GGA activo, decisión en Engram, `SKILL.md`, pruebas del
scraper, deploy en Hugging Face Spaces y diagrama de arquitectura.

---

## Anexo C — Diagnóstico de cumplimiento al 2026-10-29 (no normativo)

| Requisito | Estado actual | Acción antes del 31-oct | Responsable |
|-----------|---------------|--------------------------|-------------|
| Repositorio público | Cumple | Mantener visibilidad y ramas limpias | Ambos |
| Licencia MIT | Pendiente | Crear `LICENSE` 2026 y declararla en README/pyproject | Ambos |
| README profesional | Parcial | Badges, arquitectura, capturas, créditos y licencia | Ambos |
| 2 PR fusionados | Pendiente (0) | Crear PRs desde ramas feat/docs y revisar | Ambos |
| App web React/FastAPI | Cumple | Frontend y API con Consulta, Resumen, FAQ y showcase | Roberto |
| LangChain y tres tareas | Pendiente | Añadir dependencias y tareas Resumen/FAQ/Q&A | Roberto |
| `data/silver` y `data/gold` | Pendiente | Chunks y base de conocimiento consolidada | Jason |
| Metadata de sección | Parcial | Enriquecer corpus y documentar campos | Jason |
| Pipeline canónico | Parcial | Crear `scripts/scrape_empresa.py` como wrapper | Jason |
| Etapas y métricas en UI | Parcial | Exponer descubrir/extraer/limpiar/deduplicar/enriquecer | Roberto |
| 20 preguntas evaluadas | Pendiente | Diseñar, ejecutar y tabular | Ambos |
| Informe cinco secciones | Pendiente | Redactar y revisar | Ambos |
| CI Ruff + pytest | Pendiente | Añadir workflow y badge | Ambos |
| Demo 12+3 | Pendiente | Ensayar con app, repo e IDE | Ambos |
| Pruebas offline | Cumple (60) | Mantener y ampliar a prompts/app | Ambos |
| Specs versionadas | Cumple | Mantener por fase | Ambos |

**Ruta crítica para el 31-oct**: licencia + app + tres tareas LangChain + silver/gold + 20 preguntas + informe +
2 PRs + CI + README. Sin estos elementos no se alcanza el nivel 5 de la rúbrica.

---

## Anexo D — Estado de estandarización al 2026-10-31 (no normativo)

Auditoría con `jan-project-standard` sobre el repositorio:

- **Identidad verificada**: GitHub `jasonCastano`, autor Jason Alejandro Castaño,
  correo `jasonale3007@gmail.com`, remoto `https://github.com/jasonCastano/proyecto_modelos_lenguaje.git`.
- **Añadido**: `.editorconfig`, `Makefile`, `.pre-commit-config.yaml`, `CONTRIBUTING.md`,
  `CODE_OF_CONDUCT.md`, `AGENTS.md`, `.opencode/rules/tgrep.md`, plantillas de PR e issues,
  Dependabot, labels, workflow de labels e índice `docs/README.md`.
- **Conservado**: `README.md`, `CONSTITUTION.md`, `LICENSE`, `pyproject.toml`, `.gitignore` y
  `.github/workflows/ci.yml`, adaptados sin reemplazarlos.
- **Arquitectura**: `docs/arquitectura.json` + `docs/arquitectura.html` generados y validados con
  Archify (`finalize --quality showcase`); captura enlazada desde el README. Decisión registrada en
  `docs/decisions/0011-project-standard.md`.
- **Estado técnico**: experiencia web React + FastAPI, tareas LangChain, capas medallion y auditoría E2E
  operativas; 323 pruebas Python + 12 pruebas web y CI verde.
- **Pendiente**: evaluación de 40 preguntas, informe, guion de demo, capturas restantes y tag
  `v0.1.0-modulo1`.

---

## Anexo E — Análisis del material actualizado y ruta del Módulo 2 al 2026-11-07 (no normativo)

> **Estado al 2026-11-11**: la ruta descrita en este anexo quedó implementada en la spec 014 (US1–US5, PRs
> #44–#50 y el PR de cierre). Resultados y pendientes en `docs/informe_modulo2.md` §5–§6; la decisión de
> arquitectura en `docs/decisions/0016-rag-agent-langgraph.md`.

**Identidad verificada**: GitHub `jasonCastano` (Jason Alejandro Castaño, `jasonale3007@gmail.com`), remoto
`jasonCastano/proyecto_modelos_lenguaje`.

**Material nuevo del curso**: `TAAML_diapositivas.md` (deck consolidado, extraído 2026-11-07), Clase 7 (bases
vectoriales y ANN), Clase 9 (RAG avanzado, Jev y HITL) y su página de Campus. Sin documento oficial de la
Entrega 2.

**Requerimientos nuevos o precisados**:

| # | Requerimiento | Fuente | Antes (v1.2.0) | Acción |
|---|---------------|--------|----------------|--------|
| 1 | Pesos 30/30/40 y nombre de la Fase 2 «Agente con memoria y enrutador» | Proyecto Integrador | No registrado | §1, §8.3 |
| 2 | Enrutamiento documental vs. estructurado (SQL/CSV) | Proyecto Integrador | Ausente | Regla 7 Fase 2 |
| 3 | Memoria corta (checkpointer/`thread_id`) y larga (Store) con retención | Clase 6 | Opcional y genérica | Reglas 5–6 |
| 4 | Embeddings elegidos por retrieval en español (MTEB) | Clase 6 | Genérico | Regla 1 |
| 5 | Base vectorial embebida persistente, índice como vista derivada | Clase 7 | Genérico | Regla 2 |
| 6 | 20–30 consultas etiquetadas, Recall@10 y nDCG@10, dos configuraciones | Clase 7 | Recall@k y MRR | Regla 10 |
| 7 | RAG Chain vs. RAG Agent (latencia, llamadas) | Clase 9 | Ausente | Regla 8 |
| 8 | Inyección indirecta con etiquetas XML y prueba maliciosa | Clase 9 | Principio IV sin prueba | Regla 9 |
| 9 | Human-in-the-Loop: lectura automática, escritura con aprobación | Clase 9 | Ausente | Regla 9 |
| 10 | Ragas + LangSmith para evaluación y observabilidad | Clase 9 (próxima sesión) | Ausente | Regla 11 |
| 11 | Fase 3 con canales WhatsApp/Telegram y Agent OS | Proyecto Integrador | Solo HF Spaces | Fase 3 |
| 12 | Jev (System One) y LLM Wiki/OKF | Clase 9 | — | Opcionales |

**Pendientes heredados del Módulo 1** (bitácora 2026-11-06): evaluación de 40 preguntas, informe, guion de demo,
capturas y tag `v0.1.0-modulo1`. Se cierran antes de iniciar la implementación de la Fase 2 (puerta de fase).

**Ruta de trabajo del Módulo 2** (cada paso por rama + PR revisado):

1. Cerrar la puerta de la Fase 1 y etiquetar `v0.1.0-modulo1`.
2. Revisar y fusionar el PR #34 (spec 013: índice semántico e híbrido) con aprobación cruzada formal.
3. `/speckit-clarify` → `/speckit-plan` → `/speckit-tasks` sobre `specs/014-rag-agent-memory-router/`.
4. Ampliar el conjunto de evaluación del PR #34 con ruta esperada y añadir Recall@10 y nDCG@10; citar evidencia
   MTEB-es en la ADR 0014.
5. Comparar léxica, semántica e híbrida en un solo reporte.
6. Tabla estructurada derivada del oro + enrutador (directo/documental/estructurado/fuera de alcance).
7. Agente con el retriever como herramienta, memoria por `thread_id` y comparación Chain vs. Agent.
8. Blindaje: aislamiento XML, prueba de documento malicioso y HITL.
9. App: conversación multi-turno con ruta, fragmentos y fuentes; modo demo completo; E2E.
10. Ragas + LangSmith, informe, prompt log, ADRs, demo y tag `v0.2.0-modulo2`.

---

## Anexo F — Auditoría del proyecto al 2026-11-07 (no normativo)

Auditoría con `jan-project-standard` (`new_project.py --audit`, con `PYTHONIOENCODING=utf-8` en Windows),
`make check` y la API de GitHub. Ejecutada por Jason Alejandro Castaño con asistencia de Claude Code.

| # | Hallazgo | Severidad | Regla | Acción |
|---|----------|-----------|-------|--------|
| 1 | Estándar: 0 FALTA, 7 OK, 18 DIFIERE (personalización legítima del proyecto) | Info | Skill | Ninguna |
| 2 | `make check` verde: 323 pruebas Python (12 omitidas) + 13 web, Ruff limpio, build web OK | Info | §3.8 | Badges y cifras del README actualizados (336) |
| 3 | `main` sin protección de rama ni rulesets: se permite push directo | Alta | §4.2 | Corregido: PR con 1 aprobación, checks `test` y `web`, sin force-push |
| 4 | Los 32 PRs fusionados tienen 0 aprobaciones formales en GitHub | Alta | Principios VI y VIII, §4.2 | Pendiente: aprobar con «Approve» el PR del otro integrante desde ahora |
| 5 | Colisión de numeración: spec `013-*` y ADR `0014-*` locales vs. PR #34 | Media | §5 transversal | Corregido: spec renumerada a 014 y ADR a 0015 |
| 6 | Evaluación de 40 preguntas (M1-08) e informe sin hacer; la sustentación del 31-oct ya pasó | Alta | §5 Fase 1, §6 | Borrador de `docs/informe_modulo1.md`; evaluador `module1_eval` (zero-shot vs. final); falta ejecución real y calificación humana |
| 7 | Sin tag `v0.1.0-modulo1` ni release | Media | §4.5 | Pendiente tras M1-08 |
| 8 | PR #34 fusionado con 0 revisiones formales; reproduce sus cifras, pero no reporta Recall@10/nDCG@10 y el umbral 0,30 no abstiene fuera de corpus (similitudes 0,80–0,87) | Alta | §5 Fase 2 reglas 7 y 10 | Revisión en `docs/revision_pr34.md`; acciones en spec 014 (FR-011, FR-020) |
| 9 | `.specify/memory/constitution.md` en v1.0.0, sin las enmiendas 1.1–1.3 | Baja | Prevalencia | Nota de alineación añadida (v1.0.1) |
| 10 | `docs/demo.md` inexistente | Media | §9 | Borrador escrito; falta ensayo cronometrado |
| 11 | Repositorio sin *topics* ni *homepage* en GitHub | Baja | README profesional | Opcional |
| 12 | `docs/prompt_log.md` §2 aún declara `llama3.1:8b` y no hay línea base real con DeepSeek (T045/T046) | Media | §3.6 | Modelo corregido y prompt zero-shot registrado; la línea base real llega con M1-08 |

**Verificado sin hallazgos**: repositorio público, `LICENSE` MIT reconocida por GitHub, CI verde en las últimas
ejecuciones, `.env` fuera del índice de Git, sin claves ni binarios pesados fuera de Git LFS, Dependabot activo y
19 etiquetas declarativas.

---

## Firmas

Ratificada por los coautores del proyecto:

**Jason Alejandro Castaño** — Co-owner, datos y pipeline

**Roberto José Guerrero** — Co-owner, LLM y aplicación

Fecha: 2026-10-29

---

**Versión**: 2.11.1 | **Ratificada**: 2026-10-29 | **Última enmienda**: 2026-11-28
