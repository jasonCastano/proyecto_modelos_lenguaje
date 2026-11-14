# Research: Avatar del agente con sincronización de labios (spec 017)

Fecha: 2026-11-14. Contexto: la voz de la spec 016 ya reproduce en el navegador un WAV de 24 kHz por oración con Web
Audio (`web/src/lib/voice.ts`, `VoicePlayer.playNext`: `source.connect(context.destination)`).

## R1. Avatar local frente a avatar en la nube

- **Decision**: avatar ilustrado **local**, en el navegador, animado con el audio que ya se reproduce.
- **Rationale**:
  - No suma servicios, claves, costos ni red. El audio no sale del equipo, igual que la voz (FR-008 de esta spec,
    FR-011 de la 016).
  - Funciona en el modo demo y el día de la sustentación sin depender de terceros.
  - La sincronización es exacta por construcción: la boca lee el mismo audio que suena.
- **Alternatives considered**:
  - **HeyGen LiveAvatar, modo LITE**: es fotorrealista y acepta el audio propio por WebSocket en PCM 16 bits a
    24 kHz. Se rechazó porque cuesta 1 crédito por minuto (el plan gratis trae 10 minutos al mes y el de pago
    $99), porque envía el audio a la nube y porque la demo dependería de la red y de los créditos. Puede volver
    como un modo opcional en el futuro.
  - **`heygen-com/skills`**: genera video asíncrono a partir de texto, con renders de 20 a 45 minutos. No sirve
    para tiempo real.
  - **Rhubarb Lip Sync en el servidor**: produce visemas exactos por fonema, pero agrega un binario externo, un
    paso de análisis por oración y latencia. Queda como mejora futura.

## R2. Cómo se obtiene la señal de la voz

- **Decision**: un único `AnalyserNode` por `AudioContext`, intercalado en el grafo de reproducción
  (`source → analyser → destination`). `VoicePlayer` lo crea perezosamente y lo expone con `analyser()`.
- **Rationale**: el analizador mide exactamente lo que suena, después de decodificar y en el reloj del contexto.
  Si se detiene la fuente, el analizador recibe silencio de inmediato. No toca el servidor ni el contrato de
  `/api/tts`.
- **Parámetros**:
  - `fftSize = 1024`: a 48 kHz son ~21 ms por ventana y bins de ~47 Hz.
  - `smoothingTimeConstant = 0.5`.
  - Se usan `getFloatTimeDomainData` para el RMS y `getByteFrequencyData` para las bandas.
- **Alternatives considered**:
  - Calcular la envolvente en el servidor y enviarla junto al WAV: agrega un contrato y no refleja pausas,
    detenciones ni bloqueos del navegador.
  - `AudioWorklet`: es más preciso, pero innecesario a 60 fps y más complejo de probar.

## R3. De la señal a la forma de la boca

- **Decision**: una función pura `mouthFromFeatures(features, previous, dtMs)` en `web/src/lib/lipsync.ts`, con
  dos etapas.
- **Características por cuadro**:
  - `rms` en dBFS.
  - Energía relativa en tres bandas que aproximan los formantes del español: **B1 300–900 Hz** (F1: apertura),
    **B2 900–1800 Hz** (F2 de vocales posteriores) y **B3 1800–3500 Hz** (F2 alto de vocales anteriores y
    sibilantes).
- **Etapa 1, apertura** (`openness` entre 0 y 1):
  - Puerta de ruido en −45 dBFS, con apertura 0 por debajo.
  - Escala lineal entre −45 y −15 dBFS.
  - Suavizado asimétrico: **ataque** τ = 30 ms, **relajación** τ = 55 ms, de modo que el cierre baja de 1 a < 0,08
    en ~150 ms a 60 fps (FR-004, SC-002). Se bajó de 60 a 55 ms al medir la cuantización por cuadros.
- **Etapa 2, forma**, por proporciones de banda y con histéresis de 2 cuadros para evitar parpadeos:
  - `openness < 0.08` → `closed`.
  - `openness < 0.3` → `half`.
  - Si `B3/(B1+B2) > 0.9` → `wide` («e», «i», «s»).
  - Si `B1/(B1+B2+B3) > 0.55` y `B3` es bajo → `round` («o», «u»).
  - En otro caso → `open` («a»).
- **Rationale**: el F1 alto se asocia con bocas abiertas y el F2 alto con labios estirados. Es un modelo simple,
  explicable y comprobable con tonos sintéticos. Los umbrales viven en una sola constante (`LIPSYNC_TUNING`) para
  ajustarlos escuchando a Rebeca.
- **Alternatives considered**:
  - Solo volumen (una boca que abre y cierra): incumple FR-003, que pide 3 formas abiertas.
  - Un clasificador de vocales entrenado: desproporcionado para el alcance.

### Calibración (2026-11-14)

