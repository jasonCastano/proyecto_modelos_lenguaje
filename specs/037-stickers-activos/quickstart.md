# Quickstart: validar los stickers activos (spec 037)

## 1. Sin red

```powershell
uv run pytest tests/unit/channels -k sticker
uv run pytest tests/api/test_channels_stickers.py
cd openclaw/plugins/valeria-bridge; npm test; cd ../../..
node --test openclaw/patches/test
make check
```

**Esperado**:

- todo en verde;
- el conjunto ampliado cumple SC-002 a SC-005:
  - entre dos y cuatro stickers en la conversación de seis mensajes;
  - al menos una de cada tres respuestas informativas con sticker;
  - cero stickers en queja, angustia, datos sensibles, crisis y después de «sin stickers»;
  - solo el pulgar en inglés;
  - máximo 8 por conversación y sin repeticiones seguidas no permitidas.

## 2. Entrega real (con instrucciones previas al usuario)

1. Reiniciar el gateway (`ValerIA-Gateway`) y esperar unos 2 minutos.
2. Revisar el log del gateway del día. Debe decir `stickers listos vía compartido` (o `parche`, si se instaló el
   respaldo).
3. Reiniciar el backend (`ValerIA-Backend`).
4. Desde el teléfono: «Hola» → «¿Qué produce Manuelita?» → «¿Y en qué países opera?» → «ok» → «gracias» → «chao».

**Esperado**:

- llegan entre dos y cuatro stickers nativos de WhatsApp (no imágenes ni archivos), en el orden correcto respecto
  al texto;
- todas las respuestas escritas llegan;
- `uv run pml ops check` muestra `stickers hoy` con los entregados iguales a los elegidos (verde).
