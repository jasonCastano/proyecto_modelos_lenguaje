# Research: Frontend profesional de Valer-IA (spec 031)

Fecha: 2026-11-27. Skill de diseño: `design-taste-frontend` (tasteskill 2.5), pedida por el integrante. Donde la
skill choca con la constitución, manda la constitución y se anota aquí.

## R1. Tipo de sitio y reparto de la skill

- **Decisión**: tipo **software** (`data-type="software"`, `site-kind="software"`): Valer-IA es una plataforma de
  agentes de IA. La categoría y el comprador del h1: «plataforma de agentes de IA» para quien consulta a Manuelita
  (visitantes, clientes, proveedores, colaboradores, planta).
- **Reparto obtenido** (`deal.mjs`, `moments.mjs`, listas de la skill, 2026-11-27):
  - hero **split**: texto a la izquierda (notice line, h1 de 3 líneas, lead, dos botones) y un visual de 628×716 a
    la derecha con una tarjeta flotante con un dato vivo. El visual es **el video pitch** (cumple «primer
    elemento» de la constitución §3.7: el video es el visual del hero);
  - nav `nav-centre`, footer `footer-statement`, cierre `close-type`, ritmo `dark-band`, botones `solid`, marca
    `wordmark` («Valer-IA» en Archivo ancho);
  - momentos: **letters-assemble** (una frase de 2 a 5 palabras que se arma al entrar en pantalla) en una sección
    propia; `iris-opens` se descarta para no sumar movimiento (la skill permite uno en página corta; FR-010).
  - Un segundo `deal.mjs` de prueba registró `triptych` en el historial; se usa el primero (`split`).
- **Por qué**: la skill pide para software «la UI real en grande» (un `app-frame`), tarjetas de función, diagramas
  con pulsos y fotos de personas o del producto; aquí las fotos muestran los negocios y cultivos sobre los que
  Valer-IA responde.

## R2. El kit de la skill no se copia al repositorio

- El kit (`assets/system.css`, `system.js`, motion, layout) **no declara licencia**. El repositorio es público y MIT,
  y la constitución exige citar fuente y licencia de todo fragmento externo.
- **Decisión**: no se copian archivos del kit. Se **reimplementan** en el CSS y los componentes del proyecto las
  reglas y medidas de sus referencias (alturas por pantalla, rejilla, bordes iguales, capa de hover y foco,
  entrada del hero, momento). Los scripts de la skill (`gate.mjs`, `copy-lint.mjs`, `consistency.mjs`, `photos.mjs`,
  `shoot.mjs`, `perf.mjs`) se usan como **herramientas externas** desde la carpeta de la skill, sin versionarlos.
- El estado de la skill (`.taste-skill/`) va a `.gitignore`.

## R3. Paleta

- `start.mjs brand` con los colores del cliente (logotipo medido en la spec 030):

  | Token | Valor | Uso |
  |---|---|---|
  | `--p-bg` | `#f5f7f3` | fondo (blanco verdoso de hoja, el de la plataforma) |
  | `--p-surface` | `#ffffff` | tarjetas y paneles |
  | `--p-ink` | `#14240f` | texto |
  | `--p-muted` | `#4b5747` | texto secundario (AA sobre fondo y superficie) |
  | `--p-accent` / `--p-action` | `#497536` | verde corporativo: acciones primarias (texto `#f5f7f3`) |
  | `--p-inv-bg` | `#14240f` | banda oscura (`dark-band`) y pie |
  | `--leaf-red` | `#d64729` | rojo anaranjado: filetes, alertas suaves, hojas |
  | `--leaf-orange` / `--leaf-yellow` | `#f39200` / `#ffd100` | hojas y relleno de producto, nunca texto |

- Los colores de producto de la spec 026 (`--cane`, `--sugar`, `--ethanol`, `--power`, `--molasses`) se conservan
  con su significado fijo; se añaden palma, uva y mejillón (data-model).
- Sin violeta ni lavanda (regla de la skill).

## R4. Tipografía

- La skill repartiría «Mona Sans + Geist Mono» desde Google Fonts. **Se mantiene Archivo variable** (constitución
  §3.7: una sola familia; el ancho marca el rol), servida localmente por fontsource, que además usan las imágenes
  de la spec 030. Archivo tiene eje de ancho como Mona Sans, así que la intención del reparto se conserva:
  titulares a `wdth` 112–125, texto a 100, cifras condensadas con números tabulares. La monoespaciada de la traza
  es la del sistema (`ui-monospace`); no se añade otra fuente.

## R5. Fotografías

- **Fuente**: búsqueda en vivo de la skill (`photos.mjs search`) sobre Wikimedia Commons: JPEG ≥ 1200 px con
  CC0, dominio público, CC BY o CC BY-SA. Prueba del 2026-11-27: hay candidatos para campo de caña, cosecha de caña,
  cristales de azúcar, uva en la vid, mejillones y plantación de palma.
