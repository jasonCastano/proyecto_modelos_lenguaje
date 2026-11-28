// Plugin puente de Valer-IA Caña para OpenClaw (spec 024, ADR 0028; voz: spec 028, ADR 0037).
// Cada mensaje entrante ya autenticado se envía al backend FastAPI por loopback; si el backend falla,
// OpenClaw sigue con su agente nativo (modo degradado). Las notas de voz de respuesta se envían con
// el adaptador saliente del canal; si falla, con el CLI de OpenClaw (`message send --media`), sin shell.
// Spec 034: los stickers se envían con `sendSticker` del listener activo de WhatsApp. Spec 037: el listener
// se busca primero en el runtime de canales que el gateway comparte (ver `src/listener.ts`).
import { execFile } from "node:child_process";
import { existsSync, readFileSync, readdirSync } from "node:fs";
import { readFile } from "node:fs/promises";
import { createRequire } from "node:module";
import { homedir } from "node:os";
import { dirname, join } from "node:path";
import { pathToFileURL } from "node:url";

import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";

import {
  VoiceMemory,
  dispatch,
  hasAudio,
  maskDigits,
  resolveConfig,
  type StickerSender,
  voiceCommandArgs,
  voiceKeys,
} from "./src/bridge.ts";
import {
  type ChannelRuntimeLike,
  findWhatsAppListener,
  type WhatsAppListenerLike,
} from "./src/listener.ts";

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
      let timer: ReturnType<typeof setTimeout> | undefined;
      try {
        await Promise.race([
          sending,
          new Promise((_, reject) => {
            timer = setTimeout(() => reject(new Error("tiempo agotado")), VOICE_SEND_TIMEOUT_MS);
          }),
        ]);
      } finally {
        clearTimeout(timer);
      }
      log("valeria-bridge: nota de voz enviada por el adaptador del canal");
      return true;
    } catch (error) {
      log(`valeria-bridge: envío de voz por el adaptador falló (${maskDigits(String(error)).slice(0, 200)}); uso el CLI`);
    }
    sendVoiceNoteViaCli(channel, target, audioPath, log);
    return false; // spec 030: sin confirmación, el texto lleva la respuesta completa
  };
}

/**
 * Spec 034 (vía «import», la última de la spec 037): listener activo desde la API pública del componente
 * instalado. Desde la instancia de este plugin suele devolver `null` (el runtime de OpenClaw está aislado
 * por plugin); se conserva por si una versión futura lo comparte. Nunca lanza.
 */
export async function loadWhatsAppListener(): Promise<WhatsAppListenerLike | null> {
  const state = process.env.OPENCLAW_STATE_DIR || join(homedir(), ".openclaw-valeria");
  const projects = join(state, "npm", "projects");
  try {
    for (const name of readdirSync(projects)) {
      if (!name.startsWith("openclaw-whatsapp")) continue;
      const api = join(projects, name, "node_modules", "@openclaw", "whatsapp", "dist", "light-runtime-api.js");
      if (!existsSync(api)) continue;
      const module = (await import(pathToFileURL(api).href)) as {
        getActiveWebListener?: (accountId?: string) => WhatsAppListenerLike | null;
      };
      const listener = module.getActiveWebListener?.() ?? null;
      if (listener) return listener;
    }
  } catch {
    return null;
  }
  return null;
}

const STICKER_PATCH_MARK = "valeria-sticker v2";

/**
 * Spec 037 (ADR 0039): ¿tiene el componente de WhatsApp instalado el parche `valeria-sticker v2`? Con él, el
 * adaptador de salida envía los `valeria-*.webp` como sticker nativo; sin él, los enviaría como documento.
 */
export function stickerPatchInstalled(): boolean {
  const state = process.env.OPENCLAW_STATE_DIR || join(homedir(), ".openclaw-valeria");
  const projects = join(state, "npm", "projects");
  try {
    for (const name of readdirSync(projects)) {
      if (!name.startsWith("openclaw-whatsapp")) continue;
      const setup = join(projects, name, "node_modules", "@openclaw", "whatsapp", "dist", ".setup");
      if (!existsSync(setup)) continue;
      for (const file of readdirSync(setup)) {
        if (!file.startsWith("send-") || file.startsWith("send-api-") || !file.endsWith(".mjs")) continue;
        if (readFileSync(join(setup, file), "utf8").includes(STICKER_PATCH_MARK)) return true;
      }
    }
  } catch {
    return false;
  }
  return false;
}

/** Spec 037: envía el sticker por el adaptador de salida del canal (la vía de las notas de voz). */
async function sendStickerViaAdapter(
  runtime: PluginRuntimeLike | undefined,
  cfg: unknown,
  target: string,
  stickerPath: string,
): Promise<boolean> {
  const adapter = await runtime?.channel?.outbound?.loadAdapter?.("whatsapp");
  if (!adapter?.sendMedia) return false;
  let timer: ReturnType<typeof setTimeout> | undefined;
  try {
    await Promise.race([
      adapter.sendMedia({
        cfg,
        to: target,
        text: "",
        mediaUrl: stickerPath,
        mediaLocalRoots: [dirname(stickerPath)],
        mediaReadFile: (path: string) => readFile(path),
      }),
      new Promise((_, reject) => {
        timer = setTimeout(() => reject(new Error("tiempo agotado")), VOICE_SEND_TIMEOUT_MS);
      }),
    ]);
  } finally {
    clearTimeout(timer);
  }
  return true;
}

