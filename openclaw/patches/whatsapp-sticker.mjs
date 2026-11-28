#!/usr/bin/env node
// Parche «valeria-sticker v2» para @openclaw/whatsapp 2026.11.10 (spec 037, ADR 0040).
//
// El componente de WhatsApp de OpenClaw no puede enviar stickers nativos desde un plugin:
//   - su listener activo no expone `sendSticker` (solo texto, medios, encuestas y reacciones), aunque la
//     API de envío interna sí lo tiene;
//   - el envío de medios clasifica un `.webp` como documento («sticker → document»).
// OpenClaw además aísla el runtime por plugin, así que el plugin `valeria-bridge` no alcanza el listener
// (prueba en vivo del 2026-11-28). Lo que sí alcanza es el adaptador de salida del canal, con el que ya
// envía las notas de voz. El parche hace dos reemplazos anclados:
//   A (listener, monitor-*.mjs): el listener activo expone `sendSticker` de la API de envío.
//   B (envío, send-*.mjs): un medio cuyo archivo es uno de los stickers aprobados de Valer-IA
//     (`…/valeria-<nombre>.webp`) se envía con `sendSticker`; cualquier otro medio sigue igual.
// Es idempotente (marca «valeria-sticker v2»), guarda una copia «*.orig» (si no existe ya), no adivina (si un
// anclaje no aparece exactamente una vez, no escribe nada) y retira el cambio de la versión 1 (símbolo
// global en runtime-*.mjs), que no funcionó porque los plugins no comparten `globalThis`.
//
// Uso:  node openclaw/patches/whatsapp-sticker.mjs [--state-dir <dir>] [--check]
// Salida: 0 aplicado o ya aplicado · 2 componente no instalado · 3 anclaje no encontrado (sin cambios).
// Lo ejecuta scripts/openclaw_env.ps1 -Install; nunca se aplica a mano sobre los archivos instalados.
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";

export const MARK = "/* valeria-sticker v2 */";
export const SUPPORTED_VERSION = "2026.11.10";

// Versión 1 (retirada): se deshace si está presente.
export const V1_MARK = "/* valeria-sticker v1 */";
export const V1_ANCHOR = "const setWhatsAppRuntime = runtimeStore.setRuntime;";
export const V1_REPLACEMENT =
  `const setWhatsAppRuntime = (runtime) => { ${V1_MARK}\n` +
  "\truntimeStore.setRuntime(runtime);\n" +
  '\ttry { if (runtime?.channel) globalThis[Symbol.for("valeria.whatsapp.channelRuntime")] = runtime.channel; } catch {}\n' +
  "};";

export const STICKER_FILE_RE = "/[\\\\/]valeria-[a-z0-9-]+\\.webp$/i";

export const PATCHES = [
  {
    name: "listener",
    match: (name) => name.startsWith("monitor-"),
    anchor: "\t\tsendPoll: sendApi.sendPoll,\n\t\tsendReaction: sendApi.sendReaction\n\t};",
    replacement:
      "\t\tsendPoll: sendApi.sendPoll,\n\t\tsendReaction: sendApi.sendReaction,\n" +
      `\t\tsendSticker: sendApi.sendSticker ${MARK}\n\t};`,
  },
  {
    name: "envio",
    match: (name) => name.startsWith("send-") && !name.startsWith("send-api-"),
    anchor:
      "const accepted = requireWhatsAppAcceptedSendResult(partOptions ? await active.sendMessage(to, part, " +
      "buffer, mime, partOptions) : await active.sendMessage(to, part, buffer, mime));",
    replacement:
      `const valeriaSticker = Boolean(buffer) && typeof active.sendSticker === "function" && ` +
      `typeof primaryMediaUrl === "string" && ${STICKER_FILE_RE}.test(primaryMediaUrl); ${MARK}\n` +
      "\t\t\t\tconst accepted = requireWhatsAppAcceptedSendResult(valeriaSticker ? await active.sendSticker(to, " +
      'buffer, { mimetype: "image/webp" }) : partOptions ? await active.sendMessage(to, part, buffer, mime, ' +
      "partOptions) : await active.sendMessage(to, part, buffer, mime));",
  },
];

function count(text, needle) {
  return text.split(needle).length - 1;
}

