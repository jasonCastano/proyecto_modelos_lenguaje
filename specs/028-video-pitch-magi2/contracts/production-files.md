# Contrato: archivos de producción del pitch

## `video/pitch/guion.toml` (ejemplo de forma, no el texto final)

```toml
version = "1.0.0"
language = "es"
max_seconds = 57

[[block]]
id = "gancho"
narration = "¿Y si cada persona que trabaja con Manuelita tuviera un agente que responde con fuentes?"
claims = []

[[block]]
id = "uso"
narration = "Elige tu perfil, pregunta, revisa las fuentes y, si planificas, abre la consola."
on_screen = "1 Perfil · 2 Pregunta · 3 Fuentes · 4 Planificación"
claims = []
synthetic = false
```

Las cifras o hechos de Manuelita (fundación, negocios, países) solo entran con su `unit_id` en `claims`.

## `video/pitch/escenas.json`

```json
[
  {"id": "escena-01", "block": "gancho", "prompt_file": "video/pitch/prompts/escena-01.json",
   "image": "docs/referencias/avatar_ingenio_manuelita.png", "seed": 2026,
   "model": "sand-ai/MAGI-2-preview", "model_revision": null, "resolution": "1080x1920",
   "generated_at": null, "clip": null, "duration_s": null, "trim_s": 9.5,
   "status": "pendiente", "review": null}
]
```

## `video/pitch/prompts/escena-0N.json`

Caption estructurado que MAGI-2 recibe como `prompt_file`. Campos mínimos:

- `scene`: acción de la presentadora y el entorno (cañaduzal, ingenio al fondo, luz de la mañana);
- `camera`: plano y movimiento;
- `audio`: ambiente de campo, sin voz;
- `constraints`: sin texto en pantalla, sin logotipos, la presentadora no habla a cámara.

El texto narrado no va aquí: lo pone la narración.

## `docs/referencias/avatar_ingenio_manuelita.md`

```markdown
---
file: avatar_ingenio_manuelita.png
sha256: <hash>
origin: "<herramienta de IA y fecha>"
rights: "<derechos de uso del equipo>"
real_person: false
brand_elements: false
confirmed_by: "<integrante>"
---
```
