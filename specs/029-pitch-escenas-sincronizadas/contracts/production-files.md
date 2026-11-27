# Contrato: archivos de producción (v2)

## `config/pitch.toml`

```toml
[higgsfield]
base_url = "https://api.higgsfield.ai"
api_key_env = "HIGGSFIELD_API_KEY"
poll_s = 10
timeout_s = 3600

[pitch]
model = "magi2"            # cambia a "kling4" solo con decisión del integrante (research R1)
pause_s = 0.5
retime_min = 0.8
retime_max = 1.25

[models.magi2]
usd_per_second = 0.08
resolution = "1080p"
aspect_ratio = "9:16"
image = "sand/magi-2/image-to-video"
reference = "sand/magi-2/reference-to-video"   # campos por calibrar
text = "sand/magi-2/text-to-video"

[models.kling4]
usd_per_second = 0.19
resolution = "1080p"
aspect_ratio = "9:16"
image = "kling-video/v4.0/image-to-video"
reference = "kling-video/v4.0/reference-to-video"   # exige `elements`
text = "kling-video/v4.0/text-to-video"

[budget]
max_usd = 20
```

## `video/pitch/guion.toml` (fragmento)

```toml
version = "1.2.0"
pause_s = 0.5

[[block]]
id = "problema"
narration = "Su información pública está repartida en informes, noticias y páginas de cuatro plataformas: caña, palma, acuicultura y frutas."

[[block.cue]]
id = "problema.informes"
word = "informes"
kind = "grafico"
graphic = "icono-informes"
from = [0.15, 0.30]
to = [0.55, 0.62]     # posición de la tablet en el plano 02
```

## `video/pitch/prompts/plano-03a.json`

Igual que los prompts de la 028: `subject`, `setting`, `style`, `action`, `camera`, `audio`, `constraints` y
`duration_s`. Además:

- `people`: descripción fija de las cinco personas, la que reusan 03b y 06. Por ejemplo, «visitante: mujer joven
  con mochila y cámara; …»;
- `constraints`: sin texto, sin logotipos, sin uniformes ni carnés de empresa y sin parecido con personas reales.

## Archivos versionados y LFS

| Ruta | Git |
|---|---|
| `video/pitch/planos/*.mp4` | LFS |
| `video/pitch/graficos/png/*.png` | LFS (nueva regla en `.gitattributes`) |
| `video/pitch/graficos/*.svg`, `sincronia.json`, `escenas.json`, `prompts/*.json` | texto |
| `video/pitch/borrador/` | ignorado |
