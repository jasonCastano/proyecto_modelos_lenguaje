// Plugin puente de Valer-IA Caña para OpenClaw (spec 024, ADR 0028; voz: spec 028, ADR 0032).
// Cada mensaje entrante ya autenticado se envía al backend FastAPI por loopback; si el backend falla,
// OpenClaw sigue con su agente nativo (modo degradado). Las notas de voz de respuesta se envían con
// el CLI documentado de OpenClaw (`openclaw message send --media`), sin shell.
import { execFile } from "node:child_process";
import { existsSync } from "node:fs";
import { readFile } from "node:fs/promises";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";

import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";

import {
  VoiceMemory,
  dispatch,
  hasAudio,
  resolveConfig,
  voiceCommandArgs,
  voiceKeys,
} from "./src/bridge.ts";

const VOICE_SEND_TIMEOUT_MS = 30000;
const VOICE_CLI_TIMEOUT_MS = 180000;

/** Ruta de `openclaw.mjs`: OPENCLAW_CLI, el proceso del gateway o el paquete instalado. */
function openclawEntry(): string | null {
  const candidates = [process.env.OPENCLAW_CLI, process.argv[1]];
  try {
    const require = createRequire(import.meta.url);
    candidates.push(join(dirname(require.resolve("openclaw/package.json")), "openclaw.mjs"));
  } catch {
    // el paquete puede no exponer package.json: se usan los otros candidatos
  }
  return candidates.find((path) => path && /openclaw\.mjs$/i.test(path) && existsSync(path)) ?? null;
}

/** Respaldo: el CLI tarda ~46 s en arrancar en este equipo; corre en segundo plano sin frenar el texto. */
function sendVoiceNoteViaCli(
  channel: string,
  target: string,
  audioPath: string,
  log: (message: string) => void,
): void {
  const entry = openclawEntry();
  if (!entry) {
    log("valeria-bridge: no se encontró el CLI de OpenClaw para la nota de voz");
    return;
  }
  const args = [entry, ...voiceCommandArgs(channel, target, audioPath)];
  execFile(
    process.execPath,
    args,
    { timeout: VOICE_CLI_TIMEOUT_MS, windowsHide: true, maxBuffer: 4 * 1024 * 1024 },
    (error, stdout, stderr) => {
      if (!error) {
        log("valeria-bridge: nota de voz enviada por el CLI");
        return;
      }
      // Solo el final de la salida, con los dígitos enmascarados (nunca el número de la persona).
      const tail = [String(stderr), String(stdout)]
        .join("\n")
        .trim()
        .split(/\r?\n/)
        .slice(-4)
        .join(" | ");
      log(`valeria-bridge: la nota de voz por el CLI falló: ${maskDigits(tail).slice(0, 400)}`);
    },
  );
}

function maskDigits(text: string): string {
  return text.replace(/\d{5,}/g, "#");
}

interface OutboundAdapter {
  sendMedia?: (ctx: Record<string, unknown>) => Promise<unknown>;
}

interface PluginRuntimeLike {
  channel?: { outbound?: { loadAdapter?: (id: string) => Promise<OutboundAdapter | undefined> } };
}

/**
 * Spec 029: la nota de voz se envía dentro del gateway con el adaptador de salida del canal
 * (la misma conexión de WhatsApp ya abierta), sin abrir otro proceso. `runtime.gateway.request`
 * no sirve: OpenClaw lo reserva a plugins oficiales.
 */
function voiceSender(runtime: PluginRuntimeLike | undefined, cfg: unknown, log: (message: string) => void) {
  return async (channel: string, target: string, audioPath: string): Promise<boolean> => {
    try {
      const adapter = await runtime?.channel?.outbound?.loadAdapter?.(channel);
      if (!adapter?.sendMedia) throw new Error(`el canal ${channel} no expone sendMedia`);
      voiceCommandArgs(channel, target, audioPath); // valida el destinatario
      const sending = adapter.sendMedia({
        cfg,
        to: target,
        text: "",
        mediaUrl: audioPath,
        mediaLocalRoots: [dirname(audioPath)],
        mediaReadFile: (path: string) => readFile(path),
        audioAsVoice: true,
      });
      await Promise.race([
        sending,
        new Promise((_, reject) => setTimeout(() => reject(new Error("tiempo agotado")), VOICE_SEND_TIMEOUT_MS)),
      ]);
      log("valeria-bridge: nota de voz enviada por el adaptador del canal");
      return true;
    } catch (error) {
      log(`valeria-bridge: envío de voz por el adaptador falló (${maskDigits(String(error)).slice(0, 200)}); uso el CLI`);
    }
    sendVoiceNoteViaCli(channel, target, audioPath, log);
    return false; // spec 030: sin confirmación, el texto lleva la respuesta completa
  };
}

export default definePluginEntry({
  id: "valeria-bridge",
  name: "Puente Valer-IA",
  description: "Envía los mensajes de WhatsApp a Valer-IA Caña (router, memoria, herramientas, citas y voz).",
  register(api) {
    const config = resolveConfig(api.pluginConfig, process.env);
    if (!config.token) {
      api.logger?.warn?.("valeria-bridge: falta VALERIA_CHANNEL_TOKEN; el puente queda inactivo");
      return;
    }
    const log = (message: string) => api.logger?.warn?.(message);
    const sendVoiceNote = voiceSender(api.runtime as PluginRuntimeLike | undefined, api.config, log);
    // Spec 029: `message_received` (con los adjuntos) se emite antes de `before_dispatch` (sin ellos).
    const voiceMessages = new VoiceMemory();
    api.on("message_received", (event) => {
      if (hasAudio(event.media) || hasAudio(event.originalMedia)) voiceMessages.remember(voiceKeys(event));
    });
    api.on("before_dispatch", async (event) => {
      const voice = await voiceMessages.waitFor(voiceKeys(event));
      return dispatch({ ...event, voice }, config, fetch, log, sendVoiceNote);
    });
  },
});
