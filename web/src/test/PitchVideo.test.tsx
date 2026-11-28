import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { PITCH_ERROR, PITCH_SESSION_KEY, PitchVideo } from "../components/home/PitchVideo";
import { PITCH_TRANSCRIPT } from "../data/pitch";
import { resetPlatform } from "../lib/platform";
import { Home } from "../pages/Home";

let play: ReturnType<typeof vi.fn>;
let pause: ReturnType<typeof vi.fn>;

function reducedMotion(matches: boolean) {
  vi.stubGlobal("matchMedia", (query: string) => ({
    matches: matches && query.includes("reduce"),
    media: query,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
  }));
}

beforeEach(() => {
  window.sessionStorage.clear();
  window.history.replaceState(null, "", "/");
  resetPlatform();
  play = vi.fn().mockResolvedValue(undefined);
  pause = vi.fn();
  Object.defineProperty(HTMLMediaElement.prototype, "play", { configurable: true, value: play });
  Object.defineProperty(HTMLMediaElement.prototype, "pause", { configurable: true, value: pause });
  reducedMotion(false);
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

function videoOf(container: HTMLElement): HTMLVideoElement {
  return container.querySelector("video") as HTMLVideoElement;
}

describe("PitchVideo (spec 028, US1)", () => {
  it("es el primer elemento de la entrada", () => {
    const { container } = render(<Home />);
    const first = container.querySelector("section")!;
    expect(first).toHaveAttribute("id", "inicio");
    expect(within(first).getByTestId("pitch")).toBeInTheDocument();
    expect(container.querySelectorAll("video")).toHaveLength(1);
  });

  it("arranca sin sonido, en línea, con portada y subtítulos en español", () => {
    const { container } = render(<PitchVideo />);
    const video = videoOf(container);
    expect(video.muted).toBe(true);
    expect(video).toHaveAttribute("playsinline");
    expect(video).toHaveAttribute("preload", "metadata");
    expect(video).toHaveAttribute("poster", "/media/pitch-valeria.webp");
    const track = container.querySelector("track")!;
    expect(track).toHaveAttribute("kind", "captions");
    expect(track).toHaveAttribute("srclang", "es");
    expect(track).toHaveAttribute("default");
    expect(play).toHaveBeenCalledTimes(1);
  });

  it("declara que es IA y proyecto académico como texto visible", () => {
    const { container } = render(<PitchVideo />);
    const note = container.querySelector(".pitch__disclaimer")!;
    expect(note).toBeVisible();
    expect(note).toHaveTextContent(/Video generado con IA/);
    expect(note).toHaveTextContent(/no un canal oficial de Manuelita/);
  });

  it("al terminar ofrece empezar con Valer-IA y lo recuerda en la sesión", () => {
    const { container } = render(<PitchVideo />);
    fireEvent.ended(videoOf(container));
    expect(screen.getByRole("link", { name: "Empezar con Valer-IA" })).toHaveAttribute("href", "/agente");
    expect(window.sessionStorage.getItem(PITCH_SESSION_KEY)).toBe("visto");
  });

  it("la transcripción tiene los seis bloques del guion", () => {
    render(<PitchVideo />);
    const details = screen.getByText("Ver la transcripción").closest("details")!;
    expect(within(details).getAllByRole("listitem")).toHaveLength(PITCH_TRANSCRIPT.length);
    expect(PITCH_TRANSCRIPT).toHaveLength(6);
  });
});

describe("PitchVideo (spec 028, US2)", () => {
  it("saltar pausa, recuerda la sesión, compacta y lleva el foco al héroe", async () => {
    const { container } = render(<Home />);
    await userEvent.click(screen.getByTestId("pitch-skip"));
    expect(pause).toHaveBeenCalled();
    expect(window.sessionStorage.getItem(PITCH_SESSION_KEY)).toBe("saltado");
    expect(container.querySelector('[data-testid="pitch"]')).toHaveAttribute("data-state", "compact");
    expect(document.activeElement).toHaveAttribute("id", "hero-title");
  });

  it("si ya se vio en la sesión queda compacto y no se reproduce solo", () => {
    window.sessionStorage.setItem(PITCH_SESSION_KEY, "visto");
    render(<PitchVideo />);
    expect(screen.getByTestId("pitch")).toHaveAttribute("data-state", "compact");
    expect(screen.getByRole("button", { name: "Ver el video" })).toBeInTheDocument();
    expect(play).not.toHaveBeenCalled();
  });

  it("«Ver el video» lo vuelve a reproducir", async () => {
    window.sessionStorage.setItem(PITCH_SESSION_KEY, "saltado");
    render(<PitchVideo />);
    await userEvent.click(screen.getByRole("button", { name: "Ver el video" }));
    expect(play).toHaveBeenCalledTimes(1);
    expect(screen.getByTestId("pitch")).toHaveAttribute("data-state", "open");
  });

  it("con movimiento reducido no arranca solo y abre la transcripción", () => {
    reducedMotion(true);
    render(<PitchVideo />);
    expect(play).not.toHaveBeenCalled();
    expect(screen.getByText("Ver la transcripción").closest("details")).toHaveAttribute("open");
  });

  it("si el video falla muestra el aviso y la transcripción", () => {
    const { container } = render(<PitchVideo />);
    fireEvent.error(videoOf(container));
    expect(screen.getByRole("status")).toHaveTextContent(PITCH_ERROR);
    expect(screen.getByText("Ver la transcripción").closest("details")).toHaveAttribute("open");
  });

  it("activar sonido y silenciar alternan", async () => {
    const { container } = render(<PitchVideo />);
    await userEvent.click(screen.getByRole("button", { name: "Activar sonido" }));
    expect(videoOf(container).muted).toBe(false);
    await userEvent.click(screen.getByRole("button", { name: "Silenciar" }));
    expect(videoOf(container).muted).toBe(true);
  });

  it("funciona aunque el almacenamiento de sesión falle", async () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("bloqueado");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("bloqueado");
    });
    render(<PitchVideo />);
    await userEvent.click(screen.getByTestId("pitch-skip"));
    expect(screen.getByTestId("pitch")).toHaveAttribute("data-state", "compact");
  });

  it("se detiene al salir de la entrada", () => {
    const { unmount } = render(<PitchVideo />);
    unmount();
    expect(pause).toHaveBeenCalled();
  });
});

