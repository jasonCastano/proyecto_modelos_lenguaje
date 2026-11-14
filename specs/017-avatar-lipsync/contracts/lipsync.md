# Contrato de módulos: lip-sync (spec 017)

## `web/src/lib/lipsync.ts` (funciones puras, salvo `readFeatures`)

```ts
export type MouthShape = "closed" | "half" | "open" | "round" | "wide";
export interface AudioFeatures { rmsDb: number; b1: number; b2: number; b3: number }
export interface MouthState { shape: MouthShape; openness: number; pending: { shape: MouthShape; frames: number } | null }
export interface MouthGeometry { width: number; height: number; roundness: number }

export const LIPSYNC_TUNING: Readonly<{ gateDb; fullDb; attackMs; releaseMs; wideRatio; roundRatio; roundMaxB3; hysteresisFrames }>;
export const CLOSED_MOUTH: MouthState;

/** Lee el analizador (dominio temporal y frecuencia) y devuelve las características del cuadro. */
export function readFeatures(analyser: AnalyserLike, sampleRate: number): AudioFeatures;

/** Siguiente estado de la boca; determinista para las mismas entradas. */
export function mouthFromFeatures(features: AudioFeatures, previous: MouthState, dtMs: number): MouthState;

/** Geometría objetivo de una forma con su apertura (tabla de data-model.md). */
export function mouthGeometry(state: MouthState): MouthGeometry;

/** `d` del path SVG de la boca centrada en (cx, cy). */
export function mouthPath(geometry: MouthGeometry, cx: number, cy: number): string;
```

`AnalyserLike` es el subconjunto de `AnalyserNode` que se usa: `fftSize`, `frequencyBinCount`,
`getFloatTimeDomainData(Float32Array)` y `getByteFrequencyData(Uint8Array)`. Así se puede simular en las pruebas.

**Garantías**:
- `mouthFromFeatures` no muta `previous`.
- Con `rmsDb ≤ gateDb` sostenido, la forma llega a `closed` en ≤ 160 ms simulados.
- `openness` siempre queda en [0, 1].

## `web/src/lib/voice.ts` (cambio compatible)

- `AudioContextLike` agrega `sampleRate: number` y `createAnalyser(): AnalyserLike & { connect(dest): unknown }`.
- `VoicePlayer.analyser(): { node: AnalyserLike; sampleRate: number } | null`:
  - crea perezosamente un único analizador por contexto, con `fftSize` 1024 y `smoothingTimeConstant` 0,5;
  - lo conecta a `destination`;
  - devuelve `null` si no hay `AudioContext` o si `createAnalyser` falla.
- `playNext` conecta cada fuente al analizador (`source.connect(analyser)`). Si no hay analizador, la conecta a
  `destination`, como hoy.
- Ninguna otra API pública cambia.

## `web/src/lib/useVoice.ts` (cambio compatible)

`VoiceControl` agrega `analyser(): { node: AnalyserLike; sampleRate: number } | null`. `speaking` ya existe.
