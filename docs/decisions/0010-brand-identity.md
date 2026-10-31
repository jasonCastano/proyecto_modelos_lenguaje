# ADR 0010 — Identidad visual Manuelita en la app del Módulo 1

- **Fecha**: 2026-10-30
- **Estado**: Aceptada
- **Contexto**: spec `009-manuelita-visual-identity`. La app de la spec 008 funciona pero no comunica de
  qué organización trata ni se reconoce como trabajo sobre Manuelita.

## Contexto

Se pidió adaptar la interfaz de la app Streamlit con una identidad visual inspirada en
https://www.manuelita.com/. La app es de uso académico, local y sin conexión; la constitución exige
trazabilidad, accesibilidad y no exponer secretos ni rutas absolutas, y una prueba existente prohíbe
`unsafe_allow_html` en `app.py`.

## Decisión

1. **Paleta oficial, no inventada**: se toman los `fill` del logotipo público
   (`logo.svg`): verde bosque `#387C2B`, naranja `#E86D1F`, lima `#B0BC22`, amarillo `#FFD200`,
   naranja claro `#F6A01A` y blanco. Los colores de texto y superficie son derivados con contraste
   verificado.
2. **Tema nativo + hoja de estilos propia**: `.streamlit/config.toml` define el tema base (inputs, tabs,
   expanders) y `brand.py` inyecta un CSS estático con `st.html`, sin `unsafe_allow_html`.
3. **Firma tipográfica en lugar del logotipo raster**: no se copia el SVG de la marca al repositorio
   (marca registrada, binario innecesario, requisito offline). La cabecera usa el nombre, el lema y la
   paleta.
4. **Tipografía del sistema**: `system-ui` con escala 28/22/16/13 px; cero descargas.
5. **Contraste medido, no estimado**: fórmula WCAG 2.1 en Python y diez pares declarados con umbral
   4.5:1 / 3:1, verificados en la suite. El color de advertencia se ajustó de `#B26A00` (4.24:1) a
   `#A05F00` (5.08:1) precisamente por esta prueba.
6. **Estados nunca solo con color**: cada estado tiene icono y etiqueta (`✓ Correcta`, `! Revisar`,
   `i Sin evidencia`, `× Error`, `● Modo demo`).
7. **Uso responsable de la marca**: pie con atribución a los titulares y aviso de proyecto académico no
   afiliado.

## Consecuencias

- **Positivas**: identidad reconocible sin recursos externos; accesibilidad verificable en CI; cero
  dependencias nuevas; el código de producto no cambia.
- **Negativas**: el CSS depende de selectores del DOM de Streamlit (`data-testid`), que pueden cambiar
  entre versiones; se limitan a tipografía, enlaces, sidebar y métricas.
- **Riesgo aceptado**: no se usa el logotipo oficial, por lo que el reconocimiento depende del nombre,
  la paleta y el lema.

## Alternativas consideradas

| Alternativa | Por qué no |
|-------------|------------|
| `st.markdown(..., unsafe_allow_html=True)` | Rompe una prueba de seguridad existente y abre HTML no confiable. |
| Copiar `logo.svg` al repositorio | Redistribuye una marca registrada y añade un binario que no se actualiza solo. |
| Enlazar el logo desde el sitio oficial | Incumple el requisito de funcionar sin conexión. |
| Framework de UI (Tailwind, Bootstrap) | Dependencia nueva desproporcionada para una pantalla. |
| Colores «parecidos» elegidos a ojo | No reproducibles ni verificables contra la fuente. |

## Evidencia

- `src/proyecto_modelos_lenguaje/brand.py`, `.streamlit/config.toml`, `app.py`.
- `tests/unit/test_brand.py` (contraste, tokens, fragmentos), `tests/contract/test_brand_contract.py`
  (esquema), `tests/integration/test_app_brand.py` (`AppTest`).
- `specs/009-manuelita-visual-identity/quickstart.md` para la verificación manual.
