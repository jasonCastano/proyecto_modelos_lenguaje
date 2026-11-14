# Contrato de UI: avatar del agente (spec 017)

## `AgentAvatar`

```tsx
<AgentAvatar
  state="idle" | "thinking" | "speaking"
  analyser={() => ({ node, sampleRate }) | null}
  debug?: boolean          // ?avatarDebug=1: muestra la forma y la apertura
/>
```

| Elemento | `data-testid` | Comportamiento |
|----------|---------------|----------------|
| Contenedor | `agent-avatar` | `data-state` refleja `idle`, `thinking` o `speaking`. |
| SVG | — | `aria-hidden="true"`, `focusable="false"`; ilustración original con la paleta de `tokens.css`. |
| Boca | `avatar-mouth` | `path` cuyo `d` y `data-shape` se actualizan en cada cuadro mientras `state = speaking`; en otro estado vale `closed`. |
| Ojos | `avatar-eyes` | Parpadeo por CSS con un retardo aleatorio de 2,5 a 6 s; en `thinking` se desplazan hacia un lado. |
| Depuración | `avatar-debug` | Solo con `debug`: texto «forma · apertura». |

**Reglas**:
- El bucle de `requestAnimationFrame` empieza al entrar en `speaking` y se cancela al salir. Al salir, la boca se
  fija en `closed` en ese mismo cuadro (FR-004).
- Sin analizador (`analyser()` devuelve `null`), la boca queda cerrada aunque el estado sea `speaking` (FR-009).
- Con `prefers-reduced-motion: reduce` no hay respiración, mirada ni parpadeo, pero la boca sí se mueve al hablar
  (FR-006).
- No hay re-render de React por cuadro: la boca se actualiza con una `ref`.

## Integración en `ChatView`

| Elemento | `data-testid` | Comportamiento |
|----------|---------------|----------------|
| Botón | `avatar-toggle` | «Ocultar avatar» o «Mostrar avatar»; guarda `localStorage["manuelita.avatar.hidden"]` (FR-007). |
| Diseño | — | `≥ 720 px`: rejilla con el avatar de 160 px a la izquierda de la conversación. `< 720 px`: franja compacta de 72 px sobre la conversación, nunca encima del formulario (FR-012). |

- `state = voice.speaking ? "speaking" : busy ? "thinking" : "idle"`.
- Ocultar el avatar no detiene la voz y no cambia el chat (SC-005).
