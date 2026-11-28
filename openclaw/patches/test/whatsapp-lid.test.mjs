// Pruebas del parche valeria-lid v1 (spec 033, T006 y T012): `node --test openclaw/patches/test`.
// Trabajan sobre copias mínimas de los archivos del componente, con los anclajes textuales reales; nunca
// tocan la instalación de OpenClaw. Los ID son ficticios.
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { test } from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";

const SCRIPT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "whatsapp-lid.mjs");
const LID = "10000000000001@lid";

const MONITOR = `const createWhatsAppInboundMessageNormalizer = () => {
	const normalize = async (msg) => {
		const remoteJid = msg.key?.remoteJid;
		const group = false;
		const from = group ? remoteJid : await socketSession.resolveInboundJid(remoteJid);
		if (!from) {
			if (remoteJid.endsWith("@lid") || remoteJid.endsWith("@hosted.lid")) throw new Error("WhatsApp inbound LID identity unavailable");
			return null;
		}
		return { from };
	};
	return { normalize };
};
`;

const TARGET = `const WHATSAPP_USER_JID_RE = /^(\\d+)(?::\\d+)?@s\\.whatsapp\\.net$/i;
const WHATSAPP_LID_RE = /^(\\d+)@lid$/i;
function normalizeE164(value) {
	const digits = String(value).replace(/\\D/g, "");
	return digits ? \`+\${digits}\` : "";
}
function extractUserJidPhone(jid) {
	return (jid.match(WHATSAPP_USER_JID_RE) ?? jid.match(WHATSAPP_LID_RE))?.[1] ?? null;
}
export function normalizeWhatsAppTarget(value) {
	const candidate = value.trim();
	if (!candidate) return null;
	const phone = extractUserJidPhone(candidate);
	if (phone) {
		const normalized = normalizeE164(phone);
		return normalized.length > 1 ? normalized : null;
	}
	if (candidate.includes("@")) return null;
	const normalized = normalizeE164(candidate);
	return normalized.length > 1 ? normalized : null;
}
`;

function makeState({ version = "2026.11.10", monitor = MONITOR, target = TARGET, plugin = true } = {}) {
  const state = fs.mkdtempSync(path.join(os.tmpdir(), "valeria-lid-"));
  if (!plugin) return { state };
  const dir = path.join(state, "npm", "projects", "openclaw-whatsapp-test", "node_modules", "@openclaw", "whatsapp");
  const setup = path.join(dir, "dist", ".setup");
  fs.mkdirSync(setup, { recursive: true });
  fs.writeFileSync(path.join(dir, "package.json"), JSON.stringify({ name: "@openclaw/whatsapp", version }));
  fs.writeFileSync(path.join(setup, "monitor-x.mjs"), monitor);
  fs.writeFileSync(path.join(setup, "normalize-target-x.mjs"), target);
  return { state, monitor: path.join(setup, "monitor-x.mjs"), target: path.join(setup, "normalize-target-x.mjs") };
}

function run(state, ...args) {
  try {
    const out = execFileSync(process.execPath, [SCRIPT, "--state-dir", state, ...args], { encoding: "utf8" });
    return { code: 0, out };
  } catch (error) {
    return { code: error.status, out: String(error.stdout) };
  }
}

test("--check sin parche dice «ausente» y no escribe", () => {
  const { state, monitor } = makeState();
  const result = run(state, "--check");
  assert.equal(result.code, 1);
  assert.match(result.out, /soporte-lid: ausente/);
  assert.equal(fs.readFileSync(monitor, "utf8"), MONITOR);
});

