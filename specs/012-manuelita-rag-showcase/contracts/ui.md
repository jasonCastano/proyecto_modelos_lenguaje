# UI Contract — “Cañaveral editorial”

**Feature**: `012-manuelita-rag-showcase`
**Versión**: 1.0
**Fecha**: 2026-10-31

## 1. Alcance

Contrato visual y de interacción para la página única que reemplaza la interfaz Streamlit. Define composición, tokens, estados, accesibilidad y criterios de aceptación. No define la lógica del RAG, que vive en la API.

## 2. Estructura de la página

Una sola ruta con anclas semánticas, en este orden:

1. **Hero**: titular, explicación breve, CTA “Preguntar al corpus” y CTA secundaria “Recorrer el Módulo 1”. Incluye el gesto de cañaveral.
2. **Consola RAG**: selector de tarea (Consulta, Resumen, FAQ), campo de pregunta, botón, estado, respuesta, citas y reintento.
3. **Problema**: por qué existe el sistema.
4. **Datos y medallion**: fuentes → bronce → plata → oro, con cifras reales.
5. **Prompts y tareas**: qué se construyó y cómo se controla la alucinación.
6. **App y evaluación**: qué permite la experiencia, qué se midió y qué falta.
7. **Límites y fuentes**: limitaciones, créditos, enlaces de evidencia y aviso académico.

Las anclas deben permitir navegar con teclado y enlazar directamente a una sección.

## 3. Tokens visuales

```css
--forest: #387C2B;
--orange: #E86D1F;
--lime: #B0BC22;
--gold: #FFD200;
--paper: #F5F7F3;
--ink: #14240F;
--ink-muted: #3F4A3C;
--line: color-mix(in srgb, var(--ink) 18%, transparent);
--surface-raised: #FFFFFF;
--radius-sm: 4px;
--radius-md: 10px;
```

No se introduce una paleta paralela. Cualquier color nuevo debe derivar de estos tokens y justificarse por contraste.

## 4. Tipografía

- **Display**: `Bricolage Grotesque Variable`, pesos 500–800, tracking ligeramente negativo en titulares grandes.
- **Body**: `Public Sans Variable`, pesos 400–700, `line-height` 1.55–1.7.
- **Datos**: Public Sans con `font-variant-numeric: tabular-nums`.
- Escala:
  - Hero: `clamp(3rem, 7vw, 7rem)`.
  - Título de sección: `clamp(2rem, 4vw, 4rem)`.
  - Cuerpo: 17–18 px.
  - Caption: 13–14 px, sin mayúsculas forzadas.
- Ancho de lectura ≤ 72 caracteres.
- No se usa monospace para etiquetas decorativas ni se acentúa una sola palabra del titular con otro color.

## 5. Composición y motivos

- **Hero asimétrico** (7/5 o 8/4): texto a la izquierda, cañaveral SVG a la derecha; en móvil el gesto pasa detrás o debajo sin tapar el texto.
- **Cañaveral**: líneas verticales/curvas que nacen en el hero y continúan como veta entre secciones; representan el pipeline y el crecimiento del corpus.
- **Cristal de azúcar**: retícula geométrica para separar métricas y unidades; no es un adorno repetido en cada card.
- **Onda de energía**: trazo para la sección de evaluación/resultados.
- **Palma**: marca secundaria en el cierre; no compite con el hero.
- **Prohibido**: cuadrícula uniforme de cards idénticas, sombras suaves genéricas, eyebrows en mayúsculas, numeración decorativa 01/02/03, gradientes como relleno.

## 6. Estados de la consola

| Estado | Comportamiento visual |
|--------|-----------------------|
| `idle` | Campo vacío, CTA activo, ejemplo de pregunta sugerido. |
| `submitting` | Botón deshabilitado, progreso visible, pregunta conservada. |
| `success` | Respuesta, metadatos y citas; foco en el encabezado de respuesta. |
| `fallback` | Mensaje explícito, sin citas, oferta de reformular. |
| `error` | Mensaje accionable, código discreto y botón “Reintentar”. |
| `demo` | Banner persistente “Modo demostración”; respuestas rotuladas. |
| `missing_key` | Aviso y CTA “Usar modo demostración”. |

