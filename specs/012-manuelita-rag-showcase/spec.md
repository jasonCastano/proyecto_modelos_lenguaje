# Feature Specification: Frontend profesional y showcase del Módulo 1

**Feature Branch**: `012-manuelita-rag-showcase`

**Created**: 2026-10-31

**Status**: Draft

**Input**: User description: "@frontend-design mejora la interfaz gráfica de usuario, no utilices más streamlit. Crea un front end profesional para la empresa ingenio Manuelita en donde puedan acceder al RAG desarrollado en el proyecto. Manten el uso de los colores corporativos, utiliza elementos visuales que estén en relación con los productos producidos por la empresa. Despliega el diseño de una página para enseñar lo realizado en el módulo 1"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Consultar el RAG desde una experiencia Manuelita (Priority: P1)

Una persona interesada en Manuelita entra a una página web profesional, entiende de inmediato qué puede preguntar y consulta el corpus. Recibe una respuesta con citas verificables, puede abrir las fuentes y, cuando no hay evidencia, ve un mensaje claro en lugar de una invención.

**Why this priority**: El acceso al RAG es el corazón del producto. Sin una consulta clara, citada y confiable, la página solo sería una vitrina.

**Independent Test**: Abrir la página, escribir una pregunta del alcance, enviarla y comprobar que la respuesta aparece con al menos una cita o con el fallback explícito. Repetir en móvil y con teclado.

**Acceptance Scenarios**:

1. **Given** una persona en la página principal, **When** escribe “¿Qué productos ofrece Manuelita?” y envía, **Then** ve una respuesta y fuentes citadas sin abandonar la página.
2. **Given** una pregunta sin evidencia en el corpus, **When** se envía, **Then** la interfaz muestra “No hay evidencia suficiente” y no presenta una respuesta inventada.
3. **Given** una respuesta con varias fuentes, **When** la persona abre una cita, **Then** reconoce título, sección y enlace de origen.
4. **Given** una persona que usa solo teclado, **When** recorre la página, **Then** puede llegar al campo de pregunta, enviar y abrir fuentes con foco visible.

---

### User Story 2 - Recorrer el Módulo 1 como una historia (Priority: P1)

Un docente, evaluador o miembro del equipo recorre una página que explica qué se construyó en el Módulo 1: el problema, la arquitectura medallion, la base de conocimiento, las tareas de lenguaje, la app, las métricas y la evaluación. La historia se entiende sin diapositivas y sin conocer el repositorio de antemano.

**Why this priority**: El usuario pidió explícitamente una página para enseñar lo realizado en el Módulo 1. Es el entregable de comunicación del proyecto.

**Independent Test**: Recorrer la página de principio a fin y comprobar que un lector externo puede explicar qué se construyó, con qué datos, cómo responde y qué falta, en menos de cinco minutos.

**Acceptance Scenarios**:

1. **Given** un visitante nuevo, **When** llega al hero, **Then** entiende en una frase qué hace el sistema y cuál es el siguiente paso.
2. **Given** un evaluador que baja por la página, **When** llega a la sección del Módulo 1, **Then** ve el flujo datos → conocimiento → respuestas citadas y las cifras del corpus.
3. **Given** un evaluador que revisa la evidencia, **When** abre las métricas, **Then** encuentra pruebas, cobertura, fuentes y limitaciones declaradas.
4. **Given** una persona que solo mira la página, **When** termina el recorrido, **Then** sabe qué se logró, qué se midió y qué queda pendiente.

---

### User Story 3 - Reconocer la identidad y los productos de Manuelita (Priority: P2)

La página se siente propia de una empresa agroindustrial del Valle del Cauca: usa los colores corporativos y un lenguaje visual inspirado en la caña, el azúcar, el etanol, la palma y la energía, sin parecer una plantilla genérica ni una copia del sitio oficial.

**Why this priority**: La identidad visual diferenciada es parte del encargo; una página correcta pero genérica no cumple el objetivo profesional.

**Independent Test**: Mostrar la página a alguien que no conozca el proyecto y pedirle que describa la empresa y los productos que evoca la interfaz; debe mencionar el sector agroindustrial y al menos dos motivos visuales del universo Manuelita.

**Acceptance Scenarios**:

