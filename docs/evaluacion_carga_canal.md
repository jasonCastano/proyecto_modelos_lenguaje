# Prueba de carga del canal WhatsApp (spec 024, SC-002)

**Fecha**: 2026-11-23 · **Equipo**: portátil de desarrollo (Windows 11), no el PC servidor · **Modo**: real
(DeepSeek `deepseek-flash`), Qdrant embebido · **Backend**: `uvicorn` en `127.0.0.1:8020` con un `MANUELITA_STATE_DIR`
temporal.

El cliente simula el puente de OpenClaw (`valeria-bridge`): manda `POST /api/channels/messages` con el token del
canal y un remitente E.164 ficticio distinto por cada usuario.

```bash
uv run pml channels simulate --backend http://127.0.0.1:8020 --sender +570000000100 \
    --text "¿Qué produce Manuelita?"
uv run pml channels simulate --backend http://127.0.0.1:8020 --sender +570000000200 \
    --text "¿Dónde tiene operaciones Manuelita?" --concurrency 10
```

| Prueba | Solicitudes | Respondidas | p90 | Máximo | Meta (SC-002) |
|---|---:|---:|---:|---:|---|
| Primer mensaje (incluye calentamiento del índice y del modelo) | 1 | 1 | — | 12,7 s | — |
| 10 usuarios a la vez | 10 | 10 (`answered`) | 7,3 s | 7,3 s | p90 < 15 s y máximo ≤ 45 s ✅ |

`GET /api/channels/status` registró después 11 mensajes en la última hora, 0 errores y p90 7,3 s. Sin
`X-Channel-Token`, la misma ruta responde 403.

**Pendiente**: repetir la prueba en el PC servidor con Qdrant servidor y con teléfonos reales a través de OpenClaw
(T083, T084). La latencia de WhatsApp suma el ida y vuelta del gateway y de la red móvil.
