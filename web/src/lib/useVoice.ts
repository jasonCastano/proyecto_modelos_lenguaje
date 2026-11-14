import { useCallback, useEffect, useRef, useState } from "react";

import { getVoiceStatus, VoicePlayer, type VoicePlayerOptions } from "./voice";

export const MUTED_KEY = "manuelita.voice.muted";

function readMuted(): boolean {
  try {
    return window.localStorage.getItem(MUTED_KEY) === "1";
  } catch {
    return false; // sin almacenamiento: activada solo en esta sesión
  }
}

function writeMuted(muted: boolean): void {
  try {
    if (muted) window.localStorage.setItem(MUTED_KEY, "1");
    else window.localStorage.removeItem(MUTED_KEY);
  } catch {
    // preferencia solo en memoria
  }
}

export interface VoiceControl {
  /** El servidor tiene voz y el navegador puede reproducir audio. */
  available: boolean;
  /** Motivo legible cuando no hay voz (de `GET /api/voice` o de un 503). */
  detail: string | null;
  muted: boolean;
  speaking: boolean;
  blocked: boolean;
  /** Primer audio por sesión (ms desde que se cerró la primera oración). */
  firstAudio: Record<string, number>;
  toggleMuted(): void;
  stop(): void;
  resume(): void;
  /** Envío de una pregunta (gesto del usuario): corta lo anterior y abre la sesión en vivo. */
  startLive(threadId: string | null): string | null;
  pushToken(text: string): void;
  finishLive(finalAnswer: string | null, threadId: string | null): void;
  /** «Escuchar» una respuesta guardada. */
  speak(text: string, threadId: string | null): string | null;
}

/** Estado de la voz del chat (spec 016, contracts/ui-voice.md). */
export function useVoice(options: Pick<VoicePlayerOptions, "createContext" | "fetcher"> = {}): VoiceControl {
  const [serverAvailable, setServerAvailable] = useState(false);
  const [detail, setDetail] = useState<string | null>(null);
  const [muted, setMuted] = useState(readMuted);
  const [speaking, setSpeaking] = useState(false);
  const [blocked, setBlocked] = useState(false);
  const [firstAudio, setFirstAudio] = useState<Record<string, number>>({});
  const playerRef = useRef<VoicePlayer | null>(null);
  const optionsRef = useRef(options);

  if (!playerRef.current) {
    playerRef.current = new VoicePlayer({
      ...optionsRef.current,
      onSpeaking: setSpeaking,
      onBlocked: setBlocked,
      onFirstAudio: (key, ms) => setFirstAudio((previous) => ({ ...previous, [key]: ms })),
      onUnavailable: (message) => {
        setServerAvailable(false);
        setDetail(message);
      },
    });
  }
  const player = playerRef.current;

  useEffect(() => {
    let active = true;
    void getVoiceStatus()
      .then((status) => {
        if (!active) return;
        setServerAvailable(status?.available === true);
        setDetail(status?.available === true ? null : (status?.detail ?? null));
      })
      .catch(() => {
        if (!active) return;
        setServerAvailable(false);
        setDetail(null);
      });
    return () => {
      active = false;
      player.stop();
    };
  }, [player]);

  const available = serverAvailable && player.supported();
  const enabled = available && !muted;

  const stop = useCallback(() => player.stop(), [player]);

  const toggleMuted = useCallback(() => {
    setMuted((previous) => {
      const next = !previous;
      writeMuted(next);
      if (next) player.stop();
      return next;
    });
  }, [player]);

  const resume = useCallback(() => {
    void player.unlock();
  }, [player]);

  const startLive = useCallback(
    (threadId: string | null) => {
      player.stop();
      if (!enabled) return null;
      void player.unlock();
      return player.start(threadId);
    },
    [enabled, player],
  );

  const pushToken = useCallback(
    (text: string) => {
      if (enabled) player.push(text);
    },
    [enabled, player],
  );

  const finishLive = useCallback(
    (finalAnswer: string | null, threadId: string | null) => {
      if (!enabled || !player.activeKey) return;
      player.setThread(threadId);
      player.finish(finalAnswer);
    },
    [enabled, player],
  );

  const speak = useCallback(
    (text: string, threadId: string | null) => {
      if (!enabled) return null;
      void player.unlock();
      return player.speakText(text, threadId);
    },
    [enabled, player],
  );

  return {
    available,
    detail,
    muted,
    speaking,
    blocked,
    firstAudio,
    toggleMuted,
    stop,
    resume,
    startLive,
    pushToken,
    finishLive,
    speak,
  };
}