1. **Given** la página en escritorio, **When** se observa el hero, **Then** la paleta verde, naranja y dorada se reconoce como corporativa y no como un tema por defecto.
2. **Given** la sección de productos, **When** se recorren sus motivos visuales, **Then** aparecen referencias a caña, azúcar, etanol, palma o energía sin afirmar productos o cifras no documentadas.
3. **Given** una pantalla móvil, **When** se recorre la página, **Then** la composición conserva jerarquía, legibilidad y el gesto visual principal.

---

### User Story 4 - Operar con datos reales, demo o sin conexión (Priority: P3)

Una persona puede usar el RAG con el proveedor real cuando hay credenciales, o entrar a un modo demostración claramente identificado cuando no hay clave, red o cuota. La página nunca falla en silencio ni muestra una respuesta simulada como si fuera real.

**Why this priority**: La demo y la revisión académica ocurren en entornos con distintas condiciones de red y credenciales.

**Independent Test**: Abrir la página sin clave, con clave y con una respuesta lenta; comprobar que el estado se declara, que el modo demo es visible y que los errores ofrecen una acción.

**Acceptance Scenarios**:

1. **Given** el proveedor sin clave, **When** la persona intenta preguntar, **Then** ve un aviso accionable y la opción de modo demostración.
2. **Given** el modo demostración, **When** se consulta, **Then** la respuesta se rotula como simulada y no se presenta como respuesta real del modelo.
3. **Given** una consulta lenta o un timeout, **When** la interfaz espera, **Then** muestra progreso y permite reintentar sin perder la pregunta.
4. **Given** una respuesta real, **When** se muestra, **Then** incluye proveedor, modelo, latencia y número de citas sin exponer la clave.

---

### Edge Cases

- Pregunta vacía, con solo espacios o de más de 500 caracteres.
- Respuesta muy larga con varias citas y secciones: debe poder leerse sin romper la composición.
- Pregunta fuera del alcance: debe rechazarse o declarar falta de evidencia.
- Error de autenticación, cuota, timeout, red o respuesta vacía del proveedor.
- Navegación en 360 px, tableta vertical, escritorio y pantalla grande.
- Uso con teclado, lector de pantalla, zoom 200 % y preferencia de movimiento reducido.
- Conexión lenta o imágenes que no cargan: el contenido y la consulta deben seguir siendo utilizables.
- Ausencia de JavaScript o fallo de hidratación: debe existir un mensaje comprensible, no una página en blanco.
- Enlaces de fuentes caídos: la cita textual y la URL deben permanecer visibles.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: La experiencia MUST ser una página web propia, pública y navegable, sin la interfaz de la app de prototipo anterior.
- **FR-002**: El hero MUST explicar en una frase qué hace el sistema, para quién es y cuál es la acción principal.
- **FR-003**: La página MUST permitir formular una pregunta al RAG, enviarla y ver el estado de carga.
- **FR-004**: Toda respuesta factual MUST mostrar citas verificables con título, sección o página y enlace de origen.
- **FR-005**: Si no hay evidencia, la interfaz MUST declarar el fallback explícito y no inventar una respuesta.
- **FR-006**: La página MUST ofrecer acceso a las tres tareas del Módulo 1: consulta, resumen del corpus y preguntas frecuentes.
- **FR-007**: La página MUST incluir una sección narrativa del Módulo 1 con problema, datos, arquitectura medallion, prompts, tareas, app, métricas y limitaciones.
- **FR-008**: Las métricas y afirmaciones del showcase MUST provenir de los reportes y datos reales del proyecto; no se inventan cifras ni capturas.
- **FR-009**: La interfaz MUST usar la paleta corporativa: verde bosque `#387C2B`, naranja `#E86D1F`, lima `#B0BC22`, amarillo `#FFD200`, superficie `#F5F7F3` y tinta `#14240F`.
- **FR-010**: El lenguaje visual MUST incorporar motivos relacionados con caña de azúcar, cristales de azúcar, campo, palma, etanol o energía, usados como estructura o información, no como decoración genérica.
- **FR-011**: La composición MUST tener una identidad editorial propia y no depender de una cuadrícula uniforme de tarjetas genéricas.
- **FR-012**: La página MUST ser responsive y utilizable desde 360 px hasta 1920 px sin desplazamiento horizontal.
- **FR-013**: La interfaz MUST cumplir contraste mínimo 4.5:1 en texto normal, foco visible, navegación por teclado y movimiento reducido.
- **FR-014**: El modo demostración MUST ser explícito y visualmente distinguible del proveedor real.
- **FR-015**: Los errores de proveedor, red, timeout, pregunta vacía y falta de clave MUST mostrar un mensaje accionable.
- **FR-016**: La página MUST declarar que es un proyecto académico no afiliado oficialmente a Manuelita.
- **FR-017**: La interfaz MUST no exponer claves, rutas absolutas, trazas internas ni datos privados.
- **FR-018**: La página MUST conservar la pregunta y la última respuesta durante la sesión y permitir reintentar.
- **FR-019**: La página MUST cargar el contenido principal en menos de 3 segundos en banda ancha y ser usable en conexiones lentas.
- **FR-020**: La página MUST incluir una llamada clara a explorar el Módulo 1 y otra a preguntar al corpus.
- **FR-021**: La página MUST poder desplegarse como sitio web y consumir el RAG existente sin cambiar el corpus ni los prompts.
- **FR-022**: La narrativa MUST incluir las limitaciones conocidas y los pendientes de evaluación, sin ocultarlos.

