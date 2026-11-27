# Research: Imágenes de perfil y banner de Valer-IA (spec 030)

Fecha: 2026-11-27. Todas las decisiones respetan FR-010 (sin costo, solo skills de Claude ya instaladas, sin modelos
ni servicios de generación de imágenes).

## R1. Herramienta de producción

- **Decisión**: cada pieza es una página HTML/CSS a la medida exacta de la plataforma, diseñada con la skill
  `design` (flujos «banner design» y «social photos») y la guía de `frontend-design`, y exportada a PNG con
  Playwright (Chromium local, `device_scale_factor` 1, tamaño exacto).
- **Por qué**: es el único camino de las skills instaladas que no pide clave ni cuenta; el texto es exacto y
  editable (FR-005); Playwright ya está en el grupo dev del proyecto y se usa para los gráficos del pitch (spec 029)
  y las capturas de Archify.
- **Descartadas**:
  - `ai-image-generation`: todos sus modelos pasan por RunComfy, que cobra por imagen (decisión del integrante).
  - `imagegen`: su herramienta integrada solo existe en Codex; en Claude Code pide `OPENAI_API_KEY` (de pago).
  - `design` → logos e íconos con Gemini: piden `GEMINI_API_KEY`.
  - `media-use`: HeyGen exige cuenta; FLUX local vía mflux solo corre en Mac.
  - Modelo de pesos abiertos local en la GPU: lo descartó el integrante al pedir las skills de Claude.

## R2. Medidas por plataforma

Ninguna plataforma publica una especificación estable y las guías difieren; se eligen los valores más citados y se
diseña con zonas seguras amplias. Fuentes consultadas el 2026-11-27: guías de Buffer, Snappa, SocialRails,
socialsizes.io y Moda (Facebook); Moda, Ayrshare e Instasize (WhatsApp); referencia `banner-sizes-and-styles.md` de
la skill `design` (LinkedIn y Facebook); WABetaInfo e iMore (portada de WhatsApp Business).

| Pieza | Exporta | Se muestra | Zona segura del texto | Lo que la tapa |
|---|---|---|---|---|
| Foto de perfil | 640×640 | círculo, de 40 a 640 px | círculo inscrito; rostro en el 80 % central | — |
| LinkedIn (banner personal) | 1584×396 | 4:1 | tercio derecho y centro, alto 60–340 px | foto de perfil abajo a la izquierda (≈ 0–568 × 200–396 en escritorio) |
| Facebook (portada de página) | 1640×624 | 820×312 escritorio; 640×360 teléfono (recorta lados) | centro de 1280×560 | foto de perfil abajo a la izquierda en escritorio |
| WhatsApp Business (portada) | 1920×1080 | 16:9 (la beta reportó 1211×681) | centro de 1600×760 | foto de perfil centrada abajo, superpuesta |

- **Decisión**: LinkedIn usa el banner personal (1584×396), el formato que se ve en la mayoría de perfiles. Si el
  integrante crea una página de empresa (1128×191), el mismo diseño se reexporta a esa medida en una tarea aparte.
- **WhatsApp**: la portada solo existe en WhatsApp Business. 1211×681 sale de la beta y no es oficial; se exporta
  1920×1080 (16:9), que la app reduce sin recortar el centro. Con la cuenta personal solo aplica la foto de perfil.

## R3. Encuadre a partir de la referencia, sin ampliar

- Referencia: 941×1672 px, RGB, sin canal alfa. La zona de cabeza y hombros mide unos 600×600 px nativos.
- **Decisión**:
  - Foto de perfil a 640×640: recorte de cabeza y hombros escalado como máximo ×1,1 (casi nativo); el rostro queda en
    el centro del círculo, con margen para el pelo.
  - Banners: la presentadora ocupa un panel lateral recortado de cintura para arriba. En LinkedIn (alto 396) y
    Facebook (alto 624) se reduce; en WhatsApp (alto 1080) se usa a ≤ 1,0× de su altura nativa útil.
  - Nunca se estira en un solo eje; el script de verificación rechaza un factor de escala > 1,15 (R7).
