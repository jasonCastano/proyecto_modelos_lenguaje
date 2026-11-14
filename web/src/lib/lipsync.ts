/**
 * Sincronización de labios del avatar (spec 017, data-model.md, contracts/lipsync.md).
 *
 * En cada cuadro se mide el audio que suena (volumen y energía en tres bandas cercanas a los
 * formantes del español) y se decide la forma de la boca. Todo es determinista y puro salvo
 * `readFeatures`, que solo lee el analizador.
 */

export type MouthShape = "closed" | "half" | "open" | "round" | "wide";

export interface AudioFeatures {
  /** RMS del dominio temporal en dBFS (acotado a −100). */
  rmsDb: number;
  /** Energía media normalizada (0–1) en 300–900 Hz (F1: apertura). */
  b1: number;
  /** Energía media normalizada (0–1) en 900–1800 Hz (F2 de vocales posteriores). */
  b2: number;
  /** Energía media normalizada (0–1) en 1800–3500 Hz (F2 alto y sibilantes). */
  b3: number;
}

export interface MouthState {
  shape: MouthShape;
  /** Apertura suavizada en [0, 1]. */
  openness: number;
  /** Histéresis: forma abierta candidata y cuántos cuadros seguidos lleva. */
  pending: { shape: MouthShape; frames: number } | null;
}

export interface MouthGeometry {
  width: number;
  height: number;
  roundness: number;
}

/** Subconjunto de `AnalyserNode` que se usa (simulable en pruebas). */
export interface AnalyserLike {
  fftSize: number;
  frequencyBinCount: number;
  getFloatTimeDomainData(array: Float32Array): void;
  getByteFrequencyData(array: Uint8Array): void;
}

/**
 * Umbrales calibrados el 2026-11-14 con la voz Rebeca replicando el analizador del navegador (bytes en
 * escala dB): «i/e» → estirada 81 %, «o/u» → redonda 68 %, «a» → abierta 75 % de los cuadros con voz.
 */
export const LIPSYNC_TUNING = Object.freeze({
  gateDb: -45,
  fullDb: -15,
  attackMs: 30,
  releaseMs: 55,
  wideRatio: 0.45,
  roundRatio: 0.4,
  roundMaxB3: 0.38,
  hysteresisFrames: 2,
});

export const CLOSED_MOUTH: MouthState = Object.freeze({ shape: "closed", openness: 0, pending: null });

const BANDS: ReadonlyArray<readonly [number, number]> = [
  [300, 900],
  [900, 1800],
  [1800, 3500],
];
const EPSILON = 1e-6;

const buffers = new WeakMap<AnalyserLike, { time: Float32Array; freq: Uint8Array }>();

function buffersFor(analyser: AnalyserLike) {
  let entry = buffers.get(analyser);
  if (!entry || entry.time.length !== analyser.fftSize || entry.freq.length !== analyser.frequencyBinCount) {
    entry = { time: new Float32Array(analyser.fftSize), freq: new Uint8Array(analyser.frequencyBinCount) };
    buffers.set(analyser, entry);
  }
  return entry;
}

/** Lee el analizador y devuelve las características del cuadro. */
export function readFeatures(analyser: AnalyserLike, sampleRate: number): AudioFeatures {
  const { time, freq } = buffersFor(analyser);
  analyser.getFloatTimeDomainData(time);
  analyser.getByteFrequencyData(freq);
  let sum = 0;
  for (const sample of time) sum += sample * sample;
  const rms = Math.sqrt(sum / Math.max(1, time.length));
  const rmsDb = rms > 0 ? Math.max(-100, 20 * Math.log10(rms)) : -100;
  const binHz = sampleRate / analyser.fftSize;
  const [b1, b2, b3] = BANDS.map(([low, high]) => {
    const from = Math.max(0, Math.round(low / binHz));
    const to = Math.min(freq.length - 1, Math.round(high / binHz));
    if (to < from) return 0;
    let total = 0;
    for (let index = from; index <= to; index += 1) total += freq[index];
    return total / ((to - from + 1) * 255);
  });
  return { rmsDb, b1, b2, b3 };
}

