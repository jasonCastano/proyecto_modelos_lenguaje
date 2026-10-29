# Constitución del Proyecto — RAG Ingenio Manuelita

**Versión**: 1.0.0 | **Ratificada**: 2026-10-29 | **Última enmienda**: 2026-10-29

**Equipo**: Jason Alejandro Castaño · Roberto José Guerrero

**Curso**: Técnicas Avanzadas de IA aplicadas en Modelos de Lenguaje — Maestría en IA y Ciencia de Datos,
Universidad Autónoma de Occidente, 2026-2S

**Docente**: Jan Polanco Velasco

**Empresa**: Ingenio Manuelita S.A. — Valle del Cauca, Colombia — https://www.manuelita.com/

**Repositorio**: https://github.com/jasonCastano/proyecto_modelos_lenguaje

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

Esta constitución es obligatoria para los dos integrantes. Aplica a código, datos, prompts, modelos,
interfaces, pruebas, documentación, repositorio, presentación y uso de herramientas de IA.

**Criterio de éxito**: cumplir la rúbrica del curso, demostrar el sistema en vivo y poder explicar cada
decisión técnica sin depender de diapositivas ni de la memoria de una sola persona.

---

## 2. Principios no negociables

### I. Integridad académica y autoría

- Todo entregable DEBE ser producido por Jason Alejandro Castaño y Roberto José Guerrero, o declarar
  explícitamente la herramienta de IA utilizada como asistencia.
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
- Los datos y artefactos pesados NO se versionan; se referencian por manifiesto y hash.
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
- Estructura `src/` para el paquete `proyecto_modelos_lenguaje`.
- Ruff para lint y formato; `pytest` para pruebas.
- Dependencias de runtime y desarrollo separadas; versiones fijadas en `uv.lock`.
- Variables de entorno para claves y configuración sensible; `.env` fuera del repositorio.

### 3.2 Estructura del repositorio

