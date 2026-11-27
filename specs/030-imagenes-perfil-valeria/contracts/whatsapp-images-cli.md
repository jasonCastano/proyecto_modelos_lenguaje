# Contrato: `scripts/whatsapp_images.py`

Herramienta de producción fuera de línea. No forma parte de la app ni del CLI `pml`. Sin red, sin claves.

```text
uv run python scripts/whatsapp_images.py render [--piece ID ...] [--json]
uv run python scripts/whatsapp_images.py approve ID --by "NOMBRE" [--json]
uv run python scripts/whatsapp_images.py check [--json]
```

`ID` ∈ `perfil`, `linkedin`, `facebook`, `whatsapp`.

## `render`

- Valida la referencia (existe, no es puntero LFS, `sha256` y ficha como en `data-model.md`).
- Exporta cada pieza pedida (todas por omisión) desde `docs/whatsapp/fuente/<id>.html` a
  `docs/whatsapp/borrador/<archivo>.png` con Chromium a la medida exacta, `device_scale_factor` 1.
- Escribe las vistas previas de revisión en `docs/whatsapp/borrador/revision/` (círculo a 48/96/640 px; portadas
  con la foto superpuesta en escritorio y teléfono).
- Mide y reporta por pieza: medidas, escala de la referencia, contraste mínimo del texto, si el texto cabe en la
  zona segura.
- Salida 0 si todo se exportó; 1 si falta la referencia, Chromium o las fuentes (`web/node_modules`), con el paso
  para resolverlo (`make dev`).

## `approve`

- Exige que exista el borrador de la pieza y que pase las mismas comprobaciones de `check`.
- Copia el PNG a `docs/whatsapp/<archivo>.png` y escribe `docs/whatsapp/<archivo>.md` con la ficha.
- `--by` es obligatorio; la fecha es la del día.
- Salida 0 al aprobar; 1 si falta el borrador o no pasa las comprobaciones (no copia nada).

## `check`

Para cada pieza aprobada:

- el PNG existe, no es puntero LFS y mide lo que dice el catálogo;
- la ficha existe y su `sha256`, medidas y `reference_sha256` coinciden;
- `generative_model: none`, `cost_usd: 0`, fuentes con licencia libre, `approved_by` y `approved_at` presentes;
- las portadas registran `disclosure_in` (la declaración de IA va en el texto del perfil).

Reporta las piezas que faltan por aprobar sin fallar por ello; falla (salida 1) ante cualquier incoherencia.

## `--json`

```json
{"ok": true, "pieces": [{"id": "perfil", "status": "aprobada", "width": 640, "height": 640,
  "scale": 1.07, "min_contrast": null, "errors": []}]}
```
