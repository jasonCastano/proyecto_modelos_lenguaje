# Evaluación del dictado (spec 023)

Generado: 2026-11-23T16:31:17+00:00 · frases: 44 · voces de Phonon: Rebeca, Regina · grabaciones humanas: 0.

Motor `whisper`, `compute_type` int8, `beam_size` 1, idioma `es`, `no_speech_threshold` 0.6. El vocabulario propio (12 términos) va como prompt inicial.

Metas: SC-001 WER ≤ 0.15 · SC-002 vocabulario ≥ 90 % · SC-003 p90 < 2 s para clips de hasta 10 s · SC-004 vacío en el 100 % de los silencios y ruidos.

| Modelo | WER | Vocabulario | p50 / p90 ≤ 5 s (ms) | p50 / p90 5–10 s (ms) | p90 ≤ 10 s (ms) | Vacío en silencio | SC-001 | SC-002 | SC-003 | SC-004 |
|---|---|---|---|---|---|---|---|---|---|---|
| `base-int8` | 0.048 | 72/74 (97 %) | 994 / 1073 | 568 / 580 | 1073 | 100 % | ✅ | ✅ | ✅ | ✅ |
| `small-int8` | 0.027 | 74/74 (100 %) | 2160 / 2915 | 2509 / 2759 | 2915 | 100 % | ✅ | ✅ | ❌ | ✅ |

## Frases con más error · `base-int8`

| Frase | Voz | Audio (ms) | Reconocimiento (ms) | WER | Referencia | Transcripción |
|---|---|---|---|---|---|---|
| d08-Rebeca | Rebeca | 2240 | 953 | 0.67 | ¿Manuelita produce etanol? | Manuelita, Produceta Noel. |
| v09-Rebeca | Rebeca | 4000 | 1036 | 0.45 | Me interesa saber qué hace Océanos y qué produce Mejillones América. | Me interesa saber qué hace o sea anos y qué produce mi jillones América. |
| d08-Regina | Regina | 2240 | 931 | 0.33 | ¿Manuelita produce etanol? | Manuelita, Produce Tanol. |
| c06-Rebeca | Rebeca | 2880 | 967 | 0.25 | No entendí bien, ¿me lo explicas otra vez? | No entendí bien, me lo explica su otra vez. |
| d03-Rebeca | Rebeca | 2320 | 939 | 0.20 | ¿En qué países opera Manuelita? | ¿En qué países operan Manuelita? |
| v06-Rebeca | Rebeca | 2640 | 985 | 0.20 | ¿Qué productos vende Aceites Manuelita? | ¿Qué productos vende a Aceites Manuelita? |
| d12-Regina | Regina | 2800 | 966 | 0.17 | ¿Qué programas sociales tiene la fundación? | ¿Qué programa sociales tiene la Fundación? |
| d09-Rebeca | Rebeca | 2080 | 933 | 0.14 | ¿Qué hace la empresa con el agua? | ¿Qué hacen la empresa con el agua? |

## Frases con más error · `small-int8`

| Frase | Voz | Audio (ms) | Reconocimiento (ms) | WER | Referencia | Transcripción |
|---|---|---|---|---|---|---|
| d03-Rebeca | Rebeca | 2320 | 2160 | 0.40 | ¿En qué países opera Manuelita? | ¿En qué país se opera Manuelita? |
| d03-Regina | Regina | 2320 | 2365 | 0.40 | ¿En qué países opera Manuelita? | ¿En qué país es Opera Manuelita? |
| d08-Regina | Regina | 2240 | 2147 | 0.33 | ¿Manuelita produce etanol? | Manuelita produce Tanol. |
| d12-Rebeca | Rebeca | 2720 | 2093 | 0.33 | ¿Qué programas sociales tiene la fundación? | ¿Qué programa social tiene la fundación? |
| d12-Regina | Regina | 2800 | 2142 | 0.33 | ¿Qué programas sociales tiene la fundación? | ¿Qué programa social tiene la fundación? |
| v06-Regina | Regina | 2720 | 1944 | 0.20 | ¿Qué productos vende Aceites Manuelita? | ¿Qué productos vende a Aceites Manuelita? |
| c05-Rebeca | Rebeca | 2960 | 2051 | 0.14 | ¿Eres una persona o una inteligencia artificial? | ¿Eres una persona de una inteligencia artificial? |
| c05-Regina | Regina | 3200 | 2135 | 0.14 | ¿Eres una persona o una inteligencia artificial? | ¿Eres una persona a una inteligencia artificial? |

El audio se genera en memoria en cada corrida y no se guarda. Las grabaciones humanas, si las hay, son locales y su texto solo se publica con `--include-human-text`.
