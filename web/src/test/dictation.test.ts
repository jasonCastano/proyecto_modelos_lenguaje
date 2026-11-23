import { describe, expect, it } from "vitest";

import {
  DictationError,
  ERROR_MESSAGES,
  EndpointDetector,
  apiErrorCode,
  echoSimilarity,
  encodeWav16k,
  isEcho,
  mediaErrorCode,
} from "../lib/dictation";

// Dictado (spec 023): WAV, fin de habla, guarda de eco y errores (research R5, R6, R10).

function header(buffer: ArrayBuffer) {
  const view = new DataView(buffer);
  const text = (at: number, length: number) =>
    String.fromCharCode(...new Uint8Array(buffer, at, length));
  return {
    riff: text(0, 4),
    wave: text(8, 4),
    format: view.getUint16(20, true),
    channels: view.getUint16(22, true),
    rate: view.getUint32(24, true),
    bits: view.getUint16(34, true),
    data: view.getUint32(40, true),
  };
}

describe("encodeWav16k", () => {
  it("remuestrea 48 kHz a WAV PCM16 mono de 16 kHz", () => {
    const second = new Float32Array(48_000).fill(0.25);
    const buffer = encodeWav16k([second.subarray(0, 24_000), second.subarray(24_000)], 48_000);
    expect(buffer.byteLength).toBe(32_044);
    expect(header(buffer)).toEqual({
      riff: "RIFF",
      wave: "WAVE",
      format: 1,
      channels: 1,
      rate: 16_000,
      bits: 16,
      data: 32_000,
    });
    expect(new DataView(buffer).getInt16(44 + 100, true)).toBe(Math.round(0.25 * 32767));
  });

  it("satura en ±1", () => {
    const buffer = encodeWav16k(new Float32Array([2, -3, 0]), 16_000);
    const view = new DataView(buffer);
    expect(view.getInt16(44, true)).toBe(32767);
    expect(view.getInt16(46, true)).toBe(-32768);
    expect(view.getInt16(48, true)).toBe(0);
  });
});

const QUIET = new Float32Array(960).fill(0.001);
const VOICE = new Float32Array(960).map((_, i) => 0.2 * Math.sin(i / 3));

function feed(detector: EndpointDetector, block: Float32Array, ms: number) {
  let last = detector.push(block, 20);
  for (let elapsed = 20; elapsed < ms; elapsed += 20) last = detector.push(block, 20);
  return last;
}

describe("EndpointDetector", () => {
  const options = { silenceMs: 1500, minSpeechMs: 300, maxSeconds: 60 };

  it("fija el umbral con el ruido de los primeros 300 ms (×3 con mínimo)", () => {
    const detector = new EndpointDetector(options);
    feed(detector, new Float32Array(960).fill(0.01), 300);
    expect(detector.currentThreshold).toBeCloseTo(0.03, 3);
    const quietRoom = new EndpointDetector(options);
    feed(quietRoom, QUIET, 300);
    expect(quietRoom.currentThreshold).toBe(0.015);
  });

  it("no termina sin haber oído al menos min_speech_ms de voz", () => {
    const detector = new EndpointDetector(options);
    feed(detector, QUIET, 300);
    feed(detector, VOICE, 200);
    expect(feed(detector, QUIET, 3000).done).toBeNull();
  });

  it("termina tras silence_ms de silencio después de hablar", () => {
    const detector = new EndpointDetector(options);
    feed(detector, QUIET, 300);
    const speaking = feed(detector, VOICE, 600);
    expect(speaking.speaking).toBe(true);
    expect(speaking.level).toBeGreaterThan(0);
    expect(speaking.level).toBeLessThanOrEqual(100);
    expect(feed(detector, QUIET, 1400).done).toBeNull();
    expect(feed(detector, QUIET, 100).done).toBe("silence");
  });

  it("termina al llegar al límite de duración", () => {
    const detector = new EndpointDetector({ ...options, maxSeconds: 2 });
    feed(detector, QUIET, 300);
    expect(feed(detector, VOICE, 1700).done).toBe("limit");
  });
});

describe("guarda de eco", () => {
  const spoken =
    "Manuelita produce azúcar, etanol y energía en el Valle del Cauca [U1]. También tiene negocios de acuicultura.";

  it("reconoce una transcripción parcial de lo que dijo Valer-IA", () => {
    const heard = "manuelita produce azucar etanol y energia en el valle del cauca";
    expect(echoSimilarity(heard, spoken)).toBeGreaterThan(0.6);
    expect(isEcho(heard, spoken)).toBe(true);
  });

  it("no confunde una pregunta distinta con eco", () => {
    const heard = "¿y cuántos empleados tiene la compañía en Perú?";
    expect(echoSimilarity(heard, spoken)).toBeLessThan(0.3);
    expect(isEcho(heard, spoken)).toBe(false);
    expect(isEcho("¿Qué produce Manuelita?", "Manuelita produce azúcar en el Valle.")).toBe(false);
    expect(isEcho("sí", "sí")).toBe(false);
    expect(isEcho(heard, null)).toBe(false);
  });
});

describe("errores", () => {
  it("traduce los errores del micrófono y del servidor", () => {
    expect(mediaErrorCode({ name: "NotAllowedError" })).toBe("permission");
    expect(mediaErrorCode({ name: "NotFoundError" })).toBe("no_device");
    expect(mediaErrorCode({ name: "OverconstrainedError" })).toBe("no_device");
    expect(mediaErrorCode({ name: "SecurityError" })).toBe("insecure");
    expect(apiErrorCode("stt_busy")).toBe("busy");
    expect(apiErrorCode("stt_unavailable")).toBe("unavailable");
    expect(apiErrorCode("stt_too_large")).toBe("too_long");
    expect(apiErrorCode("network_error")).toBe("network");
    expect(apiErrorCode("stt_error")).toBe("server");
    expect(new DictationError("empty").message).toBe("No te entendí, ¿puedes repetirlo?");
    expect(ERROR_MESSAGES.permission).toContain("permiso para usar el micrófono");
  });
});
