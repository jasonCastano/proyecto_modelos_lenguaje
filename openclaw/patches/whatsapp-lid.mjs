#!/usr/bin/env node
// Parche «valeria-lid v1» para @openclaw/whatsapp 2026.11.10 (spec 033, ADR 0039).
//
// WhatsApp puede entregar una cuenta solo con su ID interno («…@lid»), sin número. El componente de
// WhatsApp de OpenClaw descarta esos mensajes (los deja en reintentos con «LID identity unavailable») y,
// al enviar, convierte un «…@lid» en un número falso «+<lid>». El parche hace dos reemplazos anclados:
//   A (entrada, monitor-*.mjs): sin número, usa remoteJidAlt o el propio «…@lid» como identidad.
//   B (salida, normalize-target-*.mjs): conserva «<lid>@lid» como destino.
// Es idempotente (marca «valeria-lid v1»), guarda una copia «*.orig», no adivina (si un anclaje no
// aparece exactamente una vez, no escribe nada) y se aparta si el componente ya lo soporta de forma nativa.
//
// Uso:  node openclaw/patches/whatsapp-lid.mjs [--state-dir <dir>] [--check]
// Lo ejecuta scripts/openclaw_env.ps1 -Install; nunca se aplica a mano sobre los archivos instalados.
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";

export const MARK = "/* valeria-lid v1 */";
export const SUPPORTED_VERSION = "2026.11.10";
export const LID_THROW = 'throw new Error("WhatsApp inbound LID identity unavailable")';

export const PATCHES = [
  {
    name: "entrada",
    prefix: "monitor-",
    anchor: "const from = group ? remoteJid : await socketSession.resolveInboundJid(remoteJid);",
    replacement:
      "const from = group ? remoteJid : (await socketSession.resolveInboundJid(remoteJid)) ?? " +
      "(msg.key?.remoteJidAlt ? await socketSession.resolveInboundJid(msg.key.remoteJidAlt) : null) ?? " +
      "(/^\\d+@(lid|hosted\\.lid)$/.test(remoteJid) ? remoteJid : null); " +
      MARK,
  },
  {
    name: "salida",
    prefix: "normalize-target-",
    anchor: "\tconst phone = extractUserJidPhone(candidate);\n\tif (phone) {",
    replacement:
      `\tconst lidTarget = candidate.match(WHATSAPP_LID_RE); ${MARK}\n` +
      "\tif (lidTarget) return `${lidTarget[1]}@lid`;\n" +
      "\tconst phone = extractUserJidPhone(candidate);\n\tif (phone) {",
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

function setupFiles(pluginDir, prefix) {
  const dir = path.join(pluginDir, "dist", ".setup");
  if (!fs.existsSync(dir)) return [];
  return fs
    .readdirSync(dir)
    .filter((name) => name.startsWith(prefix) && name.endsWith(".mjs"))
    .map((name) => path.join(dir, name));
}

/** Diagnóstico sin escribir: «parcheado», «nativo» o «ausente» (con detalle). */
export function inspectPlugin(pluginDir) {
  const version = JSON.parse(fs.readFileSync(path.join(pluginDir, "package.json"), "utf8")).version;
  const contents = Object.fromEntries(
    PATCHES.map((patch) => [
      patch.name,
      setupFiles(pluginDir, patch.prefix).map((file) => ({
        file,
        text: fs.readFileSync(file, "utf8"),
      })),
    ]),
  );
  const patched = PATCHES.every((patch) => contents[patch.name].some(({ text }) => text.includes(MARK)));
  const throws = contents.entrada.some(({ text }) => text.includes(LID_THROW));
  if (patched) return { state: "parcheado", version, contents };
  if (!throws && !contents.entrada.some(({ text }) => text.includes(MARK))) {
    return { state: "nativo", version, contents };
  }
  return { state: "ausente", version, contents };
}

/** Aplica los reemplazos pendientes; valida todos los anclajes antes de escribir el primero. */
export function applyPlugin(pluginDir) {
  const report = inspectPlugin(pluginDir);
  if (report.state !== "ausente") return { state: report.state, detail: "" };
  if (report.version !== SUPPORTED_VERSION) {
    return {
      state: "ausente",
      error: `versión ${report.version} no soportada por el parche (esperada ${SUPPORTED_VERSION})`,
    };
  }
  const writes = [];
  for (const patch of PATCHES) {
    const files = report.contents[patch.name];
    if (files.some(({ text }) => text.includes(MARK))) continue;
    const targets = files.filter(({ text }) => count(text, patch.anchor) === 1);
    const total = files.reduce((sum, { text }) => sum + count(text, patch.anchor), 0);
    if (targets.length !== 1 || total !== 1) {
      return { state: "ausente", error: `anclaje «${patch.name}» no encontrado exactamente una vez` };
    }
    const { file, text } = targets[0];
    writes.push({ file, text, patched: text.replace(patch.anchor, patch.replacement) });
  }
  for (const { file, text, patched } of writes) {
    if (!fs.existsSync(`${file}.orig`)) fs.writeFileSync(`${file}.orig`, text, "utf8");
    fs.writeFileSync(file, patched, "utf8");
  }
  const after = inspectPlugin(pluginDir);
  if (after.state !== "parcheado") return { state: "ausente", error: "la verificación posterior falló" };
  return { state: "aplicado", detail: "" };
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
    console.log("soporte-lid: sin-plugin");
    console.log("No se encontró @openclaw/whatsapp en el estado de OpenClaw.");
    return 1;
  }
  const results = plugins.map((dir) => (check ? inspectPlugin(dir) : applyPlugin(dir)));
  const bad = results.find((result) => result.state === "ausente");
  const state = bad ? "ausente" : results.some((r) => r.state === "aplicado") ? "aplicado" : results[0].state;
  console.log(`soporte-lid: ${state}`);
  if (bad?.error) console.log(`No se aplicó: ${bad.error}.`);
  else if (bad) console.log("Falta el parche: ejecuta .\\scripts\\openclaw_env.ps1 -Install");
  return bad ? 1 : 0;
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  process.exitCode = main();
}
