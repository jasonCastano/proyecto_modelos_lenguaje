import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { MicButton } from "../components/MicButton";
import type { InputMeta, SttStatus } from "../lib/types";
import { useDictation } from "../lib/useDictation";
import {
  STT_READY,
  installMedia,
  quiet,
  speak,
  sttFetch,
  sttPosts,
  sttResult,
  uninstallMedia,
} from "./mediaMocks";

// Micrófono del chat (spec 023, contracts/ui.md): permiso, estados, errores y privacidad.

function Harness({
  onTranscript,
  stop,
}: {
  onTranscript: (text: string, meta: InputMeta) => void;
  stop: () => void;
}) {
  const dictation = useDictation({
    voice: { stop, speaking: false },
    threadId: "t-1",
    busy: false,
    lastSpoken: null,
    onTranscript,
  });
  return <MicButton dictation={dictation} />;
}

function setup(status: SttStatus | (() => SttStatus) = STT_READY, transcribe?: () => Response) {
  const fetchMock = sttFetch({ status, transcribe });
  vi.stubGlobal("fetch", fetchMock);
  const onTranscript = vi.fn();
  const stop = vi.fn();
  render(<Harness onTranscript={onTranscript} stop={stop} />);
  return { fetchMock, onTranscript, stop };
}

async function ready() {
  await waitFor(() => expect(screen.getByTestId("mic-privacy")).toBeInTheDocument());
}

async function listen(user = userEvent.setup()) {
  await user.click(screen.getByTestId("mic-button"));
  await waitFor(() => expect(screen.getByTestId("mic-status")).toHaveTextContent("Escuchando…"));
  return user;
}

describe("MicButton", () => {
  let media: ReturnType<typeof installMedia>;

  beforeEach(() => {
    media = installMedia();
  });

  afterEach(() => {
    uninstallMedia();
    vi.restoreAllMocks();
  });

  it("no aparece si el navegador no permite el micrófono", () => {
    uninstallMedia();
    vi.stubGlobal("fetch", sttFetch({}));
    render(<Harness onTranscript={vi.fn()} stop={vi.fn()} />);
    expect(screen.queryByTestId("mic-button")).not.toBeInTheDocument();
  });

  it("pide el permiso solo al pulsar y escucha con nivel y cancelar", async () => {
    const { stop } = setup();
    await ready();
    expect(media.getUserMedia).not.toHaveBeenCalled();
    await listen();
    expect(media.getUserMedia).toHaveBeenCalledTimes(1);
    expect(stop).toHaveBeenCalled(); // FR-013: corta la voz de Valer-IA
    const button = screen.getByTestId("mic-button");
    expect(button).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByTestId("mic-cancel")).toBeVisible();
    act(() => {
      quiet(300);
      speak(200);
    });
    await waitFor(() =>
      expect(Number(screen.getByTestId("mic-level").getAttribute("aria-valuenow"))).toBeGreaterThan(0),
    );
    expect(screen.getByTestId("mic-level")).toHaveAttribute("role", "meter");
  });

  it("al terminar transcribe y entrega el texto con sus metadatos", async () => {
    const { fetchMock, onTranscript } = setup();
    await ready();
    const user = await listen();
    act(() => {
      quiet(300);
      speak(600);
    });
    await user.click(screen.getByTestId("mic-button"));
    await waitFor(() => expect(onTranscript).toHaveBeenCalledTimes(1));
    const [text, meta] = onTranscript.mock.calls[0];
    expect(text).toBe("¿Qué produce Manuelita?");
    expect(meta).toEqual({ source: "voice", audio_ms: 2040, stt_ms: 451, edited: false, handsfree: false });
    const [, init] = sttPosts(fetchMock)[0];
    expect((init?.headers as Record<string, string>)["Content-Type"]).toBe("audio/wav");
    expect((init?.headers as Record<string, string>)["X-Thread-Id"]).toBe("t-1");
    expect(media.stopped()).toBe(1); // el micrófono se libera
  });

  it("termina solo tras el silencio", async () => {
    const { onTranscript } = setup();
    await ready();
    await listen();
    act(() => {
      quiet(300);
      speak(500);
      quiet(1500);
    });
    await waitFor(() => expect(onTranscript).toHaveBeenCalledTimes(1));
  });

  it("cancelar o cambiar de pestaña no transcribe nada", async () => {
    const { fetchMock, onTranscript } = setup();
    await ready();
    const user = await listen();
    act(() => speak(500));
    await user.click(screen.getByTestId("mic-cancel"));
    expect(screen.getByTestId("mic-button")).toHaveAttribute("aria-pressed", "false");

    await listen(user);
    act(() => speak(500));
    Object.defineProperty(document, "visibilityState", { value: "hidden", configurable: true });
    act(() => {
      document.dispatchEvent(new Event("visibilitychange"));
    });
    Object.defineProperty(document, "visibilityState", { value: "visible", configurable: true });
    await waitFor(() =>
      expect(screen.getByTestId("mic-button")).toHaveAttribute("aria-pressed", "false"),
    );
    expect(sttPosts(fetchMock)).toHaveLength(0);
    expect(onTranscript).not.toHaveBeenCalled();
  });

  it("muestra la nota de privacidad del servidor", async () => {
    setup();
    await ready();
    expect(screen.getByTestId("mic-privacy")).toHaveTextContent("el audio no se guarda");
  });
});

