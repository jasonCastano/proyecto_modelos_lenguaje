import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { DictationEngine } from "../lib/useDictation";
import {
  STT_READY,
  installMedia,
  murmur,
  quiet,
  speak,
  sttFetch,
  uninstallMedia,
} from "./mediaMocks";

// Máquina de estados del dictado en manos libres (spec 023, research R10, data-model §6).

function engineWith(now: { value: number }) {
  const env = {
    voiceStop: vi.fn(),
    threadId: () => null,
    onTranscript: vi.fn(),
    status: () => STT_READY,
    lastSpoken: () => "Manuelita produce azúcar en el Valle del Cauca.",
    now: () => now.value,
  };
  return { engine: new DictationEngine(env), env };
}

async function settle(engine: DictationEngine, state: string) {
  await vi.waitFor(() => expect(engine.getSnapshot().state).toBe(state));
}

describe("DictationEngine en manos libres", () => {
  beforeEach(() => {
    installMedia();
    window.localStorage.clear();
    vi.stubGlobal("fetch", sttFetch({}));
  });

  afterEach(() => {
    uninstallMedia();
    vi.restoreAllMocks();
  });

  it("hablar encima de Valer-IA la interrumpe y se escucha al visitante", async () => {
    const { engine, env } = engineWith({ value: 0 });
    engine.setHandsfree(true);
    await settle(engine, "listening");
    engine.update(false, true); // Valer-IA empieza a hablar
    expect(engine.getSnapshot().state).toBe("speaking");
    murmur(600); // eco residual: no supera el umbral de interrupción (×2)
    expect(env.voiceStop).toHaveBeenCalledTimes(1); // solo la llamada de start()
    speak(300); // voz del visitante sostenida ≥ 250 ms
    expect(env.voiceStop).toHaveBeenCalledTimes(2);
    expect(engine.getSnapshot().state).toBe("listening");
    quiet(1500);
    await vi.waitFor(() => expect(env.onTranscript).toHaveBeenCalledTimes(1));
    expect(env.onTranscript.mock.calls[0][1].handsfree).toBe(true);
    engine.dispose();
  });

  it("tras enviar espera la respuesta y vuelve a escuchar cuando termina", async () => {
    const now = { value: 0 };
    const { engine, env } = engineWith(now);
    engine.setHandsfree(true);
    await settle(engine, "listening");
    quiet(300);
    speak(500);
    quiet(1500);
    await settle(engine, "waiting_reply");
    expect(env.onTranscript).toHaveBeenCalledTimes(1);
    speak(500); // mientras espera la respuesta no graba
    engine.update(true, false); // petición en curso
    expect(engine.getSnapshot().state).toBe("waiting_reply");
    engine.update(false, true); // la respuesta suena
    expect(engine.getSnapshot().state).toBe("speaking");
    engine.update(false, false); // terminó
    expect(engine.getSnapshot().state).toBe("listening");
    engine.dispose();
  });

  it("si no llega respuesta, vuelve a escuchar pasado el margen", async () => {
    const now = { value: 0 };
    const { engine } = engineWith(now);
    engine.setHandsfree(true);
    await settle(engine, "listening");
    quiet(300);
    speak(500);
    quiet(1500);
    await settle(engine, "waiting_reply");
    engine.update(false, false);
    expect(engine.getSnapshot().state).toBe("waiting_reply");
    now.value = 3500;
    engine.update(false, false);
    expect(engine.getSnapshot().state).toBe("listening");
    engine.dispose();
  });

  it("desactivar manos libres libera el micrófono", async () => {
    const media = installMedia();
    const { engine } = engineWith({ value: 0 });
    engine.setHandsfree(true);
    await settle(engine, "listening");
    engine.setHandsfree(false);
    expect(engine.getSnapshot().state).toBe("idle");
    expect(media.stopped()).toBe(1);
    expect(window.localStorage.getItem("manuelita.stt.handsfree")).toBe("0");
  });
});
