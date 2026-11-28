# Quickstart: validar la spec 031

## 1. Sin teléfono

```powershell
uv run pytest tests/unit/channels/test_limits.py tests/unit/channels/test_bridge.py tests/unit/test_ops.py tests/api/test_channels_api.py
```

Esperado:

- **Límites**:
  - un número no operador recibe 1 aviso al superar 20 mensajes en 10 minutos, y el resto se ignora;
  - lo mismo con 100 en el día;
  - los operadores no tienen límites.
- **Bloqueo**: un bloqueado se ignora y no llama al agente.
- **Atajos del operador**: con `VALERIA_OPERATORS` configurado, solo responden a operadores.
- **`ops check`**: muestra `modo-canal` según `WA_DM_POLICY`.
- **Privacidad**: con 3 números distintos, ningún número completo aparece en registros, almacén ni estado.

## 2. Configurar operadores (una vez, en el servidor)

```powershell
uv run pml channels pseudonym --sender +57XXXXXXXXXX   # por cada número de prueba
# copiar los seudónimos a VALERIA_OPERATORS=wa-…,wa-… en el .env del repositorio (no versionado)
.\scripts\serve_backend.ps1 -Restart
```

## 3. Abrir el canal y probar con un número nuevo

1. Abrir el canal: `.\scripts\openclaw_env.ps1 -Mode open`. Esperar ~2 min a que el gateway escuche WhatsApp.
2. Revisar el estado: `uv run python -m proyecto_modelos_lenguaje.ops check` debe mostrar
   `modo-canal: ABIERTO al público`.
3. Desde un número que nunca le ha escrito:
   - «Hola»;
   - una pregunta por texto;
   - una nota de voz.
   Las tres reciben respuesta, sin código de emparejamiento.
4. Repetir desde un segundo número nuevo (SC-001).
5. Revisar el estado del canal: `people_today` ≥ 2; ningún número completo en `channels.jsonl`.

## 4. Cerrar (mantenimiento o fin del proyecto)

1. `.\scripts\openclaw_env.ps1 -Mode closed`.
2. El número nuevo deja de recibir respuesta y los de prueba siguen.
3. `ops check` muestra `cerrado (N números)`.

## 5. No regresión

`make check` en verde. El agente, la recuperación y los prompts no cambian.
