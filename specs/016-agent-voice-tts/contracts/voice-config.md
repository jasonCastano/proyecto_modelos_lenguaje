# Contrato de configuración: voz (spec 016)

## `config/voice.toml` (versionado)

```toml
[voice]
enabled = true
engine = "phonon"                       # "phonon" | "fake"
model = "hf://gradium/phonon-40m-es"
language = "es"
quant = "q8_0"                          # ptts.available_quants(): f32, q8_0, q8k, q6k, q5k, q4k, …
voice = "Rebeca"                        # voz oficial: femenina, español de México (id Sx8m6WdXBG06zwZT)
voice_gender = "female"
max_chars = 600
warmup = true
```

## Variables de entorno (tienen prioridad sobre el TOML)

| Variable | Efecto |
|----------|--------|
| `MANUELITA_VOICE_ENABLED` | `0`/`false` desactiva la voz. |
| `MANUELITA_VOICE_ENGINE` | `fake` usa el sintetizador simulado (pruebas, demo sin modelo). |
| `MANUELITA_VOICE` | Cambia la voz sin editar el TOML. |
| `MANUELITA_VOICE_WARMUP` | `0` no precarga el modelo al arrancar; las pruebas de la API lo usan. |
| `HF_TOKEN` | Token de Hugging Face para descargar el modelo, que exige aceptar condiciones. Va solo en `.env`; en `.env.example` aparece sin valor. |

Valores inválidos (motor desconocido, cuantización fuera de `ptts.available_quants()`, `max_chars` fuera de 1–1000, voz vacía) → error de configuración al arrancar
el servicio de voz, que queda `unavailable` con el motivo; la app sigue arrancando.
