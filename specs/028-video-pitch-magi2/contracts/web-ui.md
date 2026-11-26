# Contrato: `PitchVideo` en la entrada

## Posición y estructura

- `section[data-testid=pitch]` es el **primer** hijo de `.home`, antes del héroe. Su encabezado visible es
  «Conoce Valer-IA en un minuto».
- Contiene:
  - un `<video>` con `src=/media/pitch-valeria.mp4`, `poster=/media/pitch-valeria.webp`, `muted`, `playsInline`,
    `preload="metadata"` y `controls`;
  - un `<track kind="captions" srclang="es" default>` que apunta a `pitch-valeria.es.vtt`.
- Acciones visibles:
  - «Saltar el video» (`data-testid=pitch-skip`);
  - «Activar sonido» y «Silenciar», que alternan;
  - «Ver la transcripción», un `<details>` con el texto de `web/src/data/pitch.ts`.
- Escritorio (≥ 900 px): el video vertical a la izquierda, con un ancho máximo de 360 px, y a su lado el título, la
  transcripción y la acción. Teléfono: el video arriba, a todo el ancho y con una altura máxima de 70 vh.

## Comportamiento

| Situación | Resultado |
|---|---|
| Primera visita de la sesión, sin movimiento reducido | Intenta reproducir sin sonido; subtítulos visibles |
| Movimiento reducido | No reproduce solo; muestra la portada, el botón «Reproducir» y la transcripción abierta |
| Clic en «Saltar el video» | Pausa, guarda `valeria.pitch=saltado`, mueve el foco al héroe (`#hero-title`) y el bloque pasa a compacto |
| El video termina | Guarda `valeria.pitch=visto` y muestra el enlace «Empezar con Valer-IA» a `/agente` (FR-021) |
| Vuelta a la entrada con `visto` o `saltado` | Bloque compacto: portada pequeña y «Ver el video»; no reproduce solo |
| Error de carga (`error` del `<video>` o 404) | Portada, mensaje «El video no está disponible; aquí tienes la transcripción.» y transcripción abierta. El resto de la entrada no cambia |
| Cambio de área | El componente se desmonta y el video se detiene |

## Accesibilidad

- Todos los controles se usan con el teclado y tienen foco visible (`--focus`).
- Contraste AA, verificado con axe-core sin violaciones serias.
- Sin desplazamiento horizontal de 360 a 1920 px.
- La declaración «Video generado con IA · proyecto académico, no canal oficial de Manuelita» es visible como texto
  junto al video en todos los estados (abierto, compacto y con falla). El video no la lleva grabada.
