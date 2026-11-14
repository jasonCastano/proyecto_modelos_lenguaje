# Contrato CLI: `python -m proyecto_modelos_lenguaje.voice` (spec 016)

```bash
uv run python -m proyecto_modelos_lenguaje.voice --check [--json]
uv run python -m proyecto_modelos_lenguaje.voice --list-voices [--json]
uv run python -m proyecto_modelos_lenguaje.voice --say "Hola, soy el asistente de Manuelita." [--voice Regina] [-o salida.wav]
```

| Opción | Comportamiento |
|--------|----------------|
| `--check` | Carga el motor (descarga el modelo si falta), sintetiza una frase corta y muestra el estado (`VoiceStatus`), el tiempo de carga y el de síntesis. Sale con 0 si está listo y con 2 si no está disponible, mostrando el motivo. |
| `--list-voices` | Lista las voces en español del catálogo con nombre, id, acento (ES/MX) y género. La voz configurada aparece marcada. |
| `--say TEXTO` | Limpia el texto con `clean_for_speech`, lo sintetiza y escribe un WAV. Sin `-o`, lo escribe en un archivo temporal del sistema e imprime su ruta. Nunca escribe en `data/`. |
| `--voice NOMBRE` | Cambia la voz solo para esta ejecución. |
| `--json` | Imprime la salida como JSON para usarla en scripts. |

Códigos de salida: `0` OK · `1` argumentos inválidos o error de síntesis · `2` motor no disponible.

`--check` y `--say` con el motor `phonon` requieren el modelo y, la primera vez, red y `HF_TOKEN`. Con
`MANUELITA_VOICE_ENGINE=fake` funcionan sin red, y así se prueban en pytest.
