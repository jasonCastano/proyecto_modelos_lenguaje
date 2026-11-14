import { useEffect, useRef, useState } from "react";

import {
  CLOSED_MOUTH,
  lerpGeometry,
  mouthFromFeatures,
  mouthGeometry,
  mouthPath,
  type MouthGeometry,
  type MouthState,
  readFeatures,
} from "../lib/lipsync";
import type { VoiceAnalyser } from "../lib/voice";

export type AvatarState = "idle" | "thinking" | "speaking";

const MOUTH_X = 100;
const MOUTH_Y = 128;
/** Interpolación por cuadro del ancho y la redondez (el alto sigue a la apertura sin retraso). */
const SHAPE_LERP = 0.35;
const BLINK_MIN_MS = 2500;
const BLINK_MAX_MS = 6000;
const BLINK_MS = 140;

function prefersReducedMotion(): boolean {
  try {
    return typeof window.matchMedia === "function"
      ? window.matchMedia("(prefers-reduced-motion: reduce)").matches
      : false;
  } catch {
    return false;
  }
}

function useReducedMotion(): boolean {
  const [reduced, setReduced] = useState(prefersReducedMotion);
  useEffect(() => {
    if (typeof window.matchMedia !== "function") return;
    const query = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => setReduced(query.matches);
    query.addEventListener?.("change", update);
    return () => query.removeEventListener?.("change", update);
  }, []);
  return reduced;
}

/** Retardo del próximo parpadeo, entre 2,5 y 6 s (irregular). */
export function nextBlinkDelay(random: () => number = Math.random): number {
  return BLINK_MIN_MS + random() * (BLINK_MAX_MS - BLINK_MIN_MS);
}

/**
 * Avatar del agente (spec 017, contracts/ui-avatar.md). Ilustración original; la boca sigue el
 * audio que suena mediante el analizador de la voz. Decorativo para tecnologías de asistencia.
 */
export function AgentAvatar({
  state,
  analyser,
  debug = false,
}: {
  state: AvatarState;
  analyser: () => VoiceAnalyser | null;
  debug?: boolean;
}) {
  const mouthRef = useRef<SVGPathElement>(null);
  const debugRef = useRef<HTMLSpanElement>(null);
  const reduced = useReducedMotion();
  const [blinking, setBlinking] = useState(false);

  // Boca: bucle por cuadro solo mientras habla; fuera de ese estado queda cerrada.
  useEffect(() => {
    const mouth = mouthRef.current;
    if (!mouth) return;
    const paint = (current: MouthState, geometry: MouthGeometry) => {
      mouth.setAttribute("d", mouthPath(geometry, MOUTH_X, MOUTH_Y));
      mouth.setAttribute("data-shape", current.shape);
      if (debugRef.current) {
        debugRef.current.textContent = `${current.shape} · ${current.openness.toFixed(2)}`;
      }
    };
    const close = () => paint(CLOSED_MOUTH, mouthGeometry(CLOSED_MOUTH));
    if (state !== "speaking") {
      close();
      return;
    }
    let frame = 0;
    let last = performance.now();
    let current: MouthState = CLOSED_MOUTH;
    let geometry = mouthGeometry(CLOSED_MOUTH);
    const tick = (now: number) => {
      const source = analyser();
      const dt = Math.max(0, now - last);
      last = now;
      current = source
        ? mouthFromFeatures(readFeatures(source.node, source.sampleRate), current, dt)
        : CLOSED_MOUTH;
      const target = mouthGeometry(current);
      const blended = lerpGeometry(geometry, target, SHAPE_LERP);
      geometry = { ...blended, height: target.height };
      paint(current, geometry);
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => {
      cancelAnimationFrame(frame);
      close();
    };
  }, [state, analyser]);

  // Parpadeo irregular (no con movimiento reducido).
  useEffect(() => {
    if (reduced) {
      setBlinking(false);
      return;
    }
    let timer = setTimeout(function blink() {
      setBlinking(true);
      timer = setTimeout(() => {
        setBlinking(false);
        timer = setTimeout(blink, nextBlinkDelay());
      }, BLINK_MS);
    }, nextBlinkDelay());
    return () => clearTimeout(timer);
  }, [reduced]);

  return (
    <div
      className="agent-avatar"
      data-reduced-motion={reduced ? "true" : "false"}
      data-state={state}
      data-testid="agent-avatar"
    >
      <svg aria-hidden="true" className="avatar-figure" focusable="false" viewBox="0 0 200 200">
        <circle className="avatar-bg" cx="100" cy="100" r="96" />
        {/* Cabello (detrás) */}
        <path
          className="avatar-hair"
          d="M44 104 C40 56 70 30 102 30 C136 30 162 56 158 104 C160 132 154 160 146 176 L54 176 C46 160 40 132 44 104 Z"
        />
        {/* Cuello y hombros */}
        <path className="avatar-skin" d="M86 146 L114 146 L116 170 L84 170 Z" />
        <path className="avatar-blouse" d="M40 200 C44 172 66 162 100 162 C134 162 156 172 160 200 Z" />
        <path className="avatar-scarf" d="M80 164 C90 176 110 176 120 164 L114 160 C106 168 94 168 86 160 Z" />
        {/* Cara */}
        <ellipse className="avatar-skin" cx="100" cy="100" rx="42" ry="50" />
        <path
          className="avatar-hair"
          d="M58 92 C60 62 80 48 104 48 C126 48 142 62 144 86 C128 74 110 66 92 66 C80 70 66 80 58 92 Z"
        />
        {/* Cejas */}
        <path className="avatar-brow" d="M74 84 Q84 79 93 83" />
        <path className="avatar-brow" d="M107 83 Q116 79 126 84" />
        {/* Ojos */}
        <g
          className={`avatar-eyes${blinking ? " avatar-eyes--blink" : ""}`}
          data-blinking={blinking ? "true" : "false"}
          data-testid="avatar-eyes"
        >
          <ellipse className="avatar-eye-white" cx="84" cy="98" rx="8" ry="6" />
          <ellipse className="avatar-eye-white" cx="116" cy="98" rx="8" ry="6" />
          <g
            className={`avatar-pupils${state === "thinking" ? " avatar-pupils--aside" : ""}`}
            data-testid="avatar-pupils"
          >
            <circle className="avatar-pupil" cx="84" cy="98" r="3.6" />
            <circle className="avatar-pupil" cx="116" cy="98" r="3.6" />
          </g>
        </g>
        {/* Mejillas y nariz */}
        <circle className="avatar-cheek" cx="74" cy="116" r="6" />
        <circle className="avatar-cheek" cx="126" cy="116" r="6" />
        <path className="avatar-nose" d="M100 104 Q97 114 101 116" />
        {/* Boca */}
        <path
          className="avatar-mouth"
          d={mouthPath(mouthGeometry(CLOSED_MOUTH), MOUTH_X, MOUTH_Y)}
          data-shape="closed"
          data-testid="avatar-mouth"
          ref={mouthRef}
        />
      </svg>
      {debug ? (
        <span className="avatar-debug" data-testid="avatar-debug" ref={debugRef}>
          closed · 0.00
        </span>
      ) : null}
    </div>
  );
}