- **Por qué**: FR-003 (sin alterar rasgos) y el caso borde de resolución; ampliar más de ~15 % ablanda el rostro.

## R4. Fondo de la foto de perfil

- **Decisión**: se conserva el fondo original de la referencia (campo de caña y luz cálida) y se armoniza con la
  paleta de Valer-IA mediante un degradado suave de verde caña en los bordes y un anillo de color dentro del círculo.
  No se recorta a la persona.
- **Por qué**: recortar el pelo suelto requiere un modelo de segmentación y deja bordes artificiales; el fondo
  original ya es verde y cálido, coherente con la paleta, y es el mismo del video (SC-002). FR-003 se ajusta para
  decir «fondo de la referencia armonizado con la paleta».
- **Descartada**: recorte con `rembg` u otro modelo de segmentación (no generativo, pero añade un modelo y una
  descarga, y FR-010 pide no depender de modelos).

## R5. Texto de los banners

- Tipografía: **Archivo** variable (SIL OFL 1.1), la misma de la plataforma web, cargada desde
  `web/node_modules/@fontsource-variable/archivo` (sin red). El ancho marca el rol, como en la web.
- Copia propuesta (el integrante la aprueba en la revisión):
  - Nombre: «Valer-IA».
  - Lema: «Agentes de IA para la agroindustria de la caña: respuestas con fuente y planificación industrial».
- La declaración de IA no va en las imágenes (decisión del integrante, 2026-11-27, tras ver las portadas): va en
  el campo «Info» de WhatsApp y en la descripción de LinkedIn y Facebook (textos en `docs/whatsapp/README.md`;
  los pega el integrante). La ficha de cada portada lo registra en `disclosure_in`.

## R6. Paleta y formas

- **Actualización (2026-11-27, pedido del integrante)**: inspiración en el logotipo de Manuelita
  (imagen aportada por el integrante; no se versiona, por ser marca de un tercero). Se toman sus **colores** (rojo anaranjado `#d64729`,
  naranja `#f39200`, amarillo `#ffd100`, verde `#497536`) y la idea de **formas orgánicas solapadas**: un abanico
  de hojas de caña (`fuente/hojas.svg`) que brotan de un mismo punto, en lugar de la fila de glifos. NO se copian
  la figura circular de pétalos ni la tipografía del logotipo: la constitución (§3.7 y §10) prohíbe la marca y
  las portadas parecerían cuentas oficiales de Manuelita. Las portadas pasan a fondo claro (`--field`) con el
  nombre en el verde corporativo (contraste 5,0) y un filete rojo anaranjado; el anillo de la foto de perfil
  toma los cuatro colores. La tipografía sigue siendo Archivo.
- Versión anterior (reemplazada):

- Tokens de `web/src` (spec 026): caña `#387c2b`, caña profunda `#173512`, azúcar `#ffd200`, melaza `#f6a01a`,
  etanol `#e86d1f`, energía `#b0bc22`, tinta `#14240f`, campo `#f5f7f3`.
- Pictogramas: los propios de la plataforma (glifos de producto de la spec 027), copiados como SVG; sin logotipo ni
  piezas de la marca de Manuelita (FR-006).
- Contraste AA para todo texto sobre su fondo, medido por el script (R7).

## R7. Revisión, aprobación y verificación

- **Decisión**: un script fuera de línea, `scripts/whatsapp_images.py`, con tres órdenes (contrato en
  `contracts/whatsapp-images-cli.md`):
  - `render`: exporta cada pieza a `docs/whatsapp/borrador/` (ignorado por Git) junto con vistas previas de
    revisión: la foto en círculo a 48, 96 y 640 px, y cada portada con la foto de perfil superpuesta donde la pone la
    plataforma, en escritorio y teléfono.
  - `approve <pieza> --by "<nombre>"`: copia la pieza aprobada a `docs/whatsapp/` y escribe su ficha.
  - `check`: valida medidas, fichas, hashes, licencias, costo 0, escala ≤ 1,15 y contraste AA.
