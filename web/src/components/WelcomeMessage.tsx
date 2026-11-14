import { useEffect, useRef, useState } from "react";

import { getWelcome } from "../lib/api";
import { markWelcomed, welcomed } from "../lib/session";
import type { Citation, WelcomeResponse } from "../lib/types";
import type { VoiceControl } from "../lib/useVoice";
import { SourceList } from "./SourceList";

export const FALLBACK_WELCOME = "¡Hola! Soy Valer-IA Caña, la asistente virtual de Manuelita. ¿En qué te ayudo?";

/**
 * Bienvenida de Valer-IA Caña (spec 018, US1): se muestra sin interacción y se dice en voz alta una
 * sola vez por visita. Si el navegador bloquea el audio, suena con el primer gesto del visitante,
 * salvo que ya haya enviado un mensaje.
 */
export function WelcomeMessage({ voice, conversationStarted }: { voice: VoiceControl; conversationStarted: boolean }) {
  const [welcome, setWelcome] = useState<WelcomeResponse | null>(null);
  const [failed, setFailed] = useState(false);
  const started = useRef(conversationStarted);
  started.current = conversationStarted;

  useEffect(() => {
    let active = true;
    void getWelcome()
      .then((data) => {
        if (active) setWelcome(data);
      })
      .catch(() => {
        if (active) setFailed(true);
      });
    return () => {
      active = false;
    };
  }, []);

  const text = welcome?.text ?? (failed ? FALLBACK_WELCOME : null);

  // Voz: una sola vez por visita. Si el navegador bloquea el audio, la lectura queda en cola y
  // arranca con el primer gesto del visitante (el contexto de audio se reanuda dentro del gesto).
  const { available, muted, blocked, speak, resume } = voice;
  useEffect(() => {
    if (!text || !available || muted) return;
    if (!welcomed()) {
      markWelcomed();
      if (!started.current) speak(text, null);
    }
    if (!blocked || started.current) return;
    const onGesture = () => resume();
    window.addEventListener("pointerdown", onGesture, { once: true });
    window.addEventListener("keydown", onGesture, { once: true });
    return () => {
      window.removeEventListener("pointerdown", onGesture);
      window.removeEventListener("keydown", onGesture);
    };
  }, [text, available, muted, blocked, speak, resume]);

  if (!text) return null;
  const citations: Citation[] = (welcome?.citations ?? []).map((citation) => ({
    label: citation.label,
    url: citation.url,
    title: citation.title,
    section_path: [],
    authority: "first_party",
  }));
  return (
    <li className="chat-turn welcome-message" data-kind="welcome" data-testid="welcome-message">
      <div className="answer">
        <p className="answer-body">{text}</p>
        {citations.length > 0 ? <SourceList citations={citations} /> : null}
      </div>
    </li>
  );
}