describe("MicButton: errores y disponibilidad (US2)", () => {
  afterEach(() => {
    uninstallMedia();
    vi.restoreAllMocks();
  });

  it.each([
    ["NotAllowedError", "Necesito permiso para usar el micrófono"],
    ["NotFoundError", "No encontré un micrófono conectado"],
  ])("%s → mensaje claro y el chat sigue", async (name, text) => {
    installMedia(name);
    setup();
    await ready();
    await userEvent.setup().click(screen.getByTestId("mic-button"));
    await waitFor(() => expect(screen.getByTestId("mic-status")).toHaveTextContent(text));
    expect(screen.getByTestId("mic-status")).toHaveAttribute("data-kind", "error");
    expect(screen.getByTestId("mic-button")).toBeEnabled();
  });

  async function dictate(transcribe: () => Response, status: SttStatus = STT_READY) {
    installMedia();
    const handles = setup(status, transcribe);
    await ready();
    const user = await listen();
    act(() => {
      quiet(300);
      speak(600);
    });
    await user.click(screen.getByTestId("mic-button"));
    return handles;
  }

  it("sin voz reconocible pide repetir y no entrega texto", async () => {
    const { onTranscript } = await dictate(
      () => new Response(JSON.stringify(sttResult("", { empty: true })), { status: 200 }),
    );
    await waitFor(() =>
      expect(screen.getByTestId("mic-status")).toHaveTextContent("No te entendí, ¿puedes repetirlo?"),
    );
    expect(onTranscript).not.toHaveBeenCalled();
  });

  it("servidor ocupado", async () => {
    await dictate(
      () =>
        new Response(
          JSON.stringify({
            error: { code: "stt_busy", message: "ocupado", retryable: true, action: "reintentar" },
          }),
          { status: 503 },
        ),
    );
    await waitFor(() =>
      expect(screen.getByTestId("mic-status")).toHaveTextContent("El dictado está ocupado"),
    );
  });

  it("sin red", async () => {
    installMedia();
    const fetchMock = sttFetch({});
    fetchMock.mockImplementation(async (_url: string, init?: RequestInit) => {
      if (init?.method === "POST") throw new TypeError("Failed to fetch");
      return new Response(JSON.stringify(STT_READY), { status: 200 });
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<Harness onTranscript={vi.fn()} stop={vi.fn()} />);
    await ready();
    const user = await listen();
    act(() => {
      quiet(300);
      speak(600);
    });
    await user.click(screen.getByTestId("mic-button"));
    await waitFor(() =>
      expect(screen.getByTestId("mic-status")).toHaveTextContent("No pude convertir tu voz en texto"),
    );
  });

  it("al llegar al límite entrega lo reconocido y avisa", async () => {
    installMedia();
    const { onTranscript } = setup({ ...STT_READY, max_seconds: 1 });
    await ready();
    await listen();
    act(() => {
      quiet(300);
      speak(700);
    });
    await waitFor(() => expect(onTranscript).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(screen.getByTestId("mic-status")).toHaveTextContent("límite de 60 segundos"));
  });

  it("sin dictado en el servidor el botón queda deshabilitado con su motivo", async () => {
    installMedia();
    setup({ ...STT_READY, available: false, state: "unavailable", detail: "Modelo no instalado." });
    await waitFor(() => expect(screen.getByTestId("mic-button")).toBeDisabled());
    expect(screen.getByTestId("mic-button")).toHaveAttribute("title", "Modelo no instalado.");
    expect(screen.getByTestId("mic-status")).toHaveTextContent("Modelo no instalado.");
  });

  it("mientras el modelo carga muestra que se prepara y vuelve a consultar", async () => {
    installMedia();
    let calls = 0;
    const { fetchMock } = setup(() => {
      calls += 1;
      return calls === 1 ? { ...STT_READY, state: "loading" } : STT_READY;
    });
    await waitFor(() =>
      expect(screen.getByTestId("mic-status")).toHaveTextContent("Preparando el micrófono…"),
    );
    await waitFor(
      () => expect(screen.getByTestId("mic-status")).not.toHaveTextContent("Preparando"),
      { timeout: 4500 },
    );
    expect(fetchMock.mock.calls.filter((call) => !call[1]?.method).length).toBeGreaterThanOrEqual(2);
  });
});