function targetOpenness(rmsDb: number): number {
  const { gateDb, fullDb } = LIPSYNC_TUNING;
  if (rmsDb <= gateDb) return 0;
  return Math.min(1, Math.max(0, (rmsDb - gateDb) / (fullDb - gateDb)));
}

function openShape(features: AudioFeatures): MouthShape {
  const { b1, b2, b3 } = features;
  if (b3 / (b1 + b2 + EPSILON) > LIPSYNC_TUNING.wideRatio) return "wide";
  if (b1 / (b1 + b2 + b3 + EPSILON) > LIPSYNC_TUNING.roundRatio && b3 < LIPSYNC_TUNING.roundMaxB3) {
    return "round";
  }
  return "open";
}

/** Siguiente estado de la boca; determinista y sin mutar `previous`. */
export function mouthFromFeatures(features: AudioFeatures, previous: MouthState, dtMs: number): MouthState {
  const target = targetOpenness(features.rmsDb);
  const tau = target > previous.openness ? LIPSYNC_TUNING.attackMs : LIPSYNC_TUNING.releaseMs;
  const alpha = 1 - Math.exp(-Math.max(0, dtMs) / tau);
  const openness = Math.min(1, Math.max(0, previous.openness + (target - previous.openness) * alpha));
  if (openness < 0.08) return { shape: "closed", openness, pending: null };
  if (openness < 0.3) return { shape: "half", openness, pending: null };
  const candidate = openShape(features);
  if (candidate === previous.shape) return { shape: candidate, openness, pending: null };
  const opening = previous.shape === "closed" || previous.shape === "half";
  const frames = previous.pending?.shape === candidate ? previous.pending.frames + 1 : 1;
  if (opening || frames >= LIPSYNC_TUNING.hysteresisFrames) {
    return { shape: candidate, openness, pending: null };
  }
  return { shape: previous.shape, openness, pending: { shape: candidate, frames } };
}

const GEOMETRY: Record<MouthShape, MouthGeometry> = {
  closed: { width: 28, height: 0, roundness: 0 },
  half: { width: 26, height: 6, roundness: 0.3 },
  open: { width: 26, height: 16, roundness: 0.5 },
  round: { width: 16, height: 14, roundness: 1 },
  wide: { width: 34, height: 8, roundness: 0.2 },
};

/** Geometría objetivo: alto efectivo = alto máximo × apertura. */
export function mouthGeometry(state: MouthState): MouthGeometry {
  const base = GEOMETRY[state.shape];
  return { width: base.width, height: base.height * state.openness, roundness: base.roundness };
}

/** Interpola dos geometrías (para transiciones suaves entre cuadros). */
export function lerpGeometry(from: MouthGeometry, to: MouthGeometry, amount: number): MouthGeometry {
  const t = Math.min(1, Math.max(0, amount));
  return {
    width: from.width + (to.width - from.width) * t,
    height: from.height + (to.height - from.height) * t,
    roundness: from.roundness + (to.roundness - from.roundness) * t,
  };
}

function fixed(value: number): string {
  return (Math.round(value * 100) / 100).toString();
}

/**
 * `d` de la boca centrada en (cx, cy): labio superior e inferior como curvas cuadráticas. Con alto 0
 * es una línea con sonrisa leve; la redondez acerca los controles al centro (boca de «o»).
 */
export function mouthPath(geometry: MouthGeometry, cx: number, cy: number): string {
  const half = geometry.width / 2;
  const smile = 1.5 * (1 - geometry.roundness);
  const left = cx - half;
  const right = cx + half;
  const top = cy - geometry.height * 0.35 - smile * 0.3;
  const bottom = cy + geometry.height * 0.65 + smile;
  const spread = half * (1 - 0.45 * geometry.roundness);
  return [
    `M ${fixed(left)} ${fixed(cy)}`,
    `Q ${fixed(cx - spread * 0.2)} ${fixed(top)} ${fixed(cx)} ${fixed(top)}`,
    `Q ${fixed(cx + spread * 0.2)} ${fixed(top)} ${fixed(right)} ${fixed(cy)}`,
    `Q ${fixed(cx)} ${fixed(bottom + geometry.height * 0.35)} ${fixed(left)} ${fixed(cy)}`,
    "Z",
  ].join(" ");
}
