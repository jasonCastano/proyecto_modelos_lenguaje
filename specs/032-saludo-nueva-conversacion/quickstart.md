# Quickstart: validar el saludo al iniciar una conversación (spec 032)

## 1. Sin teléfono (cualquier equipo con el repositorio)

```powershell
uv run pytest tests/unit/channels/test_greeting.py tests/unit/channels/test_store.py `
  tests/unit/channels/test_bridge.py tests/unit/channels/test_voice.py tests/unit/channels/test_journal.py
uv run python -m proyecto_modelos_lenguaje.channels simulate `
  --script tests/fixtures/channels/conversation_start.jsonl --check
make check
```

**Esperado**:

- `--check` termina con 0 hallazgos;
- cada número ficticio nuevo recibe la presentación en su primera respuesta (texto y voz, es y en), y ninguna
  respuesta posterior la repite;
- en `logs/channels.jsonl`, `conversation_start` e `introduced` aparecen solo en los turnos que abren la
  conversación.

Prueba de inactividad sin esperar 12 horas: el guion usa un reloj simulado. También se puede bajar temporalmente
`conversation_idle_hours` a 1 en `config/agent.toml` (sin versionar el cambio).

## 2. En el teléfono (después de reiniciar el backend)

1. Reiniciar el backend y esperar a que `curl.exe http://127.0.0.1:8000/api/health` responda.
2. Desde un número que **nunca** le ha escrito a Valer-IA, enviar «¿Qué produce Manuelita?».

   **Esperado**: saludo y presentación de dos frases como máximo, luego la respuesta con fuentes, en un solo
   mensaje.
3. Desde el mismo número, «¿y en Perú?». **Esperado**: respuesta sin saludo.
4. Desde otro número nuevo, enviar una **nota de voz** con una pregunta.

   **Esperado**: la nota de voz empieza con el saludo y la presentación y cierra con «Te dejo las fuentes por
   escrito.»; el texto trae solo las fuentes.
5. Desde un tercer número nuevo, enviar solo «Hola». **Esperado**: una sola presentación e invitación a
   preguntar, sin doble «Hola».
6. Pedir «empecemos de nuevo y cuéntame de sostenibilidad».

   **Esperado**: «Listo, empezamos de cero», la presentación y la respuesta, una vez cada una.
7. Revisar el registro (sin números ni texto):

   ```powershell
   Get-Content "$env:LOCALAPPDATA\manuelita-rag\logs\channels.jsonl" -Tail 20
   ```

   **Esperado**: `conversation_start` en `first_contact` o `restart`, e `introduced` en `bridge` o `agent`, solo
   en los turnos de apertura.

## 3. Criterios de la spec

| Criterio | Cómo se verifica |
|---|---|
| SC-001, SC-002, SC-004 | `simulate --check` (≥ 10 conversaciones del guion) y pasos 2, 4 y 5 |
| SC-003 | pasos 3 y 6; `introduced` vacío en los turnos siguientes |
| SC-005 | paso 4 |
| SC-006 | prueba con reloj simulado en `test_bridge.py` y en el guion |
