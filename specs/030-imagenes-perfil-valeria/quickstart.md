# Quickstart: Imágenes de perfil y banner de Valer-IA (spec 030)

## Requisitos

- `make dev` ya ejecutado: `web/node_modules` (fuente Archivo) y Chromium de Playwright instalados.
- La imagen de referencia descargada por Git LFS (`git lfs pull --include docs/referencias/*.png`).
- Sin claves, cuentas ni red.

## A. Producir y revisar

```bash
uv run python scripts/whatsapp_images.py render --json
```

Resultado esperado: cuatro PNG en `docs/whatsapp/borrador/` con sus medidas exactas, vistas previas en
`docs/whatsapp/borrador/revision/` y, por pieza, escala ≤ 1,15, contraste ≥ 4,5 y texto dentro de la zona segura.

Revisión humana con las vistas previas:

1. Foto en círculo a 48 px: el rostro se distingue (SC-004); a 640 px es la misma presentadora del video (SC-002).
2. Cada portada con la foto superpuesta, en escritorio y teléfono: el texto se ve completo y sin errores (SC-003).
3. Ninguna pieza muestra el logotipo ni la marca de Manuelita (SC-006).

## B. Aprobar

```bash
uv run python scripts/whatsapp_images.py approve perfil --by "Roberto José Guerrero"
uv run python scripts/whatsapp_images.py approve linkedin --by "Roberto José Guerrero"
uv run python scripts/whatsapp_images.py approve facebook --by "Roberto José Guerrero"
uv run python scripts/whatsapp_images.py approve whatsapp --by "Roberto José Guerrero"
```

Resultado esperado: cada PNG con su ficha `.md` en `docs/whatsapp/`.

## C. Verificar

```bash
uv run python scripts/whatsapp_images.py check --json
LANGSMITH_TRACING=false uv run pytest tests/unit/test_whatsapp_images.py
make check
```

Resultado esperado: `ok: true` con las cuatro piezas aprobadas (SC-001), costo 0 (SC-005) y la suite en verde.

## D. Uso (lo hace el integrante, fuera de esta feature)

Subir cada pieza a su plataforma según `docs/whatsapp/README.md` y pegar el texto de «Info» o descripción con la
declaración de IA (obligatoria en el texto del perfil). Validar SC-002 con 5 personas.

## E. Audios de los stickers (US6)

Requisitos:
- Voz de la spec 016 lista: `uv run python -m proyecto_modelos_lenguaje.voice --check` responde «disponible». La
  primera vez necesita `HF_TOKEN` y las condiciones del modelo aceptadas en Hugging Face.
- Con el modelo ya en la caché, todo corre sin red.

```bash
HF_HUB_OFFLINE=1 uv run python scripts/whatsapp_images.py render --piece audios --json
```

Resultado esperado:
- ocho `.ogg` en `docs/whatsapp/borrador/audios/`;
- cada uno ≤ 5 s, con un RMS cerca de −20 dBFS y un pico ≤ −1 dBFS.

Revisión humana:
1. Escuchar cada borrador sin mirar el texto y anotar la frase que se oye: debe coincidir en los 8 casos (SC-008).
2. Comprobar que la voz es la del chat de la web, que se entiende la entonación de pregunta y de exclamación, y
   que no hay cortes ni ruido.
3. Enviar uno a un chat de prueba de WhatsApp: debe reproducirse como nota de voz sin convertirlo (SC-009).

Aprobar y verificar:

```bash
uv run python scripts/whatsapp_images.py approve audio-hola --by "Roberto José Guerrero"   # uno por audio
uv run python scripts/whatsapp_images.py check --json
LANGSMITH_TRACING=false uv run pytest tests/unit/test_whatsapp_images.py
make check
```

Resultado esperado:
- 8 audios con ficha en `docs/whatsapp/stickers/audios/` (SC-007);
- `check` con `ok: true`;
- la suite en verde sin modelo ni red.
