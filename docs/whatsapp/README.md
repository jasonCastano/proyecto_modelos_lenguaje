# Imágenes de perfil de Valer-IA (spec 030)

Foto de perfil y portadas de Valer-IA para WhatsApp, LinkedIn y Facebook. Cada pieza está compuesta a partir de la
imagen de referencia sintética (`docs/referencias/avatar_ingenio_manuelita.png`, `real_person: false`,
`brand_elements: false`), sin cambiar los rasgos de la presentadora. Se usan la tipografía Archivo (SIL OFL
1.1), los colores corporativos inspirados en el logotipo de Manuelita (rojo anaranjado, naranja, amarillo y
verde) y un abanico propio de hojas de caña; no se usan el logotipo, su figura de pétalos ni su tipografía. No interviene ningún modelo de generación de imágenes, ni
red, ni costo.

Cada PNG tiene al lado su ficha `.md`: origen, referencia, escala, tipografías y licencias, costo 0 y quién lo
aprobó. `scripts/whatsapp_images.py check` la verifica.

## Piezas

| Archivo | Medidas | Dónde se sube | Qué la tapa |
|---|---|---|---|
| `valeria-perfil.png` | 640×640 | Foto de perfil de WhatsApp (o WhatsApp Business), LinkedIn y Facebook | La plataforma la recorta en círculo; el rostro queda en el centro |
| `valeria-linkedin.png` | 1584×396 | LinkedIn → perfil → imagen de fondo (banner personal) | La foto de perfil, abajo a la izquierda |
| `valeria-facebook.png` | 1640×624 | Facebook → página → foto de portada | La foto de perfil, abajo a la izquierda en escritorio; en teléfono se recortan los lados (el texto y el rostro quedan dentro) |
| `valeria-whatsapp-portada.png` | 1920×1080 | WhatsApp Business → Ajustes → Herramientas para la empresa → Perfil → portada | La foto de perfil, centrada abajo |

La portada **solo existe en WhatsApp Business**. En una cuenta personal de WhatsApp solo aplica la foto de perfil.
WhatsApp no publica una medida oficial; la beta reportó 1211×681 (16:9) y esta pieza tiene esa proporción.

Para una página de empresa de LinkedIn (1128×191) hay que reexportar `linkedin.html` a esa medida; queda para otra
tarea.

## Textos para acompañar las imágenes

Las imágenes no llevan la declaración de IA (decisión del integrante, 2026-11-27); por eso **estos textos son
obligatorios** al publicar cada imagen: declaran que es IA y que no es un canal oficial (constitución §10).

- **WhatsApp, «Info» (máximo 139 caracteres)**:
  > Asistente con IA de un proyecto académico sobre la caña. Respuestas con fuente. No es un canal oficial de
  > Manuelita.
- **LinkedIn, titular**:
  > Valer-IA · Agentes de IA para la agroindustria de la caña (proyecto académico)
- **LinkedIn y Facebook, descripción**:
  > Valer-IA es un asistente con IA de un proyecto académico. Responde preguntas sobre la agroindustria de la
  > caña con la fuente de cada dato y muestra la planificación industrial con datos sintéticos. No es un canal
  > oficial de Manuelita ni habla en su nombre.

## Cómo reexportar o ajustar una pieza

```bash
uv run python scripts/whatsapp_images.py render --piece linkedin   # borrador + vistas previas
# revisar docs/whatsapp/borrador/revision/ (círculo a 48/96/640 px; portadas con la foto encima)
uv run python scripts/whatsapp_images.py approve linkedin --by "Nombre Apellido"
uv run python scripts/whatsapp_images.py check
```

Las fuentes están en `fuente/`:
- `base.css`, `portada.css` y `tarjeta.css`, los estilos;
- `hojas.svg`, el abanico de hojas;
- `personaje.js`, Valer-IA en caricatura;
- `sticker.html`, que abre cada sticker con `?id=…`;
- una página por pieza.

`render` mide la escala de la referencia (máximo 1,15×, igual en ambos ejes), que el texto quede en la zona
segura, el contraste (≥ 4,5) y el peso de los stickers. `approve` no publica una pieza que falle.

