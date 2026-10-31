# Fase 0 — Investigación: identidad visual Manuelita

**Feature**: `009-manuelita-visual-identity`
**Fecha**: 2026-10-30
**Estado**: decisiones cerradas; sin `NEEDS CLARIFICATION`.

## 1. Paleta institucional

- **Decisión**: usar los seis colores del logotipo público como base de la identidad.
  - Verde bosque `#387C2B` (primario), naranja `#E86D1F` (acento), verde lima `#B0BC22`, amarillo
    `#FFD200`, naranja claro `#F6A01A` y blanco `#FFFFFF`.
  - Texto principal sobre blanco: verde muy oscuro derivado `#14240F`; texto secundario `#3F4A3C`.
- **Racional**: la paleta se extrae de la fuente oficial (el SVG del logotipo declara esos `fill`), no de una
  impresión subjetiva. Es verificable y reproducible, y evita inventar colores «parecidos».
- **Alternativas consideradas**:
  - Tomar la paleta del manual de marca: no es público (requiere inicio de sesión).
  - Muestrear píxeles de capturas del sitio: introduce ruido por compresión y fondos variables.
  - Usar solo el verde: pierde el contraste cálido del naranja que caracteriza la marca.

## 2. Mecanismo de tema

- **Decisión**: combinar el **tema nativo** de Streamlit (`.streamlit/config.toml`) con una capa de
  **CSS propio** para lo que el tema no alcanza (cabecera, tarjetas, badges, pie).
- **Racional**: el tema nativo cubre inputs, tabs y expanders sin riesgo de romper widgets; el CSS propio se
  limita a clases propias del contenido. Menos código y menos superficie de regresión que estilizar todo.
- **Alternativas consideradas**:
  - Solo CSS: frágil ante cambios de Streamlit y difícil de mantener.
  - Solo tema nativo: no permite cabecera con firma, tarjetas de cita ni badges con la paleta.
  - Un framework de UI externo: dependencia nueva injustificada para una sola pantalla.

## 3. Inyección de estilos y regla de seguridad

- **Decisión**: inyectar el CSS estático con `st.html("<style>…</style>")` desde
  `brand.inject_brand_styles()`. `app.py` **no** usa `unsafe_allow_html`.
- **Racional**: la prueba existente `test_app_source_avoids_unsafe_html_and_absolute_paths` protege contra
  HTML no confiable; `st.html` renderiza nuestro CSS sin abrir esa puerta y sin relajar la prueba.
- **Alternativas consideradas**:
  - `st.markdown(..., unsafe_allow_html=True)`: obliga a relajar una prueba de seguridad.
  - Modificar el HTML de la plantilla de Streamlit: no soportado y no reproducible.
  - Renunciar al CSS: incumple los requisitos de tarjetas y badges.

## 4. Firma visual: tipografía en lugar de logotipo raster

- **Decisión**: usar una **firma tipográfica** («Grupo Manuelita» + «Ingenio Manuelita» + lema) construida con
  la paleta, sin copiar el archivo `logo.svg` al repositorio.
- **Racional**: el logotipo es una marca registrada; distribuir el archivo en un repositorio público excede el
  uso académico previsto y añade un binario que hay que mantener. La firma tipográfica con la paleta oficial y
  el lema institucional consigue el reconocimiento sin redistribuir el activo.
- **Alternativas consideradas**:
  - Copiar `logo.svg`: reconocimiento inmediato, pero redistribución de la marca y dependencia de un archivo
    externo que puede cambiar.
  - Enlazar el logo del sitio (`<img src="https://…">`): rompe el requisito de funcionar sin conexión.
  - Sin firma: no cumple el objetivo de reconocimiento de marca.

## 5. Tipografía

- **Decisión**: pila de fuentes del sistema (`system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif`)
  con escala de cuatro niveles (28/22/16/13 px) y pesos 600/600/400/400.
- **Racional**: cero descargas, arranque inmediato y aspecto consistente en Windows, macOS y Linux; el sitio
  oficial usa una sans-serif de palo seco compatible con esta elección.
- **Alternativas consideradas**:
  - Descargar una webfont: añade peso, latencia y una licencia que no tenemos.
  - Serif: contradice el tono del sitio.

## 6. Accesibilidad y contraste

- **Decisión**: calcular el contraste con la fórmula WCAG 2.1 (`(L1+0.05)/(L2+0.05)`) en Python puro y
  exigir ≥4.5:1 en texto normal y ≥3:1 en texto grande y bordes de estado.
- **Racional**: es medible sin navegador, entra en la suite y evita discusiones subjetivas sobre «se ve bien».
- **Alternativas consideradas**:
  - Revisión visual manual: no reproducible ni automatizable.
  - Librería de accesibilidad: dependencia nueva para una fórmula de 10 líneas.

## 7. Comunicación de estados

- **Decisión**: cada estado se representa con una tupla `(token de color, icono, etiqueta)`:
  `ok/ready` verde + ✓ + «Lista», `review` ámbar + ! + «Revisar», `fallback` azul + i + «Sin evidencia»,
  `error` rojo + × + «Error», y `demo` naranja + ● + «Modo demo».
- **Racional**: la app ya distingue `ready|review|missing_evidence` y `ok|fallback|review|error`; añadir el
  canal de texto e icono cumple el requisito de no depender del color sin cambiar la semántica.
- **Alternativas consideradas**:
  - Solo color: excluye a personas con daltonismo y falla en videobeam.
  - Cambiar los estados existentes: rompería la spec 008 y sus pruebas.

## 8. Uso responsable de la marca

- **Decisión**: pie de página con «Proyecto académico · no afiliado a Grupo Manuelita», atribución de la marca
  a su titular y nota de uso de información pública.
- **Racional**: evita sugerir patrocinio o respaldo oficial, requisito FR-011/FR-012 de la especificación y
  buena práctica de la constitución (§III).
- **Alternativas consideradas**:
  - Omitir el aviso: riesgo de interpretación errónea en la sustentación y en GitHub.
  - Añadir un descargo largo: ruido visual; se resuelve en una línea.

## 9. Pruebas sin navegador

- **Decisión**: pruebas unitarias puras para tokens y contraste; `AppTest` para presencia de cabecera, badges y
  pie; verificación manual solo para lo perceptual (360 px, videobeam, color desaturado).
- **Racional**: la suite ya usa `AppTest` y no requiere servidor; mantener ese patrón conserva el tiempo de
  ejecución por debajo de 2 minutos.
- **Alternativas consideradas**:
  - Playwright o Selenium: dependencia pesada y navegador en CI.
  - Capturas comparativas: frágiles entre sistemas operativos.
