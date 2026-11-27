# Quickstart: validar la spec 028

Prerrequisitos: Fase A de la spec 024 completa en el portátil servidor, SIM dedicada vinculada
([openclaw-ops.md](contracts/openclaw-ops.md) O1), modelos de voz descargados (es y en) y backend con
`channels.voice_notes = true`.

## 1. Pruebas sin red (cualquier equipo)

```powershell
uv run pytest tests/unit/channels tests/unit/agent/test_planning_activation.py tests/api/test_channels_api.py
cd openclaw/plugins/valeria-bridge; npm test; cd ../../..
uv run python -m proyecto_modelos_lenguaje.mcp_server --list   # exactamente 15 herramientas
make check
```

Esperado: todo en verde; la prueba «sin comandos» recorre los textos del canal y el guion natural.

## 2. Conversación natural sin teléfono

```powershell
uv run pml channels simulate --script tests/fixtures/channels/natural_conversation.jsonl --mode demo
```

Esperado: saludo con presentación natural, cambio de tema, «empecemos de nuevo», «olvida lo que sabes de mí» →
confirmación → «dale», ambigüedad re-preguntada, ningún texto con comandos (SC-004, SC-005).

## 3. Activación del planificador

```powershell
uv run python -m proyecto_modelos_lenguaje.agent evaluate --planning-activation --markdown
```

Esperado: ≥ 14/15 de planificación activadas y ≥ 14/15 parecidas no activadas (SC-007); resultado en
`docs/evaluacion_activacion_planificador.md`.

## 4. Voz en el backend (sin WhatsApp)

```powershell
uv run pml channels simulate --kind audio --text "¿Qué produce Manuelita?" --mode real
uv run pml channels simulate --kind audio --text "What does Manuelita produce?" --mode real
```

Esperado: respuesta con `voice.audio_path` (Ogg/Opus, ≤ 60 s) en el idioma correcto y `messages` con citas y
fuentes; el guion no contiene `[`, `http` ni «Fuentes» (SC-002).

## 5. Extremo a extremo por WhatsApp (modo cerrado)

1. Desde un teléfono de prueba: «hola» → presentación natural en texto.
2. Nota de voz «¿Qué produce Manuelita?» → nota de voz en español + texto con fuentes.
3. Nota de voz en inglés → nota de voz en inglés + texto.
4. «respóndeme por escrito» y otra nota de voz → solo texto.
5. «Tenemos 15 % menos caña esta semana, ¿cómo cumplimos los compromisos?» → planificador con aviso de datos
   sintéticos; «¿y si baja 20 %?» → sigue en planificación.
6. Dos mensajes seguidos rápidos → ambos respondidos en orden.

## 6. Modo abierto y cerrado

```powershell
.\scripts\openclaw_env.ps1 -Mode open     # un teléfono nuevo recibe respuesta (SC-006)
.\scripts\openclaw_env.ps1 -Mode closed   # el mismo teléfono ya no recibe respuesta
```

## 7. Medición de herramientas y prueba con teléfonos ajenos

```powershell
uv run python -m proyecto_modelos_lenguaje.agent evaluate --tools --mode real --markdown
```

Esperado: exactitud ≥ 88,4 % (no baja, regla 21; meta 90 %) y 0 búsquedas en triviales (SC-009). Luego, con el
modo abierto, 10 notas de voz desde teléfonos ajenos (≥ 3 en inglés) con nota de voz y texto con fuentes en < 30 s
el 90 % de las veces (SC-001, SC-003).

## 8. Seguridad

```powershell
git log -p | Select-String -Pattern "\+57\d{10}" -Quiet   # sin coincidencias
```

y el job `secretos` del CI en verde (SC-010).
