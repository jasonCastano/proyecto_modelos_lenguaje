import { act, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AgentAvatar, nextBlinkDelay } from "../components/AgentAvatar";
import type { AnalyserLike } from "../lib/lipsync";
import type { VoiceAnalyser } from "../lib/voice";

/** Analizador simulado: `level` controla el volumen; las bandas favorecen una forma abierta. */
function fakeAnalyser() {
  const control = { level: 0 };
  const node: AnalyserLike = {
    fftSize: 1024,
    frequencyBinCount: 512,
    getFloatTimeDomainData(array) {
      array.fill(control.level);
    },
    getByteFrequencyData(array) {
      const binHz = 48_000 / 1024;
      for (let index = 0; index < array.length; index += 1) {
        const hz = index * binHz;
        array[index] = control.level > 0 && hz >= 300 && hz <= 1800 ? 200 : 0;
      }
    },
  };
  const source: VoiceAnalyser = { node, sampleRate: 48_000 };
  return { control, analyser: () => source };
}

/** `requestAnimationFrame` controlable: cada `step()` avanza un cuadro de ~16,7 ms. */
function fakeFrames() {
  let now = 0;
  let callbacks: Array<(time: number) => void> = [];
  const cancel = vi.fn((_id: number) => undefined);
  vi.stubGlobal("requestAnimationFrame", (callback: (time: number) => void) => {
    callbacks.push(callback);
    return callbacks.length;
  });
  vi.stubGlobal("cancelAnimationFrame", cancel);
  vi.spyOn(performance, "now").mockImplementation(() => now);
  const step = (frames = 1) => {
    for (let index = 0; index < frames; index += 1) {
      now += 1000 / 60;
      const pending = callbacks;
      callbacks = [];
      act(() => pending.forEach((callback) => callback(now)));
    }
  };
  return { step, cancel };
}

function mouth() {
  return screen.getByTestId("avatar-mouth");
}

describe("AgentAvatar", () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("mueve la boca con la voz y la cierra con el silencio", () => {
    const frames = fakeFrames();
    const { control, analyser } = fakeAnalyser();
    render(<AgentAvatar analyser={analyser} state="speaking" />);
    const closedPath = mouth().getAttribute("d");

    control.level = 0.3; // ~ −10 dBFS
    frames.step(8);
    expect(["open", "round", "wide"]).toContain(mouth().getAttribute("data-shape"));
    expect(mouth().getAttribute("d")).not.toBe(closedPath);

    control.level = 0;
    frames.step(10);
    expect(mouth().getAttribute("data-shape")).toBe("closed");
  });

  it("al dejar de hablar cierra la boca en el mismo cuadro y cancela el bucle", () => {
    const frames = fakeFrames();
    const { control, analyser } = fakeAnalyser();
    const { rerender } = render(<AgentAvatar analyser={analyser} state="speaking" />);
    control.level = 0.3;
    frames.step(8);
    expect(mouth().getAttribute("data-shape")).not.toBe("closed");

    rerender(<AgentAvatar analyser={analyser} state="idle" />);
    expect(mouth().getAttribute("data-shape")).toBe("closed");
    expect(frames.cancel).toHaveBeenCalled();
    expect(screen.getByTestId("agent-avatar")).toHaveAttribute("data-state", "idle");
  });

  it("sin analizador la boca queda cerrada aunque hable", () => {
    const frames = fakeFrames();
    render(<AgentAvatar analyser={() => null} state="speaking" />);
    frames.step(10);
    expect(mouth().getAttribute("data-shape")).toBe("closed");
  });

  it("es decorativo para lectores de pantalla y muestra la depuración si se pide", () => {
    fakeFrames();
    const { container } = render(<AgentAvatar analyser={() => null} debug state="idle" />);
    const svg = container.querySelector("svg");
    expect(svg).toHaveAttribute("aria-hidden", "true");
    expect(svg).toHaveAttribute("focusable", "false");
    expect(screen.getByTestId("avatar-debug")).toHaveTextContent("closed · 0.00");
  });

  it("parpadea a intervalos irregulares entre 2,5 y 6 s", () => {
    fakeFrames();
    expect(nextBlinkDelay(() => 0)).toBe(2500);
    expect(nextBlinkDelay(() => 1)).toBe(6000);
    vi.spyOn(Math, "random").mockReturnValue(0); // próximo parpadeo a los 2,5 s
    render(<AgentAvatar analyser={() => null} state="idle" />);
    const eyes = screen.getByTestId("avatar-eyes");
    act(() => vi.advanceTimersByTime(2400));
    expect(eyes).toHaveAttribute("data-blinking", "false");
    act(() => vi.advanceTimersByTime(100));
    expect(eyes).toHaveAttribute("data-blinking", "true");
    act(() => vi.advanceTimersByTime(200));
    expect(eyes).toHaveAttribute("data-blinking", "false");
  });

  it("al pensar mira hacia un lado", () => {
    fakeFrames();
    const { rerender } = render(<AgentAvatar analyser={() => null} state="idle" />);
    expect(screen.getByTestId("avatar-pupils")).not.toHaveClass("avatar-pupils--aside");
    rerender(<AgentAvatar analyser={() => null} state="thinking" />);
    expect(screen.getByTestId("avatar-pupils")).toHaveClass("avatar-pupils--aside");
    expect(screen.getByTestId("agent-avatar")).toHaveAttribute("data-state", "thinking");
  });

  it("con movimiento reducido no parpadea pero la boca sigue la voz", () => {
    vi.stubGlobal("matchMedia", (query: string) => ({
      matches: query.includes("reduce"),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }));
    const frames = fakeFrames();
    const { control, analyser } = fakeAnalyser();
    render(<AgentAvatar analyser={analyser} state="speaking" />);
    expect(screen.getByTestId("agent-avatar")).toHaveAttribute("data-reduced-motion", "true");
    act(() => vi.advanceTimersByTime(10_000));
    expect(screen.getByTestId("avatar-eyes")).toHaveAttribute("data-blinking", "false");
    control.level = 0.3;
    frames.step(8);
    expect(mouth().getAttribute("data-shape")).not.toBe("closed");
  });
});
