# Research: Pitch v2 con escenas sincronizadas

## R1. Proveedor y modelo

### Lo que se observó el 2026-11-26

Sondeos sin costo con la clave del integrante, enviando cuerpos inválidos:

- **MAGI-2 ya no responde por la API.**
  - Hasta la tarde, `sand/magi-2/image-to-video` generó las 6 escenas de la v1.
  - A las 21:33 UTC, el catálogo (`GET /models`) tenía 105 modelos, sin ningún `sand/magi-2/*`; por la mañana eran
    108.
  - Los tres modos responden `403 {"detail":"model_unavailable"}` antes de validar el cuerpo.
  - La página de referencia de la API sigue publicada: `https://api.higgsfield.ai/sand/magi-2/text-to-video`,
    0,08 USD/s, de 4 a 30 s, `aspect_ratio` con `9:16`, `generate_audio` y `seed`.
  - Conclusión: es una pausa o restricción del modelo, no un problema de la clave. Los demás modelos responden con
    errores de validación normales.
- **Alternativas que sí responden** (precios aproximados; Higgsfield y terceros no coinciden):

| Modelo | USD/s | Máx. | Identidad sin fijar el primer cuadro | Nota |
|---|---|---|---|---|
| Kling 4.0 | 0,13–0,19 | 1080p | sí (`elements`) | Cuadro final y referencias; hasta 30 s |
| Kling 4.0 Flash | 0,06–0,09 | 720p | sí | 3–20 s |
| Wan 3.0 | sin publicar | 1080p | sí (imágenes) | Calibrar |
| Wan 2.7 | 0,05–0,075 | 1080p | solo con video de referencia | |
| Seedance 2.5 | 0,26–0,65 | 1080p | sí | Fuera de presupuesto en 1080p |
| MiniMax H3 Lite | 0,025 | 768p | sí (exige audio) | Pierde nitidez |

**Decision**:

- **Configuración**: el modelo y los nombres de campos van por modo en `config/pitch.toml` (`[models.magi2]`,
  `[models.kling4]`). La v2 usa **un solo modelo para todos sus planos**, sin mezclar estilos.
- **Vía principal**: MAGI-2.
- **Antes de generar**, `pml pitch probe` comprueba sin costo el catálogo y cada modo.
  - Si MAGI-2 está disponible, se sigue con él.
  - Si no, el comando lo informa y la generación se detiene. El integrante decide entre esperar y cambiar a
    `kling4`, la alternativa recomendada: 1080p, identidad por `elements`, unos 10,70 USD dentro del tope.

**Decisión del integrante (2026-11-26, 22:38 UTC)**:

- **Orden de preferencia**: `[pitch].models = ["magi2", "kling4"]`.
  - `generate` sondea en ese orden y usa el primero disponible.
  - El modelo queda fijado en `escenas.json.model` al primer plano generado, para que todos los planos usen el
    mismo.
- **A esa hora**: MAGI-2 seguía en 403 y Kling 4.0 respondía con validación normal.

**Campos de Kling 4.0** (referencia de la API y sondeos con `prompt` numérico, sin cobro):

| Modo | Campos |
|---|---|
| `kling-video/v4.0/image-to-video` | `image_url` (obligatorio, primer cuadro), `prompt`, `image_urls` (cuadros intermedios, máx. 8), `end_image_url`, `duration` 3–30, `resolution` `720p`/`1080p`. Sin `aspect_ratio`: el encuadre sale de la imagen, que se envía en 1080×1920 |
| `kling-video/v4.0/reference-to-video` | `prompt` (nombra las referencias como `@image_1`), `image_urls` (máx. 10), `video_urls`, `duration`, `resolution`, `aspect_ratio` (`9:16`, `adaptive` …) |
| `kling-video/v4.0/text-to-video` | `prompt`, `duration`, `resolution`, `aspect_ratio` (`9:16`; sin `adaptive`) |

- Kling no documenta **semilla** ni **audio**. La semilla se registra, pero no se envía: la regeneración varía.
  Sin audio, el montaje usa fondo silencioso (R10).
- **Lección del sondeo**: Seedance 2.0 aceptó un cuerpo con `aspect_ratio` inválido y creó un trabajo real, que
  falló por la imagen falsa y no se cobró. Por eso `probe` solo envía `{"prompt": 1}`, que siempre es inválido.

**Rationale**: no gasta ni cambia de modelo sin decisión humana, y el resto del diseño no depende del proveedor.

**Alternatives considered**:

- Cambiar ya a Kling: cambia la premisa del curso sin necesidad si MAGI-2 vuelve.
- API directa de Sand.ai: es para organizaciones aprobadas y no permite recargas.

## R2. Modos de generación por plano

**Decision**: tres modos.

- `image`: el primer cuadro es la imagen de referencia normalizada a 1080×1920, o el **último cuadro de otro
  plano** (`source = "frame:plano-03a"`).
- `reference`: la imagen fija la identidad, pero la presentadora puede entrar al cuadro.
- `text`: sin imagen, para el trapiche.

Los campos de `reference` y `text` de MAGI-2 se confirman con una calibración de 4 s por modo (0,32 USD cada una)
cuando el modelo responda. En Kling, `reference` exige `elements`.

**Rationale**:

- Encadenar el último cuadro de 03a con 03b y con 06 mantiene a las cinco personas iguales sin pagar un modelo de
  personajes.
- El modo `reference` es lo único que permite «sale de la caña por la derecha».

**Alternatives considered**:

- Generar una imagen de grupo con un modelo de imagen: suma otro proveedor y otro costo.
- Pedir que la presentadora ya esté en cuadro: incumple la escena 01 de la spec.

