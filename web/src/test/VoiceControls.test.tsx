import { act, render, renderHook, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { VoiceControls } from "../components/VoiceControls";
import { MUTED_KEY, useVoice, type VoiceControl } from "../lib/useVoice";

function control(overrides: Partial<VoiceControl> = {}): VoiceControl {
  return {
    available: true,
    detail: null,
    muted: false,
    speaking: false,
    pending: false,
    blocked: false,
    firstAudio: {},
    toggleMuted: vi.fn(),
    stop: vi.fn(),
    resume: vi.fn(),
    startLive: vi.fn(() => null),
    pushToken: vi.fn(),
    finishLive: vi.fn(),
    speak: vi.fn(() => null),
    analyser: vi.fn(() => null),
    ...overrides,
  };
}

describe("VoiceControls", () => {
  it("el toggle refleja el estado y el botón detener solo aparece mientras suena", async () => {
    const voice = control();
    const { rerender } = render(<VoiceControls voice={voice} showUnavailable />);
    const toggle = screen.getByTestId("voice-toggle");
    expect(toggle).toHaveAttribute("aria-pressed", "true");
    expect(toggle).toHaveTextContent("Voz activada");
    expect(screen.queryByTestId("voice-stop")).not.toBeInTheDocument();

    await userEvent.setup().click(toggle);
    expect(voice.toggleMuted).toHaveBeenCalled();

    rerender(<VoiceControls voice={control({ speaking: true })} showUnavailable />);
    expect(screen.getByTestId("voice-stop")).toBeInTheDocument();
    expect(screen.getByTestId("voice-speaking")).toHaveAttribute("aria-live", "polite");

    rerender(<VoiceControls voice={control({ muted: true })} showUnavailable />);
    expect(screen.getByTestId("voice-toggle")).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByTestId("voice-toggle")).toHaveTextContent("Voz silenciada");
  });

  it("sin voz muestra el aviso y deshabilita el toggle", () => {
    render(
      <VoiceControls
        voice={control({ available: false, detail: "Voz desactivada por configuración." })}
        showUnavailable
      />,
    );
    expect(screen.getByTestId("voice-toggle")).toBeDisabled();
    expect(screen.getByTestId("voice-unavailable")).toHaveTextContent(
      "La voz no está disponible: Voz desactivada por configuración. El chat sigue funcionando por texto.",
    );
  });

  it("si el navegador bloquea el audio ofrece reproducir", async () => {
    const voice = control({ blocked: true });
    render(<VoiceControls voice={voice} showUnavailable />);
    await userEvent.setup().click(screen.getByTestId("voice-resume"));
    expect(voice.resume).toHaveBeenCalled();
  });
});

describe("useVoice: preferencia de silencio", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
    window.localStorage.clear();
  });

  function stubServer() {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(JSON.stringify({ available: true, state: "ready", detail: null }))),
    );
  }

  it("guarda el silencio en localStorage y lo recuerda al remontar", async () => {
    stubServer();
    const options = { createContext: () => null };
    const first = renderHook(() => useVoice(options));
    expect(first.result.current.muted).toBe(false);
    act(() => first.result.current.toggleMuted());
    expect(window.localStorage.getItem(MUTED_KEY)).toBe("1");
    first.unmount();

    const second = renderHook(() => useVoice(options));
    expect(second.result.current.muted).toBe(true);
    act(() => second.result.current.toggleMuted());
    expect(window.localStorage.getItem(MUTED_KEY)).toBeNull();
  });

  it("si localStorage falla, la voz queda activada solo en la sesión", async () => {
    stubServer();
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("bloqueado");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("bloqueado");
    });
    const { result } = renderHook(() => useVoice({ createContext: () => null }));
    expect(result.current.muted).toBe(false);
    act(() => result.current.toggleMuted());
    expect(result.current.muted).toBe(true);
  });

  it("sin AudioContext la voz no está disponible aunque el servidor sí", async () => {
    stubServer();
    const { result } = renderHook(() => useVoice({ createContext: () => null }));
    await waitFor(() => expect(globalThis.fetch).toHaveBeenCalled());
    expect(result.current.available).toBe(false);
  });
});
