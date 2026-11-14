# Quickstart: validar la voz del agente (spec 016)

Todos los comandos se ejecutan desde la raíz del repositorio. Si tu `UV_PROJECT_ENVIRONMENT` global apunta a otro
proyecto, antepón `UV_PROJECT_ENVIRONMENT=.venv`.

## 0. Prerrequisitos (una sola vez)

1. Con tu cuenta de Hugging Face, abre <https://huggingface.co/gradium/phonon-40m-es> y acepta las condiciones de
   acceso.
2. Crea un token de lectura en <https://huggingface.co/settings/tokens> y agrégalo a `.env` como `HF_TOKEN=...`.
   Este archivo no se versiona.
3. `uv sync` instala `ptts`; no requiere PyTorch.
4. Si usas x86-64, el equipo necesita una CPU con AVX2. El i9-12900H del equipo de desarrollo cumple.

## 1. Sin red: lo que corre en CI

```bash
make check                                    # incluye las pruebas de voz con el sintetizador simulado
MANUELITA_VOICE_ENGINE=fake uv run python -m proyecto_modelos_lenguaje.voice --check
```

**Esperado**: todo en verde. `--check` sale con 0, con `engine: fake`.

## 2. Motor real

```bash
uv run python -m proyecto_modelos_lenguaje.voice --check                 # descarga ~75 MB la primera vez
uv run python -m proyecto_modelos_lenguaje.voice --list-voices
uv run python -m proyecto_modelos_lenguaje.voice --say "Manuelita produce azúcar, etanol y energía [U2]." -o prueba.wav
uv run pytest -o addopts="" -m voice tests/integration/voice
```

**Esperado**:
- `state: ready`, con la voz femenina configurada.
- `prueba.wav` suena en español con voz de mujer y no pronuncia «U2».
- La prueba `voice` pasa.

**Elegir la voz** (tarea R4): genera la misma frase con cada voz femenina de `--list-voices`, escúchalas en equipo
y fija la elegida en `config/voice.toml`.

## 3. De punta a punta en la app

```bash
make app        # http://127.0.0.1:8000
```

| Escenario | Pasos | Resultado esperado | Criterio |
|-----------|-------|--------------------|----------|
| Voz en vivo | En el chat del agente, en modo demo y en modo real, pregunta «¿Qué produce Manuelita?». | La primera oración suena mientras el texto sigue apareciendo. La voz es femenina, en español, y no lee citas. | US1, SC-001, SC-003 |
| Orden | Haz una pregunta con respuesta larga, como «Resume la historia de Manuelita». | Las oraciones suenan en orden, sin repetirse ni superponerse. | SC-002 |
| Controles | Mientras suena: detener; silenciar y recargar; «Escuchar» en un turno anterior; enviar una nueva pregunta. | Corte en menos de 0,5 s; el silencio persiste tras recargar; relectura completa; la nueva pregunta corta la anterior. | US2, SC-005 |
| Respaldo | Una pregunta fuera de alcance o sin evidencia. | Se lee el mensaje final del turno. | R3 |
| Sin voz | Reinicia con `MANUELITA_VOICE_ENABLED=0`, o sin `HF_TOKEN` ni modelo en caché. | Aviso «La voz no está disponible…». El chat responde por texto igual que antes. `GET /api/voice` devuelve `available=false`. | US3, SC-006 |
| Corpus adversarial | `MANUELITA_DEMO_CORPUS=malicious make app`, con la pregunta s01. | La voz lee la respuesta del agente y nunca la instrucción inyectada. | Edge case |

## 4. Medición

- `MANUELITA_STATE_DIR/logs/voice.jsonl` registra `synth_ms` y `audio_ms` por oración.
- La traza de cada turno muestra «🔊 primer audio X s».
- Sobre 10 preguntas de la rúbrica, verifica que al menos 9 tengan el primer audio en menos de 1,5 s (SC-001).

## 5. Resultados de la validación (2026-11-14)

Equipo de desarrollo: Intel Core i9-12900H, Windows 11, Python 3.14, `ptts` 0.7.1, modelo
`gradium/phonon-40m-es` en `q8_0` y voz Ximena.

| Comprobación | Resultado |
|--------------|-----------|
| `voice --check` (primera vez, con descarga) | `state: ready`; carga 51,6 s (descarga incluida) y luego 0,9 s desde la caché. |
| Rendimiento ya caliente (`synth`) | ~0,17 del tiempo real, unas 6× más rápido: 86 caracteres → 6,5 s de audio en 1,05 s. La primera síntesis en frío es ~2× más lenta, y por eso la precarga sintetiza «Hola.». |
| Prueba `voice` (T043) | 2/2 pasan: voz femenina configurada, WAV de 24 kHz y síntesis < 1,5 s y < 0,5× el tiempo real. |
| SC-001, primer audio (API de punta a punta, 10 preguntas en modo real, variante cadena) | **Sin límite del primer segmento: 7/10 < 1,5 s** (mediana 1,1 s, máximo 2,1 s; las lentas tenían primeras oraciones de ~200 caracteres). **Con el primer segmento limitado a 120 caracteres: 10/10 < 1,5 s** (mediana 0,67 s, máximo 1,03 s). |
| Lectura antes de terminar el streaming | 8/10 respuestas pidieron el primer audio antes del evento `done`. Las otras 2 (saludo directo y fuera de alcance) no emiten tokens: la respuesta llega completa y se lee al final. |
| Orden y estados | 71 oraciones sintetizadas, todas `200` o `204`, en orden de `segment`. |
| Registro `voice.jsonl` | 71 líneas `ok`, con la voz Ximena, sin texto de las respuestas. |
| Sin voz y 503 | Cubiertos por las pruebas de contrato (`tests/api/test_voice_api.py`) y de la interfaz (`ChatViewVoice.test.tsx`). |

**Pendiente de verificación humana**:
- Escuchar en el navegador la naturalidad de la voz (SC-004) y la ausencia de citas leídas (SC-003, cubierto
  por pruebas del texto limpio).
- Medir el corte al detener (SC-005, cubierto por pruebas con audio simulado).
- Elegir la voz definitiva entre las 13 muestras (T037).