- **Por qué**: igual que el pitch (borrador → revisión humana → publicación), cumple FR-009 y deja trazabilidad
  (FR-008) sin tocar la app.
- **Pruebas**: `tests/unit/test_whatsapp_images.py` cubre `check` y la escritura de fichas con imágenes sintéticas
  creadas por Pillow; no abre navegador, así que corre en el CI sin Playwright.

## R8. Versionado

- PNG y WebP aprobados por Git LFS (`docs/whatsapp/**/*.png` y `**/*.webp`, también en `tarjetas/` y `stickers/`).
- Fuentes HTML/CSS/SVG de las piezas como texto en `docs/whatsapp/fuente/`.
- `docs/whatsapp/borrador/` en `.gitignore`.

## R10. Stickers animados

- **Estilo**: la imagen de estilo aportada (`docs/referencias/thumbs_up_fallout.jpg`, no versionada) es un
  personaje de una franquicia de videojuegos. Se toma su **estilo** de caricatura de los años 50 (contorno
  negro grueso, colores planos, guiño, insignia roja redonda, borde blanco troquelado), no el personaje: la
  figura es Valer-IA con sus rasgos de la referencia (pelo oscuro ondulado con raya, chaqueta verde, camisa
  blanca, aretes dorados) y los colores corporativos.
- **Producción**: ilustración vectorial dibujada en código (`fuente/personaje.js`: insignia, poses de pulgar,
  saludo y pensando, ojos abiertos, guiño, felices o hacia arriba, y extras animables). La animación es CSS
  de 2 s en bucle; el script fija el tiempo con la Web Animations API, captura 24 cuadros (12 por segundo)
  con fondo transparente y arma un WebP animado con Pillow, bajando la calidad hasta caber en 500 KB.
- **Formato de WhatsApp**: 512×512, WebP, animado ≤ 500 KB, ícono del paquete 96×96 PNG ≤ 50 KB, de 3 a
  30 stickers por paquete. Para usarlos en un chat se cargan con una app de paquetes de stickers o como
  sticker personalizado en WhatsApp Web; el proyecto no publica paquetes.
- **Rendimiento**: `method=6` del codificador WebP tardaba ~5 s por cuadro; `method=4` da casi el mismo peso
  en ~1 s por sticker.

## R11. Tarjetas del bot y QR

- Mismo sistema que las portadas (fondo claro, verde corporativo, filete rojo anaranjado, hojas, Archivo).
  Bienvenida y novedad usan la fotografía en círculo; sin evidencia, fuera de servicio y consejo usan la
  caricatura. Medidas: 1080×1080 (cuadradas), 1080×1350 (verticales) y 1080×1920 (Estados, con 240 px arriba
  y 260 px abajo libres para la interfaz de WhatsApp).
- La tarjeta de bienvenida dice «Soy una asistente con IA de un proyecto académico» (lo pide la
  recomendación 1); no repite la frase de las portadas que el integrante retiró.
- **QR**: apunta a `https://github.com/jasonCastano/proyecto_modelos_lenguaje` (decisión del integrante). No
  hay biblioteca de QR en el entorno ni un decodificador para verificar uno escrito a mano; la instalación
  de `segno` con `uvx` necesita la autorización del integrante. Hasta entonces la tarjeta QR queda pendiente
  (su fuente HTML espera `fuente/qr-repositorio.svg`).

## R9. Constitución

- Las imágenes de una persona sintética salen por primera vez de la web a perfiles de redes. Se añade a §10 una
  regla de «imágenes de perfil de Valer-IA»: solo composiciones de la imagen de referencia con ficha, sin modelos
  generativos, sin marca de Manuelita, con la declaración de IA en el texto del perfil y aprobación humana.
- Enmienda **MINOR 2.5.0** con ADR 0034; requiere la aprobación de ambos integrantes.
- La rama parte de `029-pitch-escenas-sincronizadas` (constitución 2.4.0) para no chocar con la numeración; depende
  de los PR #84 y #85.

