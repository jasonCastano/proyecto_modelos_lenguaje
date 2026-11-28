# Quickstart: validar el estilo caleño (spec 036)

## 1. Sin red

```powershell
uv run pytest tests/unit/agent -k "style or plan or review"
uv run pytest tests/integration/agent -k style
uv run python -m proyecto_modelos_lenguaje.agent converse --style --mode demo
uv run python -m proyecto_modelos_lenguaje.agent converse --focus --mode demo   # regresión spec 035
make check
```

**Esperado**:

- todo en verde;
- `--style` en demo con:
  - ≥ 60 % de uso en los turnos informales o neutros;
  - 0 vetadas;
  - 0 excesos;
  - 0 expresiones en queja, angustia, crisis e inglés;
  - 0 repeticiones seguidas;
  - 100 % de citas conservadas.

## 2. Audición de voces (local, sin red después de descargar el modelo)

```powershell
uv run python -m proyecto_modelos_lenguaje.voice --audition
```

**Esperado**: WAV por cada voz candidata y por cada expresión hablada en `MANUELITA_STATE_DIR/voice_audition/`,
con `index.txt`. El equipo escucha, elige la voz (se actualiza `config/voice.toml`) y marca las expresiones mal
pronunciadas (`spoken = false` en `config/caleno.toml`).

## 3. Con el modelo real (medición SC-001 a SC-006 y SC-008)

```powershell
uv run python -m proyecto_modelos_lenguaje.agent converse --style --mode real
uv run python -m proyecto_modelos_lenguaje.agent converse --mode real            # regresión regla 21
```

**Esperado**:

- las metas del punto 1;
- el juez califica la claridad y el profesionalismo con 4 de 5 o más en promedio;
- la empatía y la naturalidad no bajan respecto a `docs/evaluacion_conversacion.json`.

## 4. En el teléfono y en la web (después de reiniciar el backend)

Conversación de prueba:

1. «Hola»
2. «¿Qué produce Manuelita?»
3. «Uy, qué bacano, ¿y dónde queda?»
4. una nota de voz preguntando por la Fundación Manuelita
5. «¿Qué significa "ve"?»
6. «Buenos días, quisiera información para distribución»
7. «Habla normal, por favor»
8. «Gracias, chao»

**Esperado**:

- expresiones caleñas con medida (como máximo una por mensaje y dos en la nota de voz) y sin voseo;
- explicación breve de «ve»;
- cortesía sobria en el mensaje formal;
- sin expresiones después de «habla normal»;
- citas intactas.

Una persona de Cali califica 5 respuestas (SC-007): «suena caleña» y «suena profesional» en al menos 4.
