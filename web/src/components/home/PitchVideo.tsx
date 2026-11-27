/**
 * Video pitch de Valer-IA (spec 028, contracts/web-ui.md): lo primero de la entrada. Arranca sin sonido
 * y con subtítulos, se salta en un paso, no se impone dos veces en la misma sesión, respeta el
 * movimiento reducido y, si el video falta, deja la portada y la transcripción. El video se genera
 * fuera de línea con MAGI-2 (`video/pitch/`); la web solo lo sirve.
 */
import { useEffect, useRef, useState } from "react";

import { PITCH_DISCLAIMER, PITCH_TRANSCRIPT, PITCH_VIDEO } from "../../data/pitch";
import { Link } from "../../lib/router";

export const PITCH_SESSION_KEY = "valeria.pitch";
export const PITCH_ERROR = "El video no está disponible; aquí tienes la transcripción.";

type Seen = "visto" | "saltado" | null;

function readSeen(): Seen {
  try {
    const value = window.sessionStorage.getItem(PITCH_SESSION_KEY);
    return value === "visto" || value === "saltado" ? value : null;
  } catch {
    return null;
  }
}

function writeSeen(value: Exclude<Seen, null>) {
  try {
    window.sessionStorage.setItem(PITCH_SESSION_KEY, value);
  } catch {
    // Sin almacenamiento de sesión el video simplemente no se recuerda.
  }
}

function prefersReducedMotion(): boolean {
  return typeof window.matchMedia === "function"
    ? window.matchMedia("(prefers-reduced-motion: reduce)").matches
    : false;
}

export function PitchVideo() {
  const video = useRef<HTMLVideoElement>(null);
  const [initial] = useState<Seen>(readSeen);
  const [reduced] = useState(prefersReducedMotion);
  const [compact, setCompact] = useState(initial !== null);
  const [ended, setEnded] = useState(false);
  const [failed, setFailed] = useState(false);
  const [muted, setMuted] = useState(true);
  const autoplay = initial === null && !reduced;

  useEffect(() => {
    const element = video.current;
    if (!element || !autoplay) return;
    element.muted = true;
    const attempt = element.play?.();
    if (attempt && typeof attempt.catch === "function") attempt.catch(() => undefined);
  }, [autoplay]);

  useEffect(() => {
    const element = video.current;
    return () => element?.pause?.();
  }, []);

  function skip() {
    video.current?.pause?.();
    writeSeen("saltado");
    setCompact(true);
    document.getElementById("hero-title")?.focus();
  }

  function finish() {
    writeSeen("visto");
    setEnded(true);
  }

  function replay() {
    setCompact(false);
    setEnded(false);
    const element = video.current;
    if (!element) return;
    element.currentTime = 0;
    const attempt = element.play?.();
    if (attempt && typeof attempt.catch === "function") attempt.catch(() => undefined);
  }

  function toggleSound() {
    const element = video.current;
    const next = !muted;
    if (element) element.muted = next;
    setMuted(next);
  }

  const openTranscript = reduced || failed;

  return (
    <section
      aria-labelledby="pitch-title"
      className="pitch"
      data-state={compact ? "compact" : "open"}
      data-testid="pitch"
    >
      <div className="pitch__frame">
        <video
          className="pitch__video"
          controls
          muted
          onEnded={finish}
          onError={() => setFailed(true)}
          playsInline
          poster={PITCH_VIDEO.poster}
          preload="metadata"
          ref={video}
          src={PITCH_VIDEO.src}
        >
          <track default kind="captions" label="Español" src={PITCH_VIDEO.captions} srcLang="es" />
        </video>
      </div>
      <div className="pitch__copy">
        <h2 className="pitch__title" id="pitch-title">
          Conoce Valer-IA en un minuto
        </h2>
        <p className="pitch__disclaimer">{PITCH_DISCLAIMER}.</p>
        {failed ? (
          <p className="pitch__error" role="status">
            {PITCH_ERROR}
          </p>
        ) : null}
        <div className="pitch__actions">
          {compact ? (
            <button className="action action--quiet" onClick={replay} type="button">
              Ver el video
            </button>
          ) : (
            <>
              <button className="action action--quiet" onClick={toggleSound} type="button">
                {muted ? "Activar sonido" : "Silenciar"}
              </button>
              <button
                className="action action--quiet"
                data-testid="pitch-skip"
                onClick={skip}
                type="button"
              >
                Saltar el video
              </button>
            </>
          )}
          {ended ? (
            <Link className="action action--primary" to="/agente">
              Empezar con Valer-IA
            </Link>
          ) : null}
        </div>
        <details className="pitch__transcript" open={openTranscript}>
          <summary>Ver la transcripción</summary>
          <ol>
            {PITCH_TRANSCRIPT.map((item) => (
              <li key={item.id}>{item.text}</li>
            ))}
          </ol>
        </details>
      </div>
    </section>
  );
}