describe("PitchVideo: sonido con la primera interacción (2026-11-27)", () => {
  it("el primer clic en cualquier parte activa el sonido y reinicia el video", () => {
    const { container } = render(
      <div>
        <p>Otro contenido</p>
        <PitchVideo />
      </div>,
    );
    const video = videoOf(container);
    video.currentTime = 3;
    fireEvent.pointerDown(screen.getByText("Otro contenido"));
    expect(video.muted).toBe(false);
    expect(video.currentTime).toBe(0);
    expect(play).toHaveBeenCalledTimes(2);
    expect(screen.getByRole("button", { name: "Silenciar" })).toBeInTheDocument();
  });

  it("solo la primera interacción cuenta: después respeta el silencio elegido", async () => {
    const { container } = render(<PitchVideo />);
    fireEvent.keyDown(document.body, { key: "Tab" });
    expect(videoOf(container).muted).toBe(false);
    await userEvent.click(screen.getByRole("button", { name: "Silenciar" }));
    fireEvent.pointerDown(document.body);
    expect(videoOf(container).muted).toBe(true);
  });

  it("«Saltar el video» como primera interacción no activa el sonido", async () => {
    const { container } = render(<PitchVideo />);
    await userEvent.click(screen.getByTestId("pitch-skip"));
    expect(videoOf(container).muted).toBe(true);
  });

  it("si el video no arranca solo, la primera interacción no lo hace sonar", () => {
    window.sessionStorage.setItem(PITCH_SESSION_KEY, "visto");
    const { container } = render(<PitchVideo />);
    fireEvent.pointerDown(document.body);
    expect(videoOf(container).muted).toBe(true);
    expect(play).not.toHaveBeenCalled();
  });
});

describe("PitchVideo: lo que desarma la primera interacción", () => {
  it("después de saltar, un clic en la página no reanuda ni hace sonar el video", async () => {
    const { container } = render(<PitchVideo />);
    await userEvent.click(screen.getByTestId("pitch-skip"));
    play.mockClear();
    fireEvent.pointerDown(document.body);
    expect(videoOf(container).muted).toBe(true);
    expect(play).not.toHaveBeenCalled();
  });
});