El cambio de tarea conserva la última pregunta de esa tarea o declara que se limpió.

## 7. Citas

Cada cita muestra:

- Etiqueta `[U#]`.
- Título.
- Sección o página/tiempo.
- Enlace externo con `rel="noreferrer noopener"`.
- Indicador de autoridad (`first_party`, `third_party`).

Las citas se agrupan bajo “Fuentes”; no se esconden en tooltips. Si el enlace falla, el título y la URL siguen visibles.

## 8. Responsive

| Ancho | Regla |
|-------|-------|
| 360–639 | Una columna; hero con gesto reducido; consola a ancho completo; tipografía fluida. |
| 640–1023 | Una columna con bandas de datos a dos columnas; hero 1:1. |
| 1024–1439 | Hero asimétrico; narrativa con rail lateral; métricas en 3–4 columnas. |
| ≥1440 | Composición editorial amplia, máximo 1440 px de contenido; no estirar líneas. |

Sin scroll horizontal en ningún ancho. El foco y el orden DOM siguen el orden visual.

## 9. Accesibilidad

- HTML semántico: `header`, `main`, `section`, `nav`, `footer`.
- Un solo `h1`; jerarquía sin saltos.
- Foco visible con `outline` de alto contraste; nunca `outline: none` sin sustituto.
- Labels asociados a inputs; errores con `aria-live`.
- Contraste mínimo 4.5:1 texto normal y 3:1 texto grande/controles.
- `prefers-reduced-motion`: desactiva la entrada y cualquier animación no esencial.
- Teclado: todo el flujo de consulta, cambio de tarea y apertura de fuentes.
- Textos alternativos en SVG decorativos con `aria-hidden`; los informativos llevan título.

## 10. Movimiento

- Una sola secuencia de entrada en el hero (cañaveral y titular), ≤ 900 ms.
- La respuesta aparece con un fade corto; no se anima cada sección al hacer scroll.
- `prefers-reduced-motion` reduce a opacity instantánea.
- No se usa parallax ni autoplay.

## 11. Copy

- Español claro, voz activa, frases cortas.
- El CTA dice exactamente qué ocurre: “Preguntar al corpus”, “Ver fuentes”, “Reintentar”.
- Los errores explican qué pasó y qué hacer; no se disculpan ni usan jerga.
- El aviso académico es explícito y visible en el footer.
- No se inventan cifras, productos ni certificaciones.

## 12. Selectores de prueba

| Elemento | Selector |
|----------|----------|
| Hero | `[data-testid="hero"]` |
| Consola | `[data-testid="rag-console"]` |
| Campo de pregunta | `[data-testid="question-input"]` |
| Botón enviar | `[data-testid="ask-button"]` |
| Respuesta | `[data-testid="answer-panel"]` |
| Fuentes | `[data-testid="source-list"]` |
| Estado demo | `[data-testid="demo-banner"]` |
| Métricas | `[data-testid="metric-band"]` |
| Narrativa | `[data-testid="showcase-story"]` |
| Aviso de límites | `[data-testid="limits-note"]` |

## 13. Presupuesto de rendimiento

- LCP < 3 s en banda ancha.
- JS inicial < 250 KB gzip.
- Fuentes subseteadas y `font-display: swap`.
- SVG inline para los motivos; sin imágenes pesadas above the fold.
- La consola no bloquea el render del showcase; la API se consulta después de la interacción.

## 14. No objetivos

- Multi-página, login, cuentas o persistencia en servidor.
- Chat multi-turno con memoria; la sesión conserva solo la última consulta/respuesta.
- Modo oscuro completo en la primera entrega; se puede añadir si no rompe la identidad.
- Sustituir el sitio oficial de Manuelita.
- Mostrar fotos de producto sin fuente.
