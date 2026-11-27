# Quickstart: validar la spec 030

## 1. Sin teléfono

Pruebas automáticas y simulación:

```powershell
uv run pytest tests/unit/channels/test_format.py tests/unit/channels/test_quality.py tests/unit/channels/test_bridge.py tests/api/test_channels_api.py
cd openclaw/plugins/valeria-bridge; npm test; cd ../../..
uv run pml channels simulate --sender +570000000001 --script tests/fixtures/channels/language_format.jsonl --check
```

Esperado:

- **Regresión**: las dos respuestas reales de `regression_2026-11-27b.jsonl`, tratadas como turno con voz, fallan
  (`voice_text_duplicate`). Su bloque de fuentes aislado pasa.
- **Simulador**: 0 hallazgos, con estos textos:
  - consultas por audio con fuentes: solo fuentes;
  - consultas por audio sin fuentes: sin texto;
  - consultas escritas: respuesta completa.

## 2. Falla de voz simulada

Las pruebas del puente y del plugin cubren dos casos:

- **Falla al generar la voz**: llega la respuesta completa y el aviso de que no se pudo enviar el audio.
- **Falla al entregar la voz** (el adaptador lanza error): el plugin devuelve `messages`, no `sources_messages`.

## 3. Con el teléfono

Las instrucciones se dan antes de ejecutar. Después de reiniciar, esperar ~2 min a que el gateway escuche WhatsApp.

1. Reiniciar el backend (`.\scripts\serve_backend.ps1 -Restart`) y el gateway (`.\scripts\openclaw_env.ps1 -Restart`).
2. Repetir por voz las dos pruebas de las 13:26 y 13:31:
   - «¿Puedes darme datos de los productos que genera Manuelita?» → nota de voz que cierra con «Te dejo las fuentes
     por escrito» y un texto con solo «Fuentes:» y 3 líneas.
   - «¿Cuánta caña va a producir Manuelita este año?» → nota de voz y un texto con «Fuentes:» y 1 línea.
3. «Hola Valeria» por voz → solo la nota de voz.
4. Una pregunta por texto → respuesta completa con fuentes, como siempre.
5. En `channels.jsonl` (solo metadatos), revisar `written`:
   - `sources` / `none` para las preguntas por voz;
   - `full` para la pregunta por texto.

## 4. No regresión

`make check` en verde. La spec no toca el agente ni la recuperación, así que las evaluaciones de herramientas y del
blindaje del canal no cambian.