## Tarjetas del bot (`tarjetas/`)

Imágenes que el bot envía en momentos fijos de la conversación (recomendaciones 1–6, 8 y 9).

| Archivo | Medidas | Cuándo se envía |
|---|---|---|
| `bienvenida.png` | 1080×1080 | Primer mensaje a un número nuevo |
| `perfiles.png` | 1080×1350 | Cuando la persona elige con quién hablar (`/perfil`) |
| `guia-rapida.png` | 1080×1350 | Respuesta a «ayuda» o «¿cómo funciona?» |
| `sin-evidencia.png` | 1080×1080 | Cuando la respuesta es `fallback` (sin evidencia) |
| `fuera-de-servicio.png` | 1080×1080 | Mantenimiento o fallo del modelo |
| `plantilla-planificacion.png` | 1080×1350 | Fondo del resultado del planificador; los recuadros quedan vacíos para las cifras del optimizador |
| `qr-repositorio.png` | 1080×1080 | Web, README y presentaciones: QR al repositorio público del proyecto |
| `estado-consejo.png` | 1080×1920 | Estado de WhatsApp: «Pide la fuente» |
| `estado-novedad.png` | 1080×1920 | Estado de WhatsApp: planificación industrial (demostración con datos sintéticos) |

Los Estados dejan libres 240 px arriba y 260 px abajo, que tapa la interfaz de WhatsApp. El QR se generó en
local con `segno` (`fuente/qr-repositorio.svg`), sin IA.

## Stickers animados (`stickers/`)

Valer-IA en caricatura (recomendación 7). Es una ilustración vectorial propia, dibujada en código en
`fuente/personaje.js`, con sus rasgos de la referencia: pelo oscuro ondulado, chaqueta verde, camisa blanca y
aretes dorados. El estilo es el de las caricaturas de los años 50 (contorno grueso, colores planos, guiño,
insignia redonda y borde blanco); no reproduce el personaje de la imagen de estilo.

| Archivo | Texto | Animación |
|---|---|---|
| `valeria-pulgar.webp` | — | Pulgar arriba que rebota, guiño y destellos |
| `valeria-bienvenido.webp` | ¡Bienvenido! | Destellos y texto que aparece |
| `valeria-gracias-confianza.webp` | ¡Gracias por confiar en nosotros! | Asiente y suben corazones |
| `valeria-consulta.webp` | ¿Cuál es tu consulta? | Inclina la cabeza; el signo de pregunta salta |
| `valeria-hola.webp` | Hola | Saluda con la mano |
| `valeria-lindo-dia.webp` | Lindo día | Sol que gira y guiño |
| `valeria-gracias.webp` | ¡Gracias! | Asiente con ojos felices y corazones |
| `valeria-pensando.webp` | Pensando | Mano en el mentón y burbuja de pensamiento que aparece |
| `valeria-listo.webp` | ¡Listo! | Pulgar arriba y marca de verificación que se dibuja |

- Cumplen el formato de WhatsApp:
  - WebP animado de 512×512, fondo transparente, ciclo de 2 s a 12 cuadros por segundo, ≤ 500 KB;
  - `icono-paquete.png`, de 96×96 y ≤ 50 KB, es el ícono del paquete.
- **Cómo usarlos**: WhatsApp no carga paquetes desde un archivo suelto.
  - En el teléfono, con una app de paquetes de stickers: se crea un paquete con los 9 `.webp` y el ícono, y
    se añade a WhatsApp.
  - En WhatsApp Web, como sticker personalizado: se sube cada `.webp`.
  - El bot los envía como mensaje de tipo sticker (specs 034 y 037). El plugin `valeria-bridge` busca la
    los envía por el adaptador de salida del canal (como las notas de voz). El parche
    `openclaw/patches/whatsapp-sticker.mjs` (ADR 0040) hace que el componente los envíe como sticker nativo y
    no como documento; sin él no llega ningún sticker. Lo aplica `scripts/openclaw_env.ps1 -Install`. En el log del gateway
    queda una línea por sticker («sticker enviado (…) vía …» o «sticker no enviado (…): motivo»), y al
    arrancar, «stickers listos vía …» o «sin vía de stickers (…)». `uv run pml ops check` muestra
    `stickers-hoy` (elegidos, entregados y fallidos del día) y se pone en rojo si se eligen y no llega
    ninguno.

