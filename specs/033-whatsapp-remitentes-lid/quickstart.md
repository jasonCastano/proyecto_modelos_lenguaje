# Quickstart: validar la respuesta a cuentas identificadas solo por ID (spec 033)

## 1. Sin teléfono

```powershell
uv run pytest tests/unit/channels/test_identity.py tests/unit/channels/test_bridge.py `
  tests/unit/channels/test_cli_operator.py tests/unit/test_ops.py tests/api/test_channels_api.py
node --test openclaw/patches/test/whatsapp-lid.test.mjs
cd openclaw\plugins\valeria-bridge; npm test; cd ..\..\..
make check
```

**Esperado**:

- todo en verde;
- un remitente `…@lid` ficticio recibe respuesta con seudónimo `wa-…` y máscara `ID ••••…`;
- un mensaje con `received_at` de hace 20 min queda `ignored` con evento `stale`;
- el parche aplica sobre copias de los archivos, es idempotente y falla sin anclajes.

## 2. Estado del parche en el equipo

```powershell
node openclaw\patches\whatsapp-lid.mjs --check      # antes: soporte-lid: ausente
.\scripts\openclaw_env.ps1 -Install                  # aplica el parche y reinicia el gateway
node openclaw\patches\whatsapp-lid.mjs --check      # después: soporte-lid: parcheado
uv run pml ops check                                 # soporte-lid ✅
```

Después de reiniciar el gateway, esperar **~2 minutos** antes de escribir.

## 3. Prueba real con la cuenta que falló (antes de activarlo para la sustentación)

1. Reiniciar el backend (tarea `ValerIA-Backend`; ver la guía de despliegue).
2. Desde el número que no recibió respuesta el 2026-11-27, escribir «¿Qué produce Manuelita?».

   **Esperado**: saludo, presentación y respuesta con fuentes en el chat de esa cuenta.
3. Desde el mismo número, «¿y en Perú?». **Esperado**: la misma conversación, sin presentación.
4. Enviar una nota de voz. **Esperado**: llega la nota de voz de respuesta a ese chat, con solo las fuentes por
   escrito.
5. Revisar `channels.jsonl` (sin números): `sender_kind: "lid"` en esos turnos.

   El mensaje retenido de las 20:34 debe aparecer como `stale`, sin respuesta.
6. Si el paso 2 o el 4 fallan, desactivar el soporte reinstalando el componente:

   ```powershell
   openclaw plugins install @openclaw/whatsapp --force
   ```

   No ejecutar `-Install` en ese caso, porque vuelve a aplicar el parche. Luego reiniciar con `-Restart` y
   documentar la limitación para la sustentación.

## 4. Criterios

| Criterio | Verificación |
|---|---|
| SC-001, SC-002 | pasos 3.2–3.4 |
| SC-003 | registro del gateway sin `LID identity unavailable` después del parche |
| SC-004 | pruebas de privacidad (sin dígitos de ID en logs ni registros) |
| SC-005 | reinstalar el componente → `ops check` ❌ → `-Install` → ✅ |
| SC-006 | `make check` en verde |