### Visual Direction

La dirección visual se inspira en el paisaje agroindustrial del Valle del Cauca, no en una plantilla SaaS:

- **Paleta**: verde bosque como base institucional, naranja de cosecha como acento, lima y dorado para datos y energía, papel cálido para respirar.
- **Tipografía**: una familia editorial con personalidad para titulares y una sans humanista muy legible para cuerpo; jerarquía por escala, peso y espacio, no por etiquetas en mayúsculas.
- **Composición**: hero asimétrico con una metáfora de caña/campo; una veta visual recorre la página y conecta datos, productos y respuestas.
- **Motivos**: líneas de surco, cristales de azúcar, haces de caña, ondas de energía y palma; cada motivo debe explicar una parte del sistema o de los productos.
- **Principio**: un solo gesto visual memorable; el resto se mantiene sobrio, legible y funcional.

### Key Entities

- **RAG Query**: pregunta de la persona, estado, marca temporal y modo (real o demo).
- **Cited Answer**: respuesta, estado, modelo, latencia, tokens y lista de fuentes.
- **Source Citation**: título, URL, sección, página o tiempo y autoridad.
- **Showcase Section**: bloque narrativo del Módulo 1 con título, propósito, evidencia y métricas.
- **Corpus Metric**: cifra real del corpus con etiqueta, valor, unidad y fuente.
- **Demo State**: modo real, demostración, sin clave, timeout o error.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100 % de las respuestas mostradas incluye al menos una cita o el fallback explícito.
- **SC-002**: Una persona nueva entiende qué hace el sistema y encuentra el campo de pregunta en menos de 10 segundos.
- **SC-003**: Un evaluador puede explicar qué se construyó en el Módulo 1 después de recorrer la página en menos de 5 minutos.
- **SC-004**: La página se usa sin desplazamiento horizontal en 360, 768, 1024, 1440 y 1920 px.
- **SC-005**: El 100 % de los controles principales son accesibles con teclado y tienen foco visible.
- **SC-006**: El contraste de texto normal cumple 4.5:1 y el texto grande 3:1.
- **SC-007**: El contenido principal es visible en menos de 3 segundos en banda ancha y la consulta sigue siendo usable con red lenta.
- **SC-008**: Cero claves, rutas absolutas o trazas internas visibles en la interfaz o en el código enviado al navegador.
- **SC-009**: El 100 % de las cifras del showcase coincide con los reportes del corpus y se puede rastrear a su fuente.
- **SC-010**: Al menos 8 de cada 10 personas reconocen la paleta y los motivos agroindustriales como propios de Manuelita en una prueba rápida de percepción.

## Assumptions

- El backend RAG existente se reutiliza; esta feature cambia la experiencia de acceso, no el corpus, los prompts ni la lógica de recuperación.
- La página se entrega en español y puede desplegarse en un hosting estático o en un servicio web; la decisión técnica se toma en el plan.
- Los colores corporativos se toman de la paleta de marca aprobada del proyecto; no se inventa una paleta nueva.
- Los motivos visuales pueden ser ilustraciones o geometrías originales inspiradas en los productos; no se usan fotos de producto sin fuente.
- El modo demostración sigue disponible para revisión sin clave y sin red.
- La página no pretende ser el sitio oficial de Manuelita y declara su carácter académico.
- Las cifras y capturas se generan desde el proyecto real; no se maquillan resultados.
- El acceso al RAG puede requerir una credencial del proveedor en el servidor, nunca en el navegador.
