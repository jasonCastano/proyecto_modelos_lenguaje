# Quickstart: validar los stickers de Valer-IA (spec 034)

## 0. Verificación temprana (antes de implementar todo)

Comprobar en el gateway real que el plugin alcanza el listener activo y que el sticker llega **como sticker**, no
como imagen ni como documento. El mensaje de prueba va al número de un operador. Si falla, aplicar el plan B
(research R1) antes de seguir.

## 1. Sin teléfono

```powershell
uv run pytest tests/unit/channels/test_stickers.py tests/unit/channels/test_bridge.py tests/unit/channels/test_store.py tests/unit/test_ops.py
cd openclaw\plugins\valeria-bridge; npm test; cd ..\..\..
uv run python -m proyecto_modelos_lenguaje.channels simulate --script tests/fixtures/channels/stickers.jsonl --check
make check
```

**Esperado**:

- todo en verde;
- el guion recorre saludo, pregunta, agradecimiento, queja, despedida y conversación en inglés;
- en cada turno aparece el sticker esperado, o ninguno;
- 0 hallazgos: ningún turno con más de un sticker, ningún sticker en una respuesta factual ni en una queja, y
  ninguno con texto en inglés.

## 2. En el teléfono

1. Reiniciar el backend y el gateway (`.\scripts\openclaw_env.ps1 -Restart`); esperar ~2 min.
2. `uv run pml ops check`: `stickers` ✅ «9/9 disponibles».
3. Desde un número sin conversación previa: «Hola».

   **Esperado**: el sticker «¡Bienvenido!» y la presentación.
4. «¿Qué produce Manuelita?». **Esperado**: respuesta con fuentes, sin sticker.
5. «Muchas gracias». **Esperado**: respuesta breve y, después, el sticker «¡Gracias!».
6. «Chao». **Esperado**: despedida y, después, «Lindo día».
7. Una pregunta de planificación que tarde más de 8 s. **Esperado**: «Pensando» antes de la respuesta.
8. Una queja («esto no me sirve, estoy molesto»). **Esperado**: sin sticker.
9. Revisar `channels.jsonl`: el campo `sticker` coincide con lo recibido, sin números ni texto.

## 3. Criterios

| Criterio | Verificación |
|---|---|
| SC-001 a SC-004 | `simulate --check` con `stickers.jsonl` y los pasos 2.3–2.8 |
| SC-005 | prueba del plugin con el listener caído: el texto llega igual |
| SC-006 | opinión de quien prueba en el teléfono (notas de T-final) |
