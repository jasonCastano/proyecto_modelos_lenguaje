# Data Model: Frontend profesional de Valer-IA (spec 031)

Datos de presentación (estáticos en `web/src/data/`); la API no cambia.

## Producto de Manuelita (`products.ts`)

| Campo | Tipo | Regla |
|---|---|---|
| `key` | `cane` \| `sugar` \| `ethanol` \| `power` \| `molasses` \| `palm` \| `grape` \| `mussel` | único |
| `name` | str | como lo nombra el sitio oficial: Caña de azúcar, Azúcar, Bioetanol, Energía renovable, Miel, Palma de aceite, Uva de mesa, Mejillones |
| `platform` | `caña` \| `palma` \| `frutas` \| `acuicultura` | negocio al que pertenece |
| `color` | token CSS | fijo en todas las áreas; nunca como color de texto si no da AA |
| `glyph` | componente de `ProductGlyphs` | propio, sin piezas de la marca (palma, uva y mejillón ya existen) |
| `photo` | `PhotoId` \| null | foto sustituta de la rejilla de negocios |

## Foto (`photos.ts` + `web/public/media/fotos/CREDITOS.md`)

| Campo | Tipo | Regla |
|---|---|---|
| `id` | str | id de Commons (`f74470253`) |
| `src` | str | WebP en `/media/fotos/`, 1600 y 800 px |
| `alt` | str | describe lo que se ve, en español |
| `author`, `license`, `sourceUrl` | str | licencia ∈ {CC0, dominio público, CC BY, CC BY-SA}; MUST existir |
| `subject` | str | qué ilustra (campo de caña, cristales de azúcar…) |
| `standIn` | `true` | siempre: no es foto de Manuelita |

Validación: una prueba de Vitest recorre `photos.ts` y falla si falta autor, licencia o URL, o si la licencia no está
en la lista; el pie muestra una línea de créditos generada desde este archivo.

## Sección de la entrada (`homeSections.ts`)

| Campo | Regla |
|---|---|
| `id` | `hero`, `producto`, `perfiles`, `negocios`, `frase`, `planificacion`, `garantias`, `evidencia`, `preguntas`, `cierre` |
| `screens` | 1 o 2 a 1440×900 |
| `heading` | h2 con un sustantivo (copy de la skill) |

## Perfil (sin cambios)

`web/src/data/profileSuggestions.ts` (spec 027) sigue siendo la fuente: nombre, para quién, qué puede preguntar,
ejemplo, glifo. Se le añade `color` (token de producto) si falta.