/** Instalaciones de @openclaw/whatsapp dentro del estado de OpenClaw de Valer-IA. */
export function findPlugins(stateDir) {
  const projects = path.join(stateDir, "npm", "projects");
  if (!fs.existsSync(projects)) return [];
  return fs
    .readdirSync(projects)
    .filter((name) => name.startsWith("openclaw-whatsapp"))
    .map((name) => path.join(projects, name, "node_modules", "@openclaw", "whatsapp"))
    .filter((dir) => fs.existsSync(path.join(dir, "package.json")));
}

function setupFiles(pluginDir, match) {
  const dir = path.join(pluginDir, "dist", ".setup");
  if (!fs.existsSync(dir)) return [];
  return fs
    .readdirSync(dir)
    .filter((name) => name.endsWith(".mjs") && match(name))
    .map((name) => path.join(dir, name))
    .map((file) => ({ file, text: fs.readFileSync(file, "utf8") }));
}

/** Diagnóstico sin escribir: «parcheado» (las dos partes) o «ausente». */
export function inspectPlugin(pluginDir) {
  const version = JSON.parse(fs.readFileSync(path.join(pluginDir, "package.json"), "utf8")).version;
  const contents = Object.fromEntries(PATCHES.map((p) => [p.name, setupFiles(pluginDir, p.match)]));
  const patched = PATCHES.every((p) => contents[p.name].some(({ text }) => text.includes(MARK)));
  const v1 = setupFiles(pluginDir, (name) => name.startsWith("runtime-")).filter(({ text }) =>
    text.includes(V1_MARK),
  );
  return { state: patched ? "parcheado" : "ausente", version, contents, v1 };
}

/** Retira el cambio de la versión 1 (si está) y aplica las partes que falten de la versión 2. */
export function applyPlugin(pluginDir) {
  const report = inspectPlugin(pluginDir);
  if (report.version !== SUPPORTED_VERSION) {
    if (report.state === "parcheado") return { state: "parcheado" };
    return {
      state: "ausente",
      code: 3,
      error: `versión ${report.version} no soportada por el parche (esperada ${SUPPORTED_VERSION})`,
    };
  }
  const writes = [];
  for (const { file, text } of report.v1) {
    if (count(text, V1_REPLACEMENT) === 1) writes.push({ file, text, patched: text.replace(V1_REPLACEMENT, V1_ANCHOR) });
  }
  for (const patch of PATCHES) {
    const files = report.contents[patch.name];
    if (files.some(({ text }) => text.includes(MARK))) continue;
    const targets = files.filter(({ text }) => count(text, patch.anchor) === 1);
    const total = files.reduce((sum, { text }) => sum + count(text, patch.anchor), 0);
    if (targets.length !== 1 || total !== 1) {
      return { state: "ausente", code: 3, error: `anclaje «${patch.name}» no encontrado exactamente una vez` };
    }
    const { file, text } = targets[0];
    writes.push({ file, text, patched: text.replace(patch.anchor, patch.replacement) });
  }
  if (writes.length === 0) return { state: "parcheado" };
  for (const { file, text, patched } of writes) {
    if (!fs.existsSync(`${file}.orig`)) fs.writeFileSync(`${file}.orig`, text, "utf8");
    fs.writeFileSync(file, patched, "utf8");
  }
  if (inspectPlugin(pluginDir).state !== "parcheado") {
    return { state: "ausente", code: 3, error: "la verificación posterior falló" };
  }
  return { state: "aplicado" };
}

function resolveStateDir(argv) {
  const index = argv.indexOf("--state-dir");
  if (index >= 0 && argv[index + 1]) return argv[index + 1];
  return process.env.OPENCLAW_STATE_DIR || path.join(os.homedir(), ".openclaw-valeria");
}

export function main(argv = process.argv.slice(2)) {
  const check = argv.includes("--check");
  const plugins = findPlugins(resolveStateDir(argv));
  if (plugins.length === 0) {
    console.log("soporte-sticker: sin-plugin");
    console.log("No se encontró @openclaw/whatsapp en el estado de OpenClaw.");
    return 2;
  }
  const results = plugins.map((dir) => (check ? inspectPlugin(dir) : applyPlugin(dir)));
  const bad = results.find((result) => result.state === "ausente");
  const applied = results.some((r) => r.state === "aplicado");
  const state = bad ? "ausente" : applied ? "aplicado" : "parcheado";
  console.log(`soporte-sticker: ${state}`);
  if (bad?.error) console.log(`No se aplicó: ${bad.error}.`);
  else if (bad) console.log("Falta el parche: ejecuta .\\scripts\\openclaw_env.ps1 -Install");
  if (!bad) return 0;
  return bad.code ?? 3;
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  process.exitCode = main();
}