## Audios de los stickers (`stickers/audios/`)

La frase de cada sticker dicha por Valer-IA, con la misma voz del chat de la web (spec 016, voz «Rebeca»). El
pulgar no tiene frase, así que no tiene audio.

| Archivo | Frase | Sticker | Duración |
|---|---|---|---|
| `valeria-bienvenido.ogg` | ¡Bienvenido! | `valeria-bienvenido.webp` | 0,97 s |
| `valeria-gracias-confianza.ogg` | ¡Gracias por confiar en nosotros! | `valeria-gracias-confianza.webp` | 1,63 s |
| `valeria-consulta.ogg` | ¿Cuál es tu consulta? | `valeria-consulta.webp` | 1,22 s |
| `valeria-hola.ogg` | Hola | `valeria-hola.webp` | 0,62 s |
| `valeria-lindo-dia.ogg` | Lindo día | `valeria-lindo-dia.webp` | 0,88 s |
| `valeria-gracias.ogg` | ¡Gracias! | `valeria-gracias.webp` | 0,91 s |
| `valeria-pensando.ogg` | Estoy pensando | `valeria-pensando.webp` | 1,04 s |
| `valeria-listo.ogg` | ¡Listo! | `valeria-listo.webp` | 0,75 s |

- **Formato**: OGG/Opus, mono, 48 kHz, ≤ 5 s, con el volumen igualado entre los ocho. Es el formato de las notas de
  voz de WhatsApp.
- **Cómo usarlos**:
  - Como nota de voz: se envía el sticker y después su audio.
  - Como sticker con sonido: se une el audio a la animación en un video corto y se convierte con «Crear» en
    WhatsApp, donde la función esté disponible. Eso queda fuera de esta feature.
- **Producirlos de nuevo**: `HF_HUB_OFFLINE=1 uv run python scripts/whatsapp_images.py render --piece audios`, luego
  escucharlos en `borrador/audios/` y publicar con `approve audio-<nombre> --by "…"`. Necesita el modelo de voz de
  la spec 016 en la caché.
- **Atribución y licencia**: voz sintetizada con Phonon (Gradium, `gradium/phonon-40m-es`). El modelo y las voces
  son **CC BY-NC 4.0**: solo uso académico, no comercial. Cada audio lleva su ficha con la licencia y la
  atribución.

### Uso por el bot (spec 034)

Valer-IA envía estos stickers en WhatsApp como mensajes de tipo sticker, con moderación. El mapeo vive en
`config/stickers.toml`. Los archivos de esta carpeta no cambian.

| Sticker | Cuándo lo usa el bot |
|---|---|
| `valeria-bienvenido` | Saludo de una persona que escribe por primera vez (antes del texto) |
| `valeria-hola` | Saludo al iniciar una conversación nueva (antes del texto) |
| `valeria-consulta` | Saludo a mitad de conversación, sin pregunta |
| `valeria-gracias` | La persona agradece |
| `valeria-lindo-dia` | La persona se despide |
| `valeria-pulgar` | La persona asiente («ok», «dale»); el único que se usa en inglés |
| `valeria-gracias-confianza` | La persona aprueba que se recuerden sus datos |
| `valeria-listo` | Se completó una acción pedida o se entregó un plan |
| `valeria-pensando` | La respuesta tarda más de 8 s (lo envía el plugin) |

Moderación:

- uno por respuesta y nunca dos respuestas seguidas, salvo la despedida;
- máximo 4 por conversación, sin repetir, salvo el pulgar;
- ninguno ante quejas, molestia, datos personales, errores, avisos o respuestas factuales.

## Reglas comunes

- La misma presentadora y la misma paleta.
- Sin la marca de Manuelita.
- Texto exacto compuesto en el diseño.
- Sin cifras dibujadas: las pone el optimizador.
- Ficha de origen y aprobación humana para cada pieza y cada audio.
