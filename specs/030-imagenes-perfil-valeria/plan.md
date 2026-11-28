# Implementation Plan: Imágenes de perfil y banner de Valer-IA

**Branch**: `030-imagenes-perfil-valeria` (US6 en una rama propia; la 030 ya se fusionó en el PR #86) | **Date**: 2026-11-27 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/030-imagenes-perfil-valeria/spec.md`

## Summary

Cuatro piezas de identidad de Valer-IA: la foto de perfil (640×640) y las portadas de LinkedIn (1584×396), Facebook
(1640×624) y WhatsApp Business (1920×1080). Se guardan en `docs/whatsapp/`.

El enfoque técnico, sin costo y sin modelos generativos (FR-010):

- **Diseño**: cada pieza es una página HTML/CSS a la medida exacta, hecha con la skill `design` (flujos de banners y
  de imágenes para redes) y la guía de `frontend-design`. Usa la imagen de referencia tal cual, recortada, con la
  paleta, la tipografía Archivo y los pictogramas de la plataforma web.
- **Exportación**: Playwright/Chromium local la convierte en PNG; ya se usa para los gráficos del pitch.
- **Revisión**: `scripts/whatsapp_images.py render` deja borradores y vistas previas (círculo a 48 px, portadas con
  la foto superpuesta en escritorio y teléfono). `approve` publica la pieza con su ficha y `check` verifica medidas,
  fichas, costo 0, escala y contraste.
- **Gobierno**: constitución 2.5.0 (§10, imágenes de perfil) con ADR 0034.

**Ampliación US6 (2026-11-27): audios de los stickers.** Ocho audios cortos con la frase de cada sticker
(todos menos el pulgar), dichos con la voz oficial del agente (Phonon, «Rebeca», spec 016), en
`docs/whatsapp/stickers/audios/`. Enfoque:

- **Síntesis**: `VoiceService` de la spec 016, con su configuración (`config/voice.toml`), en el equipo y con el
  modelo ya en la caché de Hugging Face (`HF_HUB_OFFLINE=1`). Sin servicios externos ni costo.
- **Acabado**: se recorta el silencio, se añaden 150 ms de silencio a cada lado y se iguala el volumen de los ocho
  (R12). Se exporta a OGG/Opus mono de 48 kHz, el formato de las notas de voz de WhatsApp, con PyAV, que ya es
  dependencia del proyecto (spec 023). No hay dependencias nuevas.
- **Flujo**: el mismo de las imágenes. `render` deja el borrador, una persona lo escucha, `approve --by` lo
  publica con su ficha y `check` verifica duración ≤ 5 s, formato, huella y ficha.
- **Gobierno**: enmienda MINOR 2.7.0 de §10 (audios de los stickers con la voz del agente) con ADR 0036 (R13).

## Technical Context

**Language/Version**: Python ≥ 3.14 (uv); HTML/CSS/SVG para las piezas
**Primary Dependencies**: ya presentes: Playwright (grupo dev) con Chromium, Pillow, `@fontsource-variable/archivo`
(en `web/node_modules`). Sin dependencias nuevas.
**Storage**: archivos
- `docs/whatsapp/*.png` por Git LFS; fichas `*.md` y `README.md` como texto;
- `docs/whatsapp/fuente/` (HTML, CSS, SVG) como texto;
- `docs/whatsapp/borrador/` ignorado por Git.

**Testing**: pytest, `tests/unit/test_whatsapp_images.py` (sin navegador ni red; imágenes sintéticas con Pillow)
**Target Platform**: Windows del integrante; las pruebas corren también en el CI (Linux)
**Project Type**: herramienta de producción fuera de línea (script) + recursos de documentación
**Performance Goals**: `render` de las cuatro piezas en menos de 30 s
**Constraints**:
- costo 0, sin red, sin claves (FR-010, FR-012);
- escala de la referencia ≤ 1,15 (R3);
- texto con contraste AA y dentro de la zona segura (R2, R5);
- sin marca de Manuelita (FR-006).

**Scale/Scope**: 4 piezas, 1 script, 1 archivo de pruebas, documentación y gobierno

**Ampliación US6 (audios)**:
- **Dependencias**: ya presentes. `ptts` 0.7.1 (Phonon, spec 016) con el modelo `gradium/phonon-40m-es` `q8_0` en la
  caché de Hugging Face, `numpy` y `av` (PyAV 19 con `libopus`).
- **Formato**: OGG/Opus, mono, 48 kHz, 32 kbit/s. Phonon entrega 24 kHz y se remuestrea.
- **Almacenamiento**: `docs/whatsapp/stickers/audios/valeria-<nombre>.ogg` por Git LFS, más su ficha `.md`. Los
  borradores van en `docs/whatsapp/borrador/audios/`, que Git ignora.
- **Pruebas**: con `FakeSynthesizer` y PyAV, sin modelo ni red, para que corran en el CI. La síntesis real queda
  marcada `voice`.
- **Restricciones**: duración ≤ 5 s (FR-019), sin red (`HF_HUB_OFFLINE=1`), nada en `data/`.
- **Rendimiento**: en la prueba con Phonon (R12), las frases duran entre 1,2 y 2,3 s y pesan menos de 9 KB. La
  síntesis de los ocho tarda menos de 1 minuto en CPU.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Regla | Estado |
|---|---|
| §10 Ética y uso de IA: persona sintética con ficha, sin marca de Manuelita, declaración de IA | ✅ Las piezas usan solo la referencia con `real_person: false` y `brand_elements: false`. La declaración de IA va en el texto del perfil de cada red (decisión del integrante). Se añade regla nueva en §10 (R9) |
| §10 Fuentes y licencias: todo recurso externo se cita con su licencia | ✅ Archivo (OFL-1.1) y la referencia van en cada ficha (FR-008, FR-011) |
| §3.7 Identidad visual: Archivo, paleta por producto, pictogramas propios, contraste AA | ✅ Se reutilizan los tokens y glifos de la web; `check` mide el contraste |
| Secretos solo en `.env` | ✅ No hay claves |
| Capas medallion intactas | ✅ No se toca `data/` |
| `make check` en verde; pruebas sin red | ✅ Prueba unitaria sin navegador |
| Cambio de proceso o ético → constitución en el mismo commit | ✅ Enmienda MINOR 2.5.0 + ADR 0034; requiere la aprobación de ambos integrantes |
| Autoría (§4.3): solo los integrantes en Git | ✅ Commits como Robertto48, sin coautores |

**Ampliación US6 (audios)**:

| Regla | Estado |
|---|---|
| §2 Stack: voz con Phonon, modelo y voces CC BY-NC 4.0, modelo en la caché y nunca en el repo | ✅ Se reutiliza `VoiceService` con la voz oficial; la ficha y el README dan la licencia y la atribución (FR-022) |
| §10 Imágenes de perfil: «sin modelos generativos» | ⚠️ La regla trata de imágenes. Los audios sí usan un modelo de síntesis de voz, así que se amplía §10 con una regla propia para los audios (R13), en vez de forzar la de imágenes |
| §10 Ética: no clonar ni imitar voces reales | ✅ «Rebeca» es una voz de catálogo del modelo, no una clonación (spec 016) |
| Privacidad y red | ✅ La síntesis es local y sin red; el texto son frases fijas |
| `make check` sin red ni modelo | ✅ Las pruebas usan `FakeSynthesizer`; la síntesis real va marcada `voice` |
| Cambio de proceso o ético → constitución en el mismo commit | ✅ MINOR 2.7.0 + ADR 0036; requiere la aprobación de ambos integrantes |

**Post-diseño**: sin violaciones; la sección de complejidad queda vacía.

## Project Structure

### Documentation (this feature)

```text
specs/030-imagenes-perfil-valeria/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/whatsapp-images-cli.md
├── checklists/requirements.md
└── tasks.md                 # /speckit-tasks
```

### Source Code (repository root)

```text
scripts/whatsapp_images.py          # render | approve | check (fuera de línea)
tests/unit/test_whatsapp_images.py  # check y fichas, sin navegador

docs/whatsapp/
├── README.md                       # índice, dónde subir cada pieza, textos de «Info» y descripción
├── fuente/
│   ├── base.css                    # tokens de la paleta, Archivo, zonas seguras
│   ├── glifos/*.svg                # pictogramas de producto de la web
│   ├── perfil.html
│   ├── linkedin.html
│   ├── facebook.html
│   └── whatsapp.html
├── valeria-perfil.png (+ .md)      # aprobadas, LFS
├── valeria-linkedin.png (+ .md)
├── valeria-facebook.png (+ .md)
├── valeria-whatsapp-portada.png (+ .md)
├── stickers/
│   └── audios/                     # US6: valeria-<nombre>.ogg (+ .md), 8 audios, LFS
└── borrador/                       # ignorado por Git: exportaciones y vistas previas de revisión
    └── audios/                     # US6: borradores .ogg para escuchar antes de aprobar

.gitattributes                      # docs/whatsapp/**/*.png|webp y, en US6, **/*.ogg por LFS
.gitignore                          # docs/whatsapp/borrador/
CONSTITUTION.md                     # 2.5.0, §10; US6: 2.7.0
docs/decisions/0034-imagenes-perfil-valeria.md
docs/decisions/0036-audios-stickers-valeria.md   # US6
README.md                           # enlace a docs/whatsapp/
```

En US6, `scripts/whatsapp_images.py` suma piezas de tipo `audio` al catálogo (`audio-<nombre>`), y
`tests/unit/test_whatsapp_images.py` suma pruebas de acabado, formato, ficha y `check` de los audios.

**Structure Decision**: script en `scripts/`, como las demás herramientas de una sola vez del proyecto; no entra en
`src/` ni en `pml` porque no es parte de la app (spec, supuestos). Las fuentes de diseño viven junto a sus PNG para
que una pieza se pueda reexportar o ajustar sin buscar en otro lugar.

## Ajustes a la spec derivados del plan

- FR-003: «sobre el fondo de la referencia armonizado con la paleta de Valer-IA» (R4), en lugar de un fondo nuevo.
- Supuestos: la rama parte de `029-pitch-escenas-sincronizadas` y depende de los PR #84 y #85 (R9).
- Medidas confirmadas en R2 (WhatsApp Business: 1920×1080, 16:9).
- US6:
  - **FR-021:** el formato es OGG/Opus mono de 48 kHz (R12).
  - **Ficha (FR-022):** registra el modelo de voz en `tts_model`. El campo `generative_model: none` sigue
    aplicando solo a las imágenes (R13).

## Complexity Tracking

Sin violaciones de la constitución.