## R3. Tiempos de cada palabra

**Decision**: `pml pitch align` transcribe cada `narracion/bloque-0N.wav` con faster-whisper, el modelo local del
dictado (spec 023), con `word_timestamps=True`. Luego busca cada palabra clave de los momentos sincronizados,
normalizada: sin tildes, minúsculas y por prefijo, para que «visitantes» y «visitante» coincidan.

- Guarda en `sincronia.json` los tiempos de todas las palabras y de cada momento.
- Si una palabra clave no aparece, el comando falla y dice cuál.
- El guion admite `at_s` manual como respaldo.

**Rationale**: no hay red ni dependencias nuevas. El texto ya se conoce, así que basta con encontrar la palabra.
Whisper da tiempos por palabra con unos 0,1–0,2 s de error, dentro de los ±0,5 s exigidos.

**Alternatives considered**:

- Sintetizar la narración por frases, cortadas en cada palabra clave: suena entrecortado, con 6 cortes en la
  escena 02.
- Alineación forzada con otro paquete (aeneas, MFA): es una dependencia nueva y pesada.

## R4. Duración por escena

**Decision**:

- `scene_s = narration_s + pause_s`, con `pause_s = 0.5` en `config/pitch.toml`.
- El validador exige `0.3 ≤ pause_s ≤ 0.8` y una suma de 60 s o menos.
- `pml pitch narrate` deja de usar el tope de 9,5 s por escena. Solo falla si la suma de narraciones más pausas
  pasa de 60 s, y entonces indica qué bloque recortar (FR-010, FR-011).

**Rationale**: es la regla que pidió el integrante en «Cambios generales».

## R5. Sincronizar eventos de planos generados

**Decision**:

1. En la revisión, el integrante anota en `review.anchors` el segundo del clip en que ocurre cada momento de tipo
   `plano`. Por ejemplo, «la tercera persona termina de entrar en 4,2 s».
2. El montaje reparte el tiempo del plano por tramos entre anclas. Cada tramo se reajusta con un factor de velocidad
   limitado a **0,8×–1,25×** (`setpts` por tramo).
3. Si algún tramo necesitaría un factor fuera de ese rango, el montaje falla e indica el plano y el momento.
   Entonces se regenera o se mueve el ancla.

**Rationale**: los modelos no garantizan el segundo de un evento. Un reajuste de ±25 % no se nota en planos lentos
y evita pagar un plano por evento.

**Alternatives considered**:

- Un plano por evento: de 14 a 20 planos más y movimiento cortado.
- Sin reajuste: los eventos caerían a ±2 s de su palabra.

## R6. Gráficos del montaje

**Decision**:

- **Fuente**: iconos y tarjetas de perfil como SVG propios en `video/pitch/graficos/`, con los colores y la tipografía
  de la web, sin marca Manuelita.
- **Rasterizado**: `pml pitch graphics` los pasa a PNG transparente con Playwright (Chromium, `omit_background`).
- **Montaje**: superpone cada PNG con `overlay`, aparición progresiva y una trayectoria lineal definida en el guion:
  `from` y `to` en fracciones del cuadro.
  - En la escena 02, cada icono entra al decirse su palabra y viaja hasta la tablet en 0,8 s.
  - En la escena 04, tres iconos (cita, cálculo, confirmación).
  - En la escena 05, cinco tarjetas con icono y nombre de perfil, escalonadas.
- **Iconos de perfil**: los mismos conceptos que la web (visitante, cliente B2B, proveedor, colaborador,
  planificador).

**Rationale**:

- Son gratis, exactos al cuadro y legibles (aclaración Q2).
- Playwright ya está en el proyecto.
- Los PNG se versionan por LFS, así que montar no exige Chromium.

**Alternatives considered**:

- `drawtext` y dibujos de ffmpeg: iconos pobres.
- Pillow: es dependencia transitiva, no declarada, y sin SVG.
- Remotion o HyperFrames: otra cadena de herramientas.

## R7. Publicación sin perder la v1

**Decision**:

- `pml pitch assemble` escribe por defecto en `video/pitch/borrador/`, que está ignorado.
- `pml pitch check` valida el borrador.
- `pml pitch publish` copia a `web/public/media/` el video, los subtítulos y la portada, y regenera `pitch.ts`. Solo
  corre si todos los planos están `aprobada`, el chequeo da `ok` y la sincronía cumple.
- La v1 queda en el historial de Git (LFS). Los clips de la v1 (`escenas/escena-0N.mp4`) se borran en el mismo
  commit de la publicación.

**Rationale**: cumple FR-022 y SC-008 sin tocar el código de la web.

## R8. Presupuesto

**Decision**:

- El tope sigue en `budget.max_usd = 20` (aclaración Q1).
- `_spent` suma la v1, las calibraciones y los planos de la v2.
- El precio por segundo pasa a cada modelo (`models.<id>.usd_per_second`).
- `--dry-run` desglosa por plano y muestra lo que queda.

## R9. Revisión de planos

**Decision**:

- Los cuatro chequeos de la 028 se mantienen.
- Se suma `cue_shown`: el plano muestra lo que su momento pide.
- `anchors` es obligatorio para los planos con momentos de tipo `plano`.

## R10. Sonido de fondo

**Decision**:

- Se usa el audio del clip a −18 dB, como en la v1, si existe.
- Si el modelo no genera audio (por confirmar en Kling), el montaje usa un fondo silencioso, como ya hace.

No se agrega música (spec: sin cambios en sonido).
