import { describe, expect, it } from "vitest";

import {
  type AnalyserLike,
  type AudioFeatures,
  CLOSED_MOUTH,
  LIPSYNC_TUNING,
  mouthFromFeatures,
  mouthGeometry,
  mouthPath,
  type MouthState,
  readFeatures,
} from "../lib/lipsync";

const FRAME = 1000 / 60;
const VOICE: AudioFeatures = { rmsDb: -12, b1: 0.5, b2: 0.5, b3: 0.42 };
const SILENCE: AudioFeatures = { rmsDb: -100, b1: 0, b2: 0, b3: 0 };

function run(features: AudioFeatures, from: MouthState, ms: number): { state: MouthState; at: number[] } {
  let state = from;
  const openings: number[] = [];
  for (let t = 0; t < ms; t += FRAME) {
    state = mouthFromFeatures(features, state, FRAME);
    openings.push(state.openness);
  }
  return { state, at: openings };
}

function msUntil(features: AudioFeatures, from: MouthState, predicate: (state: MouthState) => boolean): number {
  let state = from;
  for (let t = FRAME; t <= 2000; t += FRAME) {
    state = mouthFromFeatures(features, state, FRAME);
    if (predicate(state)) return t;
  }
  return Infinity;
}

describe("mouthFromFeatures", () => {
  it("silencio y ruido bajo la puerta dejan la boca cerrada", () => {
    expect(run(SILENCE, CLOSED_MOUTH, 500).state).toEqual(CLOSED_MOUTH);
    const noise = run({ rmsDb: -50, b1: 0.1, b2: 0.1, b3: 0.1 }, CLOSED_MOUTH, 500).state;
    expect(noise.shape).toBe("closed");
    expect(noise.openness).toBe(0);
  });

  it("abre rápido con voz plena (ataque) y cierra en ≤ 160 ms con silencio (relajación)", () => {
    expect(msUntil(VOICE, CLOSED_MOUTH, (state) => state.openness > 0.9)).toBeLessThanOrEqual(100);
    const open: MouthState = { shape: "open", openness: 1, pending: null };
    expect(msUntil(SILENCE, open, (state) => state.shape === "closed")).toBeLessThanOrEqual(160);
  });

  it("elige la forma por bandas: estirada, redonda o abierta", () => {
    const wide = run({ rmsDb: -12, b1: 0.2, b2: 0.2, b3: 0.5 }, CLOSED_MOUTH, 200).state;
    const round = run({ rmsDb: -12, b1: 0.8, b2: 0.2, b3: 0.05 }, CLOSED_MOUTH, 200).state;
    const open = run({ rmsDb: -12, b1: 0.5, b2: 0.5, b3: 0.42 }, CLOSED_MOUTH, 200).state;
    expect([wide.shape, round.shape, open.shape]).toEqual(["wide", "round", "open"]);
  });

  it("usa entreabierta con poca apertura y cerrada por debajo de 0,08", () => {
    const quiet = run({ rmsDb: -39, b1: 0.5, b2: 0.5, b3: 0.42 }, CLOSED_MOUTH, 500).state;
    expect(quiet.openness).toBeGreaterThanOrEqual(0.08);
    expect(quiet.openness).toBeLessThan(0.3);
    expect(quiet.shape).toBe("half");
  });

  it("aplica histéresis de 2 cuadros entre formas abiertas", () => {
    const open: MouthState = { shape: "open", openness: 0.9, pending: null };
    const wideFeatures: AudioFeatures = { rmsDb: -12, b1: 0.2, b2: 0.2, b3: 0.5 };
    const first = mouthFromFeatures(wideFeatures, open, FRAME);
    expect(first.shape).toBe("open");
    expect(first.pending).toEqual({ shape: "wide", frames: 1 });
    expect(mouthFromFeatures(wideFeatures, first, FRAME).shape).toBe("wide");
    // Un cuadro aislado no cambia la forma
    const back = mouthFromFeatures(VOICE, first, FRAME);
    expect(back.shape).toBe("open");
  });

  it("no muta el estado anterior y mantiene la apertura en [0, 1]", () => {
    const previous: MouthState = { shape: "open", openness: 0.5, pending: { shape: "wide", frames: 1 } };
    const copy = structuredClone(previous);
    mouthFromFeatures({ rmsDb: 20, b1: 9, b2: 9, b3: 9 }, previous, 10_000);
    expect(previous).toEqual(copy);
    const extreme = mouthFromFeatures({ rmsDb: 20, b1: 1, b2: 1, b3: 1 }, previous, 10_000);
    expect(extreme.openness).toBeLessThanOrEqual(1);
    expect(mouthFromFeatures(SILENCE, previous, -5).openness).toBeGreaterThanOrEqual(0);
  });

  it("expone las constantes de ajuste congeladas", () => {
    expect(LIPSYNC_TUNING).toMatchObject({ gateDb: -45, fullDb: -15, attackMs: 30, releaseMs: 55 });
    expect(Object.isFrozen(LIPSYNC_TUNING)).toBe(true);
  });
});

describe("mouthGeometry y mouthPath", () => {
  it("sigue la tabla del modelo de datos con alto proporcional a la apertura", () => {
    expect(mouthGeometry(CLOSED_MOUTH)).toEqual({ width: 28, height: 0, roundness: 0 });
    expect(mouthGeometry({ shape: "half", openness: 1, pending: null })).toMatchObject({ width: 26, height: 6 });
    expect(mouthGeometry({ shape: "open", openness: 0.5, pending: null })).toMatchObject({ width: 26, height: 8 });
    expect(mouthGeometry({ shape: "round", openness: 1, pending: null })).toMatchObject({ width: 16, height: 14 });
    expect(mouthGeometry({ shape: "wide", openness: 1, pending: null })).toMatchObject({ width: 34, height: 8 });
  });

  it("produce un path SVG cerrado y válido", () => {
    const d = mouthPath({ width: 26, height: 16, roundness: 0.5 }, 100, 140);
    expect(d).toMatch(/^M [\d.]+ [\d.]+ Q .+ Z$/);
    expect(d).not.toContain("NaN");
  });
});

describe("readFeatures", () => {
  function analyser(sample: number, bins: (hz: number) => number, sampleRate = 48_000): AnalyserLike {
    const fftSize = 1024;
    return {
      fftSize,
      frequencyBinCount: fftSize / 2,
      getFloatTimeDomainData(array) {
        array.fill(sample);
      },
      getByteFrequencyData(array) {
        for (let index = 0; index < array.length; index += 1) array[index] = bins(index * (sampleRate / fftSize));
      },
    };
  }

  it("calcula el RMS en dBFS y la energía de las tres bandas", () => {
    const features = readFeatures(
      analyser(0.1, (hz) => (hz >= 300 && hz <= 900 ? 255 : 0)),
      48_000,
    );
    expect(features.rmsDb).toBeCloseTo(-20, 1);
    expect(features.b1).toBeGreaterThan(0.9);
    expect(features.b2).toBeLessThan(0.1);
    expect(features.b3).toBe(0);
  });

  it("acota el silencio digital a −100 dBFS", () => {
    expect(readFeatures(analyser(0, () => 0), 48_000)).toEqual({ rmsDb: -100, b1: 0, b2: 0, b3: 0 });
  });
});
