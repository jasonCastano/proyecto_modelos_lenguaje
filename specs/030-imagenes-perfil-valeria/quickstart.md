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
