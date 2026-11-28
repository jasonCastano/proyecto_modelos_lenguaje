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
   "provider": "higgsfield", "model": "sand/magi-2/image-to-video", "model_revision": null,
   "request_seconds": 10, "resolution": "1080x1920", "job": null, "history": [],
   "generated_at": null, "clip": null, "duration_s": null, "trim_s": 9.5,
   "status": "pendiente", "review": null}
]
```

Con un trabajo terminado, `job` queda así:

```json
{"request_id": "…", "status": "completed", "submitted_at": "2026-11-27T15:02:11Z",
 "finished_at": "2026-11-27T15:05:40Z", "seconds": 10, "cost_usd": 0.8,
 "idempotency_key": "escena-01:3f2a…:2026", "error": null}
```

Al cargar el archivo se aceptan las entradas antiguas sin `provider`, `job` ni `history`: se completan con los
valores por defecto.

## `config/pitch.toml`

```toml
[higgsfield]
base_url = "https://api.higgsfield.ai"
model = "sand/magi-2/image-to-video"
api_key_env = "HIGGSFIELD_API_KEY"   # formato id:secreto, solo en .env
resolution = "1080p"
aspect_ratio = "9:16"                # sin él, MAGI-2 extiende la imagen a 16:9
seconds = 10
audio = true
poll_s = 10
timeout_s = 3600

[higgsfield.fields]                  # confirmados con --calibrate (research R11)
duration = "duration"
audio = "generate_audio"
aspect_ratio = "aspect_ratio"

[budget]
usd_per_second = 0.08
max_usd = 20
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
