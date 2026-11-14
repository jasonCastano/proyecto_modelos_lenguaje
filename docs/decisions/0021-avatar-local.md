# ADR 0021 — Avatar local del agente con sincronización de labios

- **Estado**: aceptada
- **Fecha**: 2026-11-14
- **Autor**: Jason Alejandro Castaño
- **Relacionadas**: ADR 0020 (voz con Phonon); `specs/017-avatar-lipsync/` (spec, plan, research R1–R7, tasks).

## Contexto

Desde la spec 016 el agente habla con la voz «Rebeca», oración por oración, mientras genera la respuesta. El equipo
pidió un avatar que mueva los labios al ritmo de ese audio. Se evaluaron dos caminos:

- **HeyGen**:
  - `heygen-com/skills` son instrucciones para agentes que generan video asíncrono a partir de texto, con renders de
    20 a 45 minutos; no sirven para tiempo real.
  - **LiveAvatar en modo LITE** sí acepta el audio propio en tiempo real, por WebSocket en PCM 16 bits a 24 kHz,
    con video fotorrealista por LiveKit. Cuesta 1 crédito por minuto: el plan gratis trae 10 minutos al mes y el de
    pago, $99.
- **Local**: animar en el navegador una ilustración con el mismo audio que ya se reproduce.

## Decisión

1. **Avatar local e ilustrado**, sin servicios, claves ni red adicionales. El audio no sale del equipo.
2. **Señal**: un `AnalyserNode` de Web Audio, intercalado entre cada oración y los parlantes
   (`source → analyser → destination`). La boca mide exactamente lo que suena; al detener, recibe silencio en el
   siguiente cuadro.
3. **De la señal a la boca** (`web/src/lib/lipsync.ts`, función pura):
   - Volumen con una puerta de ruido en −45 dBFS.
   - Apertura suavizada: ataque de 30 ms y relajación de 55 ms. Cierra en ≤ 150 ms a 60 fps.
   - Cinco formas: cerrada, entreabierta, abierta, redonda y estirada, según la energía en tres bandas cercanas a
     los formantes del español (300–900, 900–1800 y 1800–3500 Hz), con histéresis de 2 cuadros.
   - Los umbrales se calibraron con la voz Rebeca replicando el analizador del navegador, que entrega bytes en
     escala dB. La forma dominante es correcta en el 81 % de los cuadros de «i/e», el 68 % de «o/u» y el 75 % de
     «a».
4. **Dibujo**: un SVG original de una asistente femenina con la paleta de la app.
   - La boca es un único `path` que se interpola; se actualiza por `ref`, sin re-render de React.
   - Respiración, parpadeo irregular (de 2,5 a 6 s) y mirada de «pensando».
   - Respeta `prefers-reduced-motion`; en ese caso solo se mueve la boca.
5. **Estados**: hablando si suena la voz; pensando mientras el chat trabaja o mientras hay voz en cola por sonar;
   reposo en otro caso. El avatar se puede ocultar y la preferencia queda en el navegador.

## Alternativas consideradas

- **HeyGen LiveAvatar LITE**: rechazada por costo, por enviar el audio a la nube y porque la demo dependería de la
  red y de los créditos. El audio de Phonon ya tiene el formato que pide, así que podría volver como un modo
  opcional.
- **Visemas exactos con Rhubarb Lip Sync**: rechazada por ahora. Agrega un binario externo y un análisis por
  oración en el servidor. Es la mejora natural si se quiere cerrar bien la boca en «m», «b» y «p».
- **Sprites PNG, Lottie o Rive**: rechazadas. Son más pesados o suman dependencias, con saltos entre imágenes.
- **Solo volumen**: rechazada. Da una boca que solo abre y cierra, sin formas por vocal.

## Consecuencias

- El avatar no es fotorrealista y la boca sigue el sonido, no fonemas exactos.
- Sin servidor nuevo ni dependencias nuevas: funciona en los modos demo y real y sin conexión.
- Medición en vivo, en Chrome con Phonon: la boca se cierra a los 31 ms de pulsar «Detener», y las transiciones de
  estado son limpias.
- Si la voz está silenciada o no disponible, el avatar sigue mostrando sus estados con la boca cerrada.