## R12. Audios de los stickers (US6)

- **Voz**: `VoiceService` de la spec 016 con la configuración del agente (`config/voice.toml`): Phonon
  `gradium/phonon-40m-es` `q8_0`, voz «Rebeca» (femenina, español de México, id `Sx8m6WdXBG06zwZT`), salida a
  24 kHz. Se usa la voz oficial del agente para que el sticker suene igual que el chat de la web (SC-008).
- **Prueba (2026-11-27, en el equipo del integrante, sin red)**:
  - «¡Gracias por confiar en nosotros!»: 2,32 s, pico 0,58, 8,5 KB en Opus.
  - «¿Cuál es tu consulta?»: 1,92 s, pico 0,64, 6,3 KB.
  - «Hola»: 1,20 s, pico 0,45, 3,6 KB.

  La frase más larga queda muy por debajo de 5 s. Los picos desiguales confirman que hace falta igualar el
  volumen (FR-019).
- **Red**: el modelo ya está en la caché de Hugging Face, pero el cargador intenta consultar el Hub y falla sin red.
  Con `HF_HUB_OFFLINE=1` carga desde la caché. Esto cumple FR-012 (nada sale del equipo).
- **Acabado**:
  1. Se recorta el silencio de los extremos: umbral de −45 dBFS en ventanas de 10 ms, con 30 ms de margen para no
     comerse consonantes finales.
  2. Se añaden 150 ms de silencio al inicio y al final.
  3. Se normaliza a un RMS objetivo de −20 dBFS, con el pico limitado a −1 dBFS.
  4. Si la duración final pasa de 5 s, se vuelve a sintetizar con la frase tal cual. Si persiste, el audio no se
     aprueba: nunca se recorta la voz.
- **Formato**: OGG/Opus mono, 48 kHz, 32 kbit/s. Es el formato de las notas de voz de WhatsApp: se reproduce
  sin convertirlo y sirve igual para unirlo después al sticker en un video. Se codifica con PyAV (`av` 19 con
  `libopus`), que ya es dependencia de runtime (spec 023), en vez de llamar a `ffmpeg`, que solo está en el equipo
  del integrante y no en el CI.
- **Texto**: el texto exacto de la spec. Si la entonación o la pronunciación fallan, el catálogo admite un
  `speech_text` distinto (otra puntuación o una grafía fonética); la ficha registra los dos.
- **Alternativas descartadas**:
  - MP3 o M4A: WhatsApp los muestra como archivo de audio, no como nota de voz.
  - WAV: pesa unas 20 veces más.
  - Llamar a `ffmpeg` por `subprocess`: no está en el CI.
  - Otra voz del catálogo: rompería la identidad con el chat web.

## R13. Constitución (US6)

- La regla de §10 sobre imágenes de perfil prohíbe los modelos generativos **para imágenes**. Los audios usan un
  modelo de síntesis de voz, que ya está aprobado en §2 (spec 016, ADR 0020), pero hasta ahora solo para leer las
  respuestas del chat. Sacar esa voz a material de difusión es un uso nuevo.
- Se amplía la regla de §10 con los audios de los stickers:
  - solo la voz oficial del agente, sintetizada en local y sin costo;
  - sin clonar ni imitar voces reales;
  - con la licencia CC BY-NC 4.0 y la atribución en la ficha y en el README;
  - uso solo académico y no comercial;
  - con la aprobación de un integrante por cada audio.
- Enmienda **MINOR 2.7.0** (la 2.6.0 es de la spec 031) con **ADR 0036**; requiere la aprobación de ambos
  integrantes.
- **Rama**: la 030 ya se fusionó (PR #86). US6 va en la rama nueva `030-audios-stickers`, que parte de
  `031-frontend-profesional-valeria` (PR #87 abierto, constitución 2.6.0) para que la enmienda 2.7.0 no choque;
  su PR depende del #87, como la 030 dependió de la 029.
