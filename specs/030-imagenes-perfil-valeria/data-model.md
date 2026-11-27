# Data Model: Imágenes de perfil y banner de Valer-IA (spec 030)

## Imagen de referencia

| Campo | Valor | Regla |
|---|---|---|
| `path` | `docs/referencias/avatar_ingenio_manuelita.png` | MUST existir y no ser un puntero LFS |
| `sha256` | `dac47b3f…7e7e` | MUST coincidir con la ficha `avatar_ingenio_manuelita.md` |
| `real_person` / `brand_elements` | `false` / `false` | MUST ser `false` en la ficha; si no, `render` no corre |

## Pieza (catálogo fijo en el script)

| `id` | Archivo | Medidas | Fuente HTML | Superposición de revisión |
|---|---|---|---|---|
| `perfil` | `valeria-perfil.png` | 640×640 | `fuente/perfil.html` | círculo a 48, 96 y 640 px |
| `linkedin` | `valeria-linkedin.png` | 1584×396 | `fuente/linkedin.html` | foto abajo a la izquierda; escritorio y teléfono |
| `facebook` | `valeria-facebook.png` | 1640×624 | `fuente/facebook.html` | foto abajo a la izquierda; recorte 640×360 de teléfono |
| `whatsapp` | `valeria-whatsapp-portada.png` | 1920×1080 | `fuente/whatsapp.html` | foto centrada abajo |

Cada pieza declara además su **zona segura** (rectángulo en px) y su **escala máxima** de la referencia (≤ 1,15).

Estados: `borrador` (en `docs/whatsapp/borrador/`, sin ficha) → `aprobada` (en `docs/whatsapp/`, con ficha). Una
pieza rechazada se queda en borrador y se vuelve a exportar; no se versiona (FR-009). Volver a aprobar una pieza
reemplaza el PNG y su ficha.

## Ficha de la pieza (`docs/whatsapp/<archivo>.md`)

Encabezado YAML, en el estilo de la ficha de la referencia:

| Campo | Tipo | Regla |
|---|---|---|
| `file` | str | nombre del PNG junto a la ficha |
| `sha256` | str | MUST coincidir con el PNG |
| `width`, `height` | int | MUST coincidir con el catálogo y con el PNG |
| `source` | str | ruta de la fuente HTML |
| `reference` | str + `reference_sha256` | MUST coincidir con la imagen de referencia |
| `tools` | lista | `design` (skill), `frontend-design` (skill), Playwright/Chromium |
| `fonts` | lista de `{name, license}` | licencia MUST ser libre (p. ej. `OFL-1.1`) |
| `generative_model` | `none` | MUST ser `none` (FR-010) |
| `cost_usd` | `0` | MUST ser 0 (SC-005) |
| `disclosure_in` | str | MUST existir en las portadas: dónde va la declaración de IA (texto del perfil) |
| `approved_by`, `approved_at` | str, fecha ISO | MUST estar presentes |

El cuerpo describe en una o dos frases el encuadre y dónde se usa la pieza.

## Índice (`docs/whatsapp/README.md`)

Tabla de piezas con medidas y dónde subir cada una, el texto sugerido para «Info» de WhatsApp y para la descripción
de LinkedIn y Facebook (con la declaración de IA), y la lista de imágenes recomendadas para el bot (spec, sección de
recomendaciones).
