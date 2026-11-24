// Pruebas del puente sin red ni gateway: `npm test` (Node ≥ 24, tipos eliminados).
import assert from "node:assert/strict";
import { test } from "node:test";

import { buildRequest, dispatch, messageKind, resolveConfig, toResult } from "../src/bridge.ts";

const CONFIG = {
  backendUrl: "http://127.0.0.1:8000",
  token: "secreto",
  timeoutMs: 50,
  channels: ["whatsapp"],
};
const EVENT = {
  messageId: "3EB0C4",
  content: "¿Qué produce Manuelita?",
  channel: "whatsapp",
  senderId: "+573001234567",
  timestamp: Date.UTC(2026, 10, 28, 13, 0, 0),
};

function fakeFetch(status: number, payload: unknown, calls: RequestInit[] = []) {
  return async (_url: string, init: RequestInit) => {
    calls.push(init);
    return new Response(JSON.stringify(payload), { status });
  };
}

test("construye el cuerpo del contrato §1", () => {
  const body = buildRequest(EVENT);
  assert.equal(body?.channel, "whatsapp");
  assert.equal(body?.message_id, "3EB0C4");
  assert.equal(body?.sender, "+573001234567");
  assert.equal(body?.kind, "text");
  assert.equal(body?.text, "¿Qué produce Manuelita?");
  assert.equal(body?.received_at, "2026-11-28T13:00:00.000Z");
});

test("los grupos y los mensajes sin remitente no se envían", () => {
  assert.equal(buildRequest({ ...EVENT, isGroup: true }), null);
  assert.equal(buildRequest({ ...EVENT, senderId: undefined }), null);
});

test("detecta adjuntos", () => {
  assert.equal(messageKind("<media:image>"), "image");
  assert.equal(messageKind("<media:audio>"), "audio");
  assert.equal(messageKind("hola"), "text");
});

test("answered responde con el texto y envía el token", async () => {
  const calls: RequestInit[] = [];
  const result = await dispatch(
    EVENT,
    CONFIG,
    fakeFetch(200, { status: "answered", messages: ["uno", "dos"] }, calls),
  );
  assert.deepEqual(result, { handled: true, text: "uno\n\ndos" });
  assert.equal((calls[0].headers as Record<string, string>)["X-Channel-Token"], "secreto");
});

test("ignored atiende en silencio", async () => {
  const result = await dispatch(EVENT, CONFIG, fakeFetch(200, { status: "ignored", messages: [] }));
  assert.deepEqual(result, { handled: true });
});

test("error HTTP o de red pasa al modo degradado", async () => {
  assert.equal(await dispatch(EVENT, CONFIG, fakeFetch(503, {})), undefined);
  const broken = async () => {
    throw new Error("ECONNREFUSED");
  };
  assert.equal(await dispatch(EVENT, CONFIG, broken), undefined);
});

test("timeout pasa al modo degradado", async () => {
  const slow = (_url: string, init: RequestInit) =>
    new Promise<Response>((_resolve, reject) => {
      init.signal?.addEventListener("abort", () => reject(new Error("abort")));
    });
  assert.equal(await dispatch(EVENT, CONFIG, slow), undefined);
});

test("otros canales no se interceptan", async () => {
  assert.equal(await dispatch({ ...EVENT, channel: "discord" }, CONFIG, fakeFetch(200, {})), undefined);
});

test("estado desconocido lanza error (y el despacho lo trata como falla)", async () => {
  assert.throws(() => toResult({ status: "raro" }));
  assert.equal(await dispatch(EVENT, CONFIG, fakeFetch(200, { status: "raro" })), undefined);
});

test("backendUrl debe ser loopback", () => {
  assert.throws(() => resolveConfig({ backendUrl: "https://ejemplo.com" }, {}));
  const config = resolveConfig({}, { VALERIA_CHANNEL_TOKEN: "t" });
  assert.equal(config.backendUrl, "http://127.0.0.1:8000");
  assert.equal(config.token, "t");
});