- **Reglas**:
  - se prefiere CC0 o dominio público; CC BY-SA obliga a compartir la imagen reducida con la misma licencia (se
    declara así);
  - nada del sitio oficial de Manuelita ni con su marca, letreros legibles o personas reconocibles;
  - cada foto es un **sustituto** (`data-source="stand-in"`): ilustra el cultivo o el producto, no a Manuelita;
  - sin pie de foto (regla 1 de la skill): los créditos van en una línea del pie y en
    `web/public/media/fotos/CREDITOS.md` (autor, archivo, licencia, URL).
- **Formato**: `photos.mjs fetch` descarga una vez; se reducen a WebP (1600 y 800 px) y se versionan por Git LFS en
  `web/public/media/fotos/`.
- **Cupo**: 6 a 10 fotos en la entrada (software: las fotos acompañan; la UI real lidera).

## R6. Estructura de la entrada (inspiración en manuelita.com)

Del sitio oficial se toma la estructura y el tono, no la marca: mensaje fuerte, negocios, cuatro tarjetas de
sostenibilidad, noticias y pie de accesos; frases cortas en primera persona del plural. Mapeo a la receta de
software de la skill, una sección por pantalla a 1440×900:

| # | Sección | Idea | Imagen | Pantallas |
|---|---|---|---|---|
| 1 | hero `split` | qué es, para quién, un dato duro; «Habla con Valer-IA» | el video pitch + tarjeta flotante | 1 |
| 2 | `app-frame` | así responde: conversación con citas y fuente abierta | UI real del chat (HTML vivo) | 1–2 |
| 3 | perfiles (bento) | cinco públicos, un agente | glifo y color de cada perfil, una foto por perfil | 1 |
| 4 | negocios (rejilla, sin carrusel) | caña (azúcar, bioetanol, energía), palma, frutas y hortalizas, acuicultura | fotos sustitutas | 1 |
| 5 | frase (`letters-assemble`) | «Cada dato, con su fuente.» | tipo | 1 |
| 6 | planificación (`dark-band`) | reparto de la caña con un optimizador | diagrama de un insumo, un proceso y tres carriles con pulsos | 1 |
| 7 | garantías (4 tarjetas) | cita, cifras calculadas, permiso, no inventa | íconos | 1 |
| 8 | evidencia | herramientas reales y traza | íconos reales (Qdrant, DeepSeek, LangGraph, FastAPI, WhatsApp, OpenClaw) | 1 |
| 9 | preguntas frecuentes | 5 preguntas | — | 1 |
| 10 | cierre `close-type` + `footer-statement` | acción final; declaración de proyecto académico; créditos | — | 1 |

Sin carruseles, pestañas temporizadas ni aparición al hacer scroll (salvo el momento dentro de su sección).

## R7. Áreas de aplicación (agente, planificación, evidencia)

- Son pantallas de trabajo, no páginas de venta: heredan el sistema (tokens, tipo, botones, tarjetas, nav, pie, capa
  de hover y foco) pero no la regla de «una sección por pantalla».
- **Agente**: conversación central a ancho de lectura, perfil activo con su color y glifo, fuentes en panel lateral
  (escritorio) o en hoja inferior (teléfono), tarjeta de aprobación destacada.
- **Planificación**: el flujo de caña y el libro de compromisos con colores de producto fijos y cifras condensadas.
- **Evidencia**: catálogo, traza y servicios con la jerarquía del sitio; tablas legibles a 360 px.
- `gate.mjs` revisa la entrada; las áreas de aplicación se validan con las pruebas e2e, axe y capturas de la skill
  (`shoot.mjs`) a 1440, 1024, 768 y 390.

## R8. Movimiento

- Entrada del hero una vez al cargar; capa de hover y foco (tarjetas que suben 2 px, fotos que hacen zoom 1,02,
  botones que responden); un momento (`letters-assemble`) en su sección. Con «reducir movimiento» todo queda quieto
  y visible. FR-010 se ajusta para permitir ese único momento.

## R9. Calidad y verificación

- `gate.mjs` sobre la entrada servida por `make app` (`--start http://127.0.0.1:8000/`) hasta `GATE: PASS`, con
  `copy-lint`, `consistency`, `check.mjs` (1440, 1024, 820, 768, 390, 320) y `perf.mjs`.
- Vitest y e2e (Playwright) actuales, ajustados; axe sin violaciones; responsive de 360 a 1920 sin scroll horizontal.
- Las exenciones de la skill (Archivo, kit no copiado, áreas de aplicación fuera del gate) van en
  `.taste-skill/waivers.json` con su motivo y en el informe.

## R10. Gobierno

- Constitución **2.6.0** (MINOR): §3.7 (identidad: colores del logotipo, fotos de stock con licencia citada, un
  momento) y ADR 0035. La rama parte de `main` (2.4.0); el PR #86 trae 2.5.0. Este PR se integra después de #86 y se
  rebasa sobre él para no chocar en el historial de la constitución.
