# ADR 0034 — Imágenes de perfil de Valer-IA compuestas, sin modelos generativos

- **Estado**: propuesta (requiere la aprobación de ambos integrantes, constitución §11)
- **Fecha**: 2026-11-27
- **Autor**: Roberto José Guerrero
- **Relacionadas**:
  - ADR 0032 y 0033 (video pitch), que introdujeron la imagen de referencia sintética y su ficha;
  - spec 024 (Valer-IA en WhatsApp con OpenClaw);
  - `specs/030-imagenes-perfil-valeria/` (spec, plan, research, contrato, tareas).

## Contexto

Valer-IA atiende por la web y por WhatsApp, pero sus perfiles en WhatsApp, LinkedIn y Facebook no tienen identidad
visual. El integrante pidió una foto de perfil y portadas a partir de la imagen de referencia del pitch, que es
sintética y tiene ficha de origen.

El primer pedido nombraba la skill `ai-image-generation`. Todos sus modelos pasan por RunComfy, que cobra por
imagen, y el integrante pidió después que la producción no tuviera costo y usara las skills de Claude ya
instaladas.

Es la primera vez que la imagen de la presentadora sintética sale de la web hacia perfiles en redes.

## Decisión

1. **Composición, no generación**: cada pieza es una página HTML/CSS a la medida exacta de la plataforma, hecha con
   las skills `design` y `frontend-design`, y exportada a PNG con Chromium local (`scripts/whatsapp_images.py`).
   La presentadora aparece tal como está en la referencia: un solo factor de escala, a lo sumo 1,15×, igual en
   ambos ejes; sin retoques y con su fondo original armonizado con la paleta.
2. **Texto exacto; declaración en el perfil**: las portadas dicen «Valer-IA» y el lema. La declaración de IA
   («Asistente con IA de un proyecto académico. No es un canal oficial de Manuelita.») no va en la imagen, por
   decisión del integrante tras ver las portadas: va en el texto del perfil de cada red («Info» de WhatsApp,
   descripción de LinkedIn y Facebook), y la ficha lo registra en `disclosure_in`. El script mide que el texto
   quede en la zona segura de cada plataforma y tenga contraste AA.
3. **Revisión y trazabilidad**: `render` deja borradores (ignorados por Git) y vistas previas; solo `approve`, con el
   nombre de quien aprueba, publica la pieza en `docs/whatsapp/` con su ficha (referencia, escala, tipografías y
   licencias, `generative_model: none`, `cost_usd: 0`). `check` lo verifica y tiene pruebas sin navegador.
4. **Inspiración en el logotipo de Manuelita, sin copiarlo** (pedido del integrante): las piezas usan sus colores
   corporativos y formas orgánicas solapadas propias (un abanico de hojas de caña), no la figura circular de
   pétalos ni la tipografía del logotipo. Copiarlos violaría §3.7 y §10 y haría pasar los perfiles por cuentas
   oficiales de Manuelita.
5. **Tarjetas del bot y stickers** (ampliación del 2026-11-27): las tarjetas siguen el mismo sistema. Los
   stickers son **una ilustración vectorial propia de Valer-IA dibujada en código** (`fuente/personaje.js`),
   animada con CSS y exportada a WebP animado de 512×512 (≤ 500 KB). Toman el estilo de caricatura de los
   años 50 de la imagen de estilo aportada por el integrante, no su personaje (que pertenece a una franquicia
   de videojuegos). Es la única pieza que no reproduce la referencia tal cual: la caricatura la interpreta.
6. **Gobierno**: la constitución 2.5.0 añade a §10 la regla de las imágenes de perfil.

## Alternativas descartadas

- **`ai-image-generation` (RunComfy)**: de pago; descartada por el integrante.
- **`imagegen`**: su herramienta integrada solo existe en Codex; en Claude Code pide `OPENAI_API_KEY` (de pago).
- **`design` → logos e íconos con Gemini** y **`media-use` → HeyGen**: piden claves o cuentas.
- **Modelo de pesos abiertos en la GPU local**: gratuito, pero el integrante pidió las skills de Claude; además,
  un modelo generativo podría alterar el rostro.
- **Recortar a la presentadora con un modelo de segmentación** para ponerla sobre un fondo nuevo: añade un modelo
  y deja bordes artificiales en el pelo suelto.

## Consecuencias

- Costo 0 y nada sale del equipo; las piezas se pueden reexportar o ajustar editando su HTML.
- El rostro es idéntico al del video.
- No hay estilo ilustrado ni poses nuevas: piezas como stickers con expresiones distintas necesitarían otra
  imagen de referencia o un modelo generativo, con su propia decisión.
- Las medidas de WhatsApp Business no son oficiales (16:9, según la beta); si la app cambia, se reexporta.
- Subir las imágenes a cada red lo hace el integrante, con los textos de `docs/whatsapp/README.md`.