/**
 * Spec 037: emisor de stickers. Con el parche `valeria-sticker v2`, por el adaptador de salida del canal
 * (vía «adaptador»); si no, la cadena de vías de `src/listener.ts`. Guarda la vía que funcionó mientras
 * responda; si falla, la vuelve a buscar en el siguiente intento.
 */
function stickerSender(
  runtime: PluginRuntimeLike | undefined,
  cfg: unknown,
  channelRuntime: ChannelRuntimeLike | undefined,
  log: (message: string) => void,
): StickerSender {
  let cached: { listener: WhatsAppListenerLike; route: string } | null = null;
  let announced = false;
  let patched: boolean | null = null;
  return async (channel, target, stickerPath) => {
    if (channel !== "whatsapp") return { ok: false, reason: "canal-sin-stickers" };
    if (!existsSync(stickerPath)) return { ok: false, reason: "sin-archivo" };
    patched = patched || stickerPatchInstalled();
    if (patched && (await sendStickerViaAdapter(runtime, cfg, target, stickerPath))) {
      return { ok: true, route: "adaptador" };
    }
    if (!cached) {
      const found = await findWhatsAppListener(channelRuntime, { importListener: loadWhatsAppListener });
      if (!found.listener || !found.route) {
        if (!announced) {
          announced = true; // el detalle una sola vez: sin ruido en cada sticker
          log(`valeria-bridge: sin vía de stickers (${found.detail.join("; ")})`);
        }
        return { ok: false, reason: found.reason ?? "sin-listener" };
      }
      cached = { listener: found.listener, route: found.route };
    }
    try {
      const buffer = await readFile(stickerPath);
      await cached.listener.sendSticker?.(target, buffer, { mimetype: "image/webp" });
      return { ok: true, route: cached.route };
    } catch (error) {
      cached = null; // la conexión pudo cambiar: se busca de nuevo la próxima vez
      throw error;
    }
  };
}

/**
 * Spec 037 (T009): deja en el log qué vía de stickers quedó lista. El componente de WhatsApp puede tardar
 * más de un minuto en registrarse y conectar después de este plugin (2026-11-28: 85 s), así que la búsqueda
 * se repite cada 30 s durante 5 minutos y solo informa «sin vía» si al final no la encontró.
 */
const ANNOUNCE_EVERY_MS = 30000;
const ANNOUNCE_TRIES = 10;

function announceStickerRoute(
  runtime: PluginRuntimeLike | undefined,
  channelRuntime: ChannelRuntimeLike | undefined,
  log: (message: string) => void,
) {
  let tries = 0;
  const attempt = async () => {
    tries += 1;
    if (stickerPatchInstalled()) {
      let adapter: OutboundAdapter | undefined;
      try {
        adapter = await runtime?.channel?.outbound?.loadAdapter?.("whatsapp");
      } catch {
        adapter = undefined;
      }
      if (adapter?.sendMedia) {
        log("valeria-bridge: stickers listos vía adaptador (parche valeria-sticker v2)");
        return;
      }
    }
    const found = await findWhatsAppListener(channelRuntime, { importListener: loadWhatsAppListener });
    if (found.route) {
      log(`valeria-bridge: stickers listos vía ${found.route}`);
      return;
    }
    if (tries >= ANNOUNCE_TRIES) {
      log(`valeria-bridge: sin vía de stickers (${found.detail.join("; ")})`);
      return;
    }
    setTimeout(() => void attempt(), ANNOUNCE_EVERY_MS).unref?.();
  };
  setTimeout(() => void attempt(), ANNOUNCE_EVERY_MS).unref?.();
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
    // Spec 037: el runtime de canales que el gateway comparte con los plugins (vía «compartido»).
    const channelRuntime = (api.runtime as { channel?: ChannelRuntimeLike } | undefined)?.channel;
    const runtime = api.runtime as PluginRuntimeLike | undefined;
    const sendSticker = stickerSender(runtime, api.config, channelRuntime, log);
    if (config.stickersDir) announceStickerRoute(runtime, channelRuntime, log);
    // Spec 029: `message_received` (con los adjuntos) se emite antes de `before_dispatch` (sin ellos).
    const voiceMessages = new VoiceMemory();
    api.on("message_received", (event) => {
      if (hasAudio(event.media) || hasAudio(event.originalMedia)) voiceMessages.remember(voiceKeys(event));
    });
    api.on("before_dispatch", async (event) => {
      const voice = await voiceMessages.waitFor(voiceKeys(event));
      return dispatch({ ...event, voice }, config, fetch, log, sendVoiceNote, sendSticker);
    });
  },
});