```text
app.py                         # interfaz Streamlit/Gradio (Módulo 1)
src/proyecto_modelos_lenguaje/ # paquete: datos, prompts, LLM, RAG
scripts/                       # entradas operativas reproducibles
config/                        # fuentes, reglas y parámetros versionados
data/                          # capas medallion (no versionado)
specs/                         # especificaciones, planes y contratos
tests/                         # unitarias, integración y contrato
docs/                          # alcance, decisiones, informe, prompt log
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
- El presupuesto de almacenamiento de la capa bronce es 10 GB; `data/` nunca se versiona.

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
- El modelo puede ser open source vía Ollama o privado vía API. La elección DEBE justificarse por costo,
  latencia, calidad, idioma y disponibilidad.
- La configuración del modelo (nombre, versión, temperatura, límite de contexto, tokens) DEBE estar en
  `config/` o variables de entorno documentadas.
- Las claves de API NO se versionan; se leen de `.env` o del gestor de secretos.
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

### 3.7 Aplicación de prueba

- Streamlit es la opción por defecto; Gradio se admite con justificación.
- La app DEBE ejecutarse con `uv run streamlit run app.py` (o el comando equivalente documentado).
- DEBE mostrar tres funcionalidades: Resumen, FAQ y Q&A.
- DEBE incluir campo de pregunta, área de respuesta, citas de fuente y un panel con las métricas del scraping
  (URLs, páginas, tokens, descartes).
- DEBE manejar errores de modelo, contexto vacío y timeout sin romper la interfaz.
- NO DEBE exponer claves, rutas absolutas ni datos sensibles.

### 3.8 Pruebas y calidad

- `uv run pytest` DEBE pasar sin red para las pruebas unitarias y de contrato.
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

### 4.4 Integración continua

- GitHub Actions DEBE ejecutar `uv sync --frozen`, `uv run ruff check .` y `uv run pytest`.
- El badge de CI DEBE mostrarse en el README.
- Un fallo de CI bloquea la fusión.
- Se recomienda publicar cobertura y un artefacto de ejemplo del corpus.

### 4.5 Versionado y entregas

- Cada entrega se etiqueta: `v0.1.0-modulo1`, `v0.2.0-modulo2`, etc.
- El tag debe apuntar a un commit con CI verde y README actualizado.
- Las releases incluyen notas de cambios y limitaciones conocidas.

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
LangChain y una interfaz Streamlit/Gradio.

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
4. **Aplicación de prueba**:
   - `app.py` con las tres funcionalidades.
   - Panel de scraping y Q&A con cita de fuente.
   - Ejecutable con `uv run streamlit run app.py`.
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

### Fase 2 — Módulo 2: Embeddings, memoria y RAG

**Objetivo**: evolucionar el Q&A a un sistema RAG con recuperación semántica, embeddings y memoria persistente.

**Reglas mínimas**:

1. **Embeddings**: elegir un modelo multilingüe adecuado para español y justificarlo por calidad, costo y
   latencia. Registrar dimensión, normalización y límite de tokens.
2. **Base vectorial**: elegir Chroma, FAISS, pgvector u otra, con justificación y persistencia reproducible.
3. **Chunking**: definir tamaño, solapamiento, metadatos y estrategia de recuperación; documentar el impacto
   en la calidad.
4. **Recuperación**: medir al menos Recall@k, MRR y calidad de las citas; comparar con la línea base del
   Módulo 1.
5. **RAG**: el LLM responde solo con los fragmentos recuperados, cita fuentes y declara cuando no hay
   evidencia.
6. **Memoria**: si se implementa memoria conversacional, definir qué se persiste, por cuánto tiempo y cómo se
   elimina; no almacenar datos sensibles.
7. **Integración**: la app debe permitir ver la pregunta, los fragmentos recuperados, la respuesta y las
   fuentes.
8. **Evaluación**: conjunto de preguntas ampliado, métricas de recuperación y fidelidad, análisis de errores.
9. **Informe y demo** actualizados; tag `v0.2.0-modulo2`.

**Nota**: si la especificación oficial del Módulo 2 difiere, se enmienda esta constitución antes de iniciar la
fase; no se improvisa sobre la marcha.

---

### Fase 3 — Módulos siguientes: chatbot final

**Objetivo**: convertir el Q&A/RAG en un chatbot evaluado y desplegable.

**Reglas mínimas**:

1. **Conversación**: manejo de contexto, memoria, turnos y fallback.
2. **Guardrails**: rechazo de preguntas fuera de alcance, protección contra prompt injection y contenido
   dañino.
3. **Evaluación**: conjunto de evaluación con métricas de fidelidad, relevancia, latencia y costo; pruebas de
   regresión.
4. **Despliegue**: Hugging Face Spaces u otro entorno reproducible; variables de entorno seguras.
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
| App | `uv run streamlit run app.py` funciona desde un clon limpio |
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
| Implementación y calidad de la app | 15% | `app.py` con tres funcionalidades, métricas y citas |
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

---

## 10. Ética, privacidad y uso de IA

- Solo se usa información pública; no se eluden autenticaciones, muros de pago ni captchas.
- No se incorporan datos personales sensibles; los cargos y nombres corporativos públicos se usan con fines
  académicos y se citan.
- El contenido de terceros se atribuye; se atienden solicitudes de retiro.
- Las respuestas del sistema no deben presentarse como asesoría oficial de Manuelita.
- El uso de asistentes de IA se declara y se verifica; el equipo asume la responsabilidad del código y de las
  afirmaciones.
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
uv run python scripts/scrape_empresa.py
uv run streamlit run app.py
uv run pytest
uv run ruff check .
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
- [ ] App Streamlit/Gradio con Resumen, FAQ y Q&A.
- [ ] `uv run streamlit run app.py` funciona.
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
| App Streamlit/Gradio | Pendiente | Implementar `app.py` con tres funcionalidades | Roberto |
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

## Firmas

Ratificada por los coautores del proyecto:

**Jason Alejandro Castaño** — Co-owner, datos y pipeline

**Roberto José Guerrero** — Co-owner, LLM y aplicación

Fecha: 2026-10-29

---

**Versión**: 1.0.0 | **Ratificada**: 2026-10-29 | **Última enmienda**: 2026-10-29
