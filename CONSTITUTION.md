# Constitución del Proyecto — RAG Ingenio Manuelita

**Versión**: 1.7.0 | **Ratificada**: 2026-10-29 | **Última enmienda**: 2026-11-14

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
- Dependencias de runtime y desarrollo separadas; versiones fijadas en `uv.lock` y `package-lock.json`.
- Variables de entorno para claves y configuración sensible; `.env` fuera del repositorio.

### 3.2 Estructura del repositorio

```text
web/                           # frontend React + Vite + TypeScript
src/proyecto_modelos_lenguaje/ # paquete: API FastAPI, datos, prompts, LLM, RAG
scripts/                       # entradas operativas reproducibles y auditoría visual
config/                        # fuentes, reglas y parámetros versionados
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

- La entrada del producto es una página React/Vite servida por FastAPI; Streamlit ya no es la interfaz.
- La app DEBE ejecutarse con `make app` o `uv run uvicorn proyecto_modelos_lenguaje.api:app`.
- DEBE mostrar tres funcionalidades: Consulta, Resumen y FAQ, con citas y fallback.
- DEBE incluir una página del Módulo 1 con datos, arquitectura, prompts, app, métricas y límites.
- DEBE incluir modo demostración explícito, estados de carga y errores accionables.
- DEBE usar la paleta corporativa y motivos de producto definidos en el contrato UI.
- NO DEBE exponer claves, rutas absolutas ni datos sensibles; la API no devuelve la clave.

### 3.8 Pruebas y calidad

- `uv run pytest` DEBE pasar sin red para las pruebas unitarias y de contrato.
- `make check` DEBE ejecutar Ruff (lint + formato), `pytest` y la verificación web (Vitest + build); el CI corre ambos jobs.
- La app DEBE auditarse con `make e2e` (Playwright) en los perfiles responsive definidos por la feature 012.
- Cada módulo crítico (scraping, chunking, prompts, recuperación, app) DEBE tener al menos una prueba.
- `uv run ruff check .` DEBE pasar sin errores.
- Un PR no se fusiona con pruebas fallidas, lint pendiente o conflictos sin resolver.
- La app y el pipeline DEBEN probarse desde un clon limpio antes de cada entrega.

### 3.9 Seguridad

- `.env`, credenciales, tokens y claves NO se versionan; `.gitignore` los cubre.
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
  Archify y se enlaza desde el README. El HTML no se edita a mano.
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
   - Ejecutable con `make app` o `uv run uvicorn proyecto_modelos_lenguaje.api:app`.
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
9. **Blindaje**: contexto recuperado aislado con etiquetas XML como dato; prueba adversarial con un documento
   malicioso que DEBE pasar. Regla de oro HITL: **lectura automática, escritura con aprobación**
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
    todo sin red ni clave, incluido un corpus adversarial (`MANUELITA_DEMO_CORPUS=malicious`) para mostrar el
    blindaje.
13. **Prompts** nuevos (enrutador, agente, resumen de memoria) versionados en `prompts/` y `docs/prompt_log.md`.
14. **Informe y demo** actualizados; tag `v0.2.0-modulo2`.

**Opcionales que suman**: puerta System One (Jev `Noul`/`Choice`) para screening/routing; exportar el oro como
bundle Open Knowledge Format (LLM Wiki).

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

---

## 10. Ética, privacidad y uso de IA

- Solo se usa información pública; no se eluden autenticaciones, muros de pago ni captchas.
- No se incorporan datos personales sensibles; los cargos y nombres corporativos públicos se usan con fines
  académicos y se citan.
- El contenido de terceros se atribuye; se atienden solicitudes de retiro.
- Las respuestas del sistema no deben presentarse como asesoría oficial de Manuelita.
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

**Versión**: 1.7.0 | **Ratificada**: 2026-10-29 | **Última enmienda**: 2026-11-14