- **Hallazgo**: en la prueba en vivo con Chrome y la voz Rebeca, la forma `wide` salió en solo 29 de ~12.000
  cuadros. `getByteFrequencyData` entrega bytes en **escala dB** (−100 a −30 dB llevados a 0–255), no
  energía lineal, así que las proporciones entre bandas son mucho más bajas que las supuestas.
- **Método**: se replicó el analizador en numpy (ventana Blackman, FFT de 1024 a 48 kHz, suavizado 0,5 y
  bytes en dB) sobre tres frases de Rebeca cargadas de «i/e», «o/u» y «a».
- **Mediciones** (medianas de los cuadros con voz):

  | Vocales | `b3/(b1+b2)` | `b3` |
  |---------|--------------|------|
  | «i/e» | 0,505 | — |
  | «a» | 0,371 | 0,51 |
  | «o/u» | 0,222 | 0,29 |

- **Umbrales elegidos**: `wideRatio = 0.45`, `roundRatio = 0.40`, `roundMaxB3 = 0.38`.
- **Resultado**: forma dominante correcta en el 81 % de los cuadros de «i/e», el 68 % de «o/u» y el 75 % de
  «a». No es un clasificador de fonemas, pero la boca cambia con las vocales.

## R4. Dibujo y animación

- **Decision**: SVG inline en `AgentAvatar.tsx`, una ilustración plana original de una asistente femenina con la
  paleta de `tokens.css` (`--forest`, `--orange`, `--gold`, `--paper`, `--ink`).
  - **La boca** es un único `path` paramétrico: su ancho, alto y redondez se interpolan según la forma y la
    apertura. Así la transición es continua, sin cambiar de imágenes.
  - **Cada cuadro** se aplica por `ref` con `setAttribute` dentro de `requestAnimationFrame`, sin re-render de
    React a 60 fps. El bucle solo corre mientras el estado es «hablando»; el navegador lo pausa en segundo plano.
  - **Reposo y pensando**: animaciones CSS (`@keyframes`) para la respiración (escala de 1 % cada 4 s), el
    parpadeo (con un retardo aleatorio entre 2,5 y 6 s fijado por JS en cada ciclo) y la mirada lateral.
  - **Movimiento reducido**: `@media (prefers-reduced-motion: reduce)` desactiva respiración y mirada, y también
    el parpadeo. La boca sigue funcionando porque es información del habla.
- **Alternatives considered**:
  - Sprites PNG por forma de boca: más pesados, con saltos entre imágenes y sin tematizar.
  - Canvas o WebGL: innecesarios para unas pocas formas.
  - Lottie o Rive: dependencias nuevas.

## R5. Estados del avatar

- **Decision**: `avatarState = speaking ? "speaking" : thinking ? "thinking" : "idle"`.
  - `speaking` sale de `useVoice` (onSpeaking del reproductor).
  - `thinking` es `busy && !speaking` en `ChatView`: entre el envío y el primer audio, o hasta el fin del turno si
    no hay voz.
- **Rationale**: reutiliza los estados existentes sin modificar el flujo del chat. Con la voz silenciada o no
  disponible, `speaking` nunca se activa y la boca queda cerrada (FR-009).

## R6. Visibilidad, diseño y accesibilidad

- **Visibilidad**: `localStorage["manuelita.avatar.hidden"] = "1"` oculta el avatar. Las lecturas y escrituras van
  en `try/catch`, como la preferencia de voz.
- **Diseño**:
  - En escritorio, la tarjeta del avatar mide 160 px y se ubica a la izquierda de la conversación en una
    rejilla de dos columnas.
  - Por debajo de 720 px pasa a una franja compacta de 72 px sobre la conversación, que no flota sobre el campo
    de escritura (FR-012).
- **Accesibilidad**: el SVG lleva `aria-hidden="true"`. El botón «Ocultar avatar» o «Mostrar avatar» es accesible.
  El estado del agente se sigue anunciando por texto con «Leyendo respuesta…» y las etapas del turno (FR-010).

## R7. Pruebas sin red ni audio

- `lipsync.ts` se prueba con características sintéticas:
  - silencio y ruido bajo la puerta → `closed`;
  - energía en B1 → `round` u `open`;
  - energía en B3 → `wide`;
  - ataque y relajación medidos en milisegundos simulados, con cierre < 200 ms;
  - histéresis sin parpadeo.
- `VoicePlayer` usa un `AudioContext` simulado: cada fuente se conecta al analizador y el analizador al destino.
- `AgentAvatar` usa un analizador simulado y `requestAnimationFrame` falso: comprueba los estados, el cierre al
  detener, el movimiento reducido y que el ocultamiento persiste.
- Para la medición en vivo (SC-001), un modo de depuración opcional (`?avatarDebug=1`) muestra la apertura y la
  forma en la tarjeta, para revisar 10 respuestas.