test("aplica los dos reemplazos, deja la marca y la copia .orig; es idempotente", () => {
  const { state, monitor, target } = makeState();
  const first = run(state);
  assert.equal(first.code, 0);
  assert.match(first.out, /soporte-lid: aplicado/);
  for (const file of [monitor, target]) {
    assert.match(fs.readFileSync(file, "utf8"), /valeria-lid v1/);
    assert.ok(fs.existsSync(`${file}.orig`));
  }
  assert.equal(fs.readFileSync(`${monitor}.orig`, "utf8"), MONITOR);
  const before = fs.readFileSync(monitor, "utf8");
  const second = run(state);
  assert.equal(second.code, 0);
  assert.match(second.out, /soporte-lid: parcheado/);
  assert.equal(fs.readFileSync(monitor, "utf8"), before);
  assert.match(run(state, "--check").out, /soporte-lid: parcheado/);
});

test("la versión nativa (sin el throw de LID) no se toca", () => {
  const native = MONITOR.replace(/\t\t\tif \(remoteJid\.endsWith[^\n]*\n/, "");
  const { state, monitor } = makeState({ monitor: native });
  const result = run(state);
  assert.equal(result.code, 0);
  assert.match(result.out, /soporte-lid: nativo/);
  assert.equal(fs.readFileSync(monitor, "utf8"), native);
});

test("otra versión con el throw presente falla sin escribir", () => {
  const { state, monitor } = makeState({ version: "2026.12.1" });
  const result = run(state);
  assert.equal(result.code, 1);
  assert.match(result.out, /versión 2026\.12\.1 no soportada/);
  assert.equal(fs.readFileSync(monitor, "utf8"), MONITOR);
});

test("sin anclajes falla sin escribir ningún archivo", () => {
  const changed = TARGET.replace("const phone = extractUserJidPhone(candidate);", "const tel = extractUserJidPhone(candidate);");
  const { state, monitor, target } = makeState({ target: changed });
  const result = run(state);
  assert.equal(result.code, 1);
  assert.match(result.out, /anclaje «salida» no encontrado/);
  assert.equal(fs.readFileSync(monitor, "utf8"), MONITOR);  // tampoco el otro archivo
  assert.equal(fs.readFileSync(target, "utf8"), changed);
});

test("sin el componente instalado dice «sin-plugin»", () => {
  const { state } = makeState({ plugin: false });
  const result = run(state, "--check");
  assert.equal(result.code, 1);
  assert.match(result.out, /soporte-lid: sin-plugin/);
});

test("la salida conserva el destino …@lid y los números siguen igual (T012)", async () => {
  const { state, target } = makeState();
  const before = await import(pathToFileURL(target).href + "?antes");
  assert.equal(before.normalizeWhatsAppTarget(LID), "+10000000000001");  // el defecto: número falso
  assert.equal(run(state).code, 0);
  const after = await import(pathToFileURL(target).href + "?despues");
  assert.equal(after.normalizeWhatsAppTarget(LID), LID);
  assert.equal(after.normalizeWhatsAppTarget("+573000000301"), "+573000000301");
  assert.equal(after.normalizeWhatsAppTarget("573000000301@s.whatsapp.net"), "+573000000301");
});

test("la entrada usa el ID cuando no hay número (y el número cuando lo hay)", async () => {
  const { state, monitor } = makeState();
  assert.equal(run(state).code, 0);
  const code = fs.readFileSync(monitor, "utf8");
  const body = `${code}\nexport { createWhatsAppInboundMessageNormalizer };`;
  const module = path.join(path.dirname(monitor), "monitor-ejecutable.mjs");
  const sessionDecl = "let socketSession;\nexport function setSession(value) { socketSession = value; }\n";
  fs.writeFileSync(module, sessionDecl + body);
  const loaded = await import(pathToFileURL(module).href);
  const { normalize } = loaded.createWhatsAppInboundMessageNormalizer();
  loaded.setSession({ resolveInboundJid: async () => null });
  assert.deepEqual(await normalize({ key: { remoteJid: LID } }), { from: LID });
  loaded.setSession({ resolveInboundJid: async (jid) => (jid.endsWith("@s.whatsapp.net") ? "+573000000301" : null) });
  assert.deepEqual(await normalize({ key: { remoteJid: LID, remoteJidAlt: "573000000301@s.whatsapp.net" } }), {
    from: "+573000000301",
  });
});
