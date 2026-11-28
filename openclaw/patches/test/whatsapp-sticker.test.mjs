// Pruebas del parche valeria-sticker v2 (spec 037, T012): `node --test openclaw/patches/test`.
// Trabajan sobre copias mínimas de `monitor-*.mjs`, `send-*.mjs` y `runtime-*.mjs` con los anclajes textuales
// reales; nunca tocan la instalación de OpenClaw.
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { test } from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";

import { V1_REPLACEMENT } from "../whatsapp-sticker.mjs";

const SCRIPT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "whatsapp-sticker.mjs");

const MONITOR = `export function makeListener(sendApi) {
	return {
		sendComposingTo: sendApi.sendComposingTo,
		sendMessage: sendApi.sendMessage,
		sendPoll: sendApi.sendPoll,
		sendReaction: sendApi.sendReaction
	};
}
`;

const SEND = `const requireWhatsAppAcceptedSendResult = (result) => result;
export async function sendMessageWhatsApp(active, to, primaryMediaUrl, buffer, mime) {
	const part = "";
	const partOptions = void 0;
	const sendPart = async () => {
				const accepted = requireWhatsAppAcceptedSendResult(partOptions ? await active.sendMessage(to, part, buffer, mime, partOptions) : await active.sendMessage(to, part, buffer, mime));
				return accepted;
	};
	return await sendPart();
}
`;

const RUNTIME = `const runtimeStore = { setRuntime(r) { this.runtime = r; } };
const setWhatsAppRuntime = runtimeStore.setRuntime;
export { setWhatsAppRuntime as a };
`;

function makeState({ version = "2026.11.10", monitor = MONITOR, send = SEND, runtime = RUNTIME, plugin = true } = {}) {
  const state = fs.mkdtempSync(path.join(os.tmpdir(), "valeria-sticker-"));
  if (!plugin) return { state };
  const dir = path.join(state, "npm", "projects", "openclaw-whatsapp-test", "node_modules", "@openclaw", "whatsapp");
  const setup = path.join(dir, "dist", ".setup");
  fs.mkdirSync(setup, { recursive: true });
  fs.writeFileSync(path.join(dir, "package.json"), JSON.stringify({ name: "@openclaw/whatsapp", version }));
  const files = {
    monitor: path.join(setup, "monitor-x.mjs"),
    send: path.join(setup, "send-x.mjs"),
    api: path.join(setup, "send-api-x.mjs"),
    runtime: path.join(setup, "runtime-x.mjs"),
  };
  fs.writeFileSync(files.monitor, monitor);
  fs.writeFileSync(files.send, send);
  fs.writeFileSync(files.api, "export const sendSticker = () => {};\n");
  fs.writeFileSync(files.runtime, runtime);
  return { state, ...files };
}

function run(state, ...args) {
  try {
    const out = execFileSync(process.execPath, [SCRIPT, "--state-dir", state, ...args], { encoding: "utf8" });
    return { code: 0, out };
  } catch (error) {
    return { code: error.status, out: String(error.stdout) };
  }
}

const load = (file) => import(`${pathToFileURL(file).href}?t=${Date.now()}${Math.random()}`);

test("aplica las dos partes: el listener expone sendSticker y los stickers de Valer-IA salen como sticker", async () => {
  const { state, monitor, send } = makeState();
  assert.match(run(state, "--check").out, /soporte-sticker: ausente/);
  const applied = run(state);
  assert.equal(applied.code, 0);
  assert.match(applied.out, /soporte-sticker: aplicado/);
  assert.ok(fs.existsSync(`${monitor}.orig`) && fs.existsSync(`${send}.orig`));

  const sendApi = { sendSticker: () => "s", sendMessage: () => "m", sendPoll: () => "p", sendReaction: () => "r" };
  const listener = (await load(monitor)).makeListener({ ...sendApi, sendComposingTo: () => {} });
  assert.equal(listener.sendSticker, sendApi.sendSticker);

  const calls = [];
  const active = {
    sendSticker: async (_to, _buffer, options) => (calls.push(["sticker", options.mimetype]), "ok-sticker"),
    sendMessage: async (_to, _part, _buffer, mime) => (calls.push(["media", mime]), "ok-media"),
  };
  const { sendMessageWhatsApp } = await load(send);
  const buffer = Buffer.from("RIFF0000WEBP");
  const windows = String.raw`D:\repo\docs\whatsapp\stickers\valeria-hola.webp`;
  assert.equal(await sendMessageWhatsApp(active, "x", windows, buffer, "image/webp"), "ok-sticker");
  assert.equal(await sendMessageWhatsApp(active, "x", "C:/fotos/otra.webp", buffer, "image/webp"), "ok-media");
  assert.equal(await sendMessageWhatsApp(active, "x", "C:/voz/nota.ogg", buffer, "audio/ogg"), "ok-media");
  assert.deepEqual(calls, [["sticker", "image/webp"], ["media", "image/webp"], ["media", "audio/ogg"]]);
});

test("es idempotente", () => {
  const { state, monitor, send } = makeState();
  run(state);
  const once = [fs.readFileSync(monitor, "utf8"), fs.readFileSync(send, "utf8")];
  const again = run(state);
  assert.equal(again.code, 0);
  assert.match(again.out, /soporte-sticker: parcheado/);
  assert.deepEqual([fs.readFileSync(monitor, "utf8"), fs.readFileSync(send, "utf8")], once);
});

test("retira el cambio de la versión 1 (símbolo global)", () => {
  const v1 = RUNTIME.replace("const setWhatsAppRuntime = runtimeStore.setRuntime;", V1_REPLACEMENT);
  const { state, runtime } = makeState({ runtime: v1 });
  assert.equal(run(state).code, 0);
  assert.equal(fs.readFileSync(runtime, "utf8"), RUNTIME);
});

test("sin el anclaje exacto no escribe nada y sale con 3", () => {
  const { state, monitor, send } = makeState({ send: SEND.replace("partOptions ? await", "partOptions?await") });
  const before = [fs.readFileSync(monitor, "utf8"), fs.readFileSync(send, "utf8")];
  const result = run(state);
  assert.equal(result.code, 3);
  assert.match(result.out, /anclaje «envio» no encontrado/);
  assert.deepEqual([fs.readFileSync(monitor, "utf8"), fs.readFileSync(send, "utf8")], before);
  assert.ok(!fs.existsSync(`${monitor}.orig`));
});

test("otra versión del componente no se parchea", () => {
  const { state } = makeState({ version: "2027.1.1" });
  const result = run(state);
  assert.equal(result.code, 3);
  assert.match(result.out, /versión 2027\.1\.1 no soportada/);
});

test("sin componente instalado sale con 2", () => {
  const { state } = makeState({ plugin: false });
  const result = run(state, "--check");
  assert.equal(result.code, 2);
  assert.match(result.out, /sin-plugin/);
});
