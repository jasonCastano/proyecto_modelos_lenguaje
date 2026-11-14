# Quickstart: validar el avatar con sincronización de labios (spec 017)

Prerrequisito: la voz de la spec 016 funciona, es decir, `uv run python -m proyecto_modelos_lenguaje.voice --check`
devuelve `ready`. Con `UV_PROJECT_ENVIRONMENT` global apuntando a otro proyecto, antepón
`UV_PROJECT_ENVIRONMENT=.venv`.

## 1. Sin red: lo mismo que corre la CI

```bash
make check                         # incluye lipsync.test.ts, AgentAvatar.test.tsx y la integración con el chat
cd web && npx vitest run src/test/lipsync.test.ts src/test/AgentAvatar.test.tsx
```

**Esperado**:
- todo en verde;
- las pruebas de la boca cubren silencio, cierre en ≤ 160 ms, las formas `round`, `open` y `wide` e histéresis.

## 2. En la app

```bash
make app   # http://127.0.0.1:8000 → pestaña Conversación
```

| Escenario | Pasos | Resultado esperado | Criterio |
|-----------|-------|--------------------|----------|
| Boca sincronizada | Preguntar «¿Qué produce Manuelita?» con la voz activada, en modo demo y en modo real. | La boca se mueve con la voz, se cierra entre oraciones y queda cerrada al final. | US1, SC-001 |
| Cierre inmediato | Pulsar «Detener» mientras habla. | La boca se cierra al instante, en menos de 0,2 s. | FR-004, SC-002 |
| Estados | Dejar la app quieta 10 s, luego enviar una pregunta. | Parpadeo irregular en reposo; mirada de «pensando» mientras genera; boca activa al hablar. | US2 |
| Movimiento reducido | Activar «Reducir movimiento» en el sistema operativo y recargar. | Sin respiración, mirada ni parpadeo; la boca sigue moviéndose al hablar. | FR-006 |
| Teléfono | DevTools con ancho de 375 px. | Franja compacta sobre la conversación; el campo de escritura queda visible. | FR-012 |
| Ocultar | «Ocultar avatar» y recargar. | Sigue oculto y la voz sigue sonando. | FR-007, SC-005 |
| Sin voz | Silenciar la voz, o usar `MANUELITA_VOICE_ENABLED=0`, y preguntar. | «Pensando» y luego reposo, con la boca cerrada; el chat igual que antes. | FR-009, SC-005 |
| Respuesta larga | «Resume la historia de Manuelita» (más de 1 minuto de audio). | Animación fluida durante toda la lectura. | SC-003 |

## 3. Medición de SC-001 (modo de depuración)

1. Abrir `http://127.0.0.1:8000/?avatarDebug=1#/chat`. La tarjeta del avatar muestra «forma · apertura».
2. Hacer 10 preguntas de la rúbrica y observar las pausas entre oraciones: la forma debe pasar a `closed`.
3. Registrar en la sección de resultados cuántas pausas cerraron la boca y cuántos tramos con voz la abrieron.
   Meta: ≥ 90 % en ambos.
4. Si la boca tiembla con el ruido o no cierra, ajustar `LIPSYNC_TUNING` (`gateDb`, `releaseMs`) y repetir.

## 4. Resultados de la validación (2026-11-14)

Equipo: Intel Core i9-12900H, Windows 11, Chrome (Playwright, headless). Voz Rebeca con Phonon y API en modo
real. Las respuestas se escucharon por el analizador real del navegador.

| Comprobación | Resultado |
|--------------|-----------|
| Pruebas sin red | Vitest 87/87 (lip-sync 11, avatar 7, voz con analizador y chat con avatar); pytest 848 pasan; Ruff limpio; `tsc -b` y `vite build` sin errores. |
| Transiciones de estado (3 preguntas) | `idle → thinking → speaking → idle` en cada pregunta, sin pasar por reposo entre pensar y hablar (se añadió `pending` en `useVoice`). |
| Formas de boca al hablar, con los umbrales iniciales | `wide` en solo 29 de ~12.000 cuadros: el analizador entrega bytes en escala dB y los umbrales suponían energía lineal. |
| Calibración (research R3) | Con `wideRatio 0.45`, `roundRatio 0.40` y `roundMaxB3 0.38`, la forma dominante es correcta en 81 % de los cuadros de «i/e», 68 % de «o/u» y 75 % de «a». |
| Formas de boca al hablar, calibradas | 12.495 cuadros: redonda 29 %, estirada 23 %, abierta 19 %, entreabierta 13 % y cerrada 16 %. |
| Cierre al pulsar «Detener» (FR-004, SC-002) | **34 ms** (meta < 200 ms). |
| Teléfono (375 px) | Franja compacta sobre la conversación; el formulario queda visible. |
| Capturas | El avatar en reposo y hablando, revisado visualmente; ilustración original con la paleta de la app. |

**Pendiente de verificación humana**:
- SC-001: boca cerrada en las pausas y abierta con la voz, sobre 10 respuestas con `?avatarDebug=1`.
- SC-004: percepción de sincronía por el equipo.
- SC-003: fluidez en una respuesta de más de 1 minuto, vista en pantalla.

Las pruebas automáticas cubren estos tres criterios con señales sintéticas, pero no reemplazan mirar y escuchar.
