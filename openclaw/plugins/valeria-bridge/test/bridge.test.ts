// Pruebas del puente sin red ni gateway: `npm test` (Node ≥ 24, tipos eliminados).
import assert from "node:assert/strict";
import { mock, test } from "node:test";

import {
  buildRequest,
  VoiceMemory,
  detectVoice,
  hasAudio,
  dispatch,
  maskDigits,
  resetThinking,
  messageKind,
  resolveConfig,
  shapeOf,
  toResult,
  transcriptOf,
  voiceCommandArgs,
  voiceKeys,
} from "../src/bridge.ts";

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

// --- spec 028: notas de voz (T019) ----------------------------------------------------------------

test("el bloque [Audio] se envía como nota de voz con su transcripción", () => {
  const body = buildRequest({ ...EVENT, content: "[Audio]\nTranscript: ¿Qué produce Manuelita?" });
  assert.equal(body?.kind, "audio");
  assert.equal(body?.input_mode, "voice");
  assert.equal(body?.text, "¿Qué produce Manuelita?");
  assert.equal(messageKind("[Audio] hola"), "audio");
});

test("transcripción tolerante y audio sin transcribir", () => {
  assert.equal(transcriptOf("[Audio]\nWhat does Manuelita produce?"), "What does Manuelita produce?");
  assert.equal(transcriptOf("[Audio] Transcripción: hola Valeria"), "hola Valeria");
  assert.equal(transcriptOf("<media:audio>"), "");
  const untranscribed = buildRequest({ ...EVENT, content: "<media:audio>" });
  assert.equal(untranscribed?.kind, "audio");
  assert.equal(untranscribed?.text, null);
});

test("con voz, primero envía la nota y después devuelve el texto", async () => {
  const order: string[] = [];
  const payload = {
    status: "answered",
    messages: ["Respuesta [1]\n\nFuentes:\n[1] Informe"],
    voice: { audio_path: "C:/estado/voice/a.ogg", language: "es" },
  };
  const fetchImpl = async () => {
    order.push("backend");
    return new Response(JSON.stringify(payload), { status: 200 });
  };
  const sent: string[][] = [];
  const result = await dispatch(EVENT, CONFIG, fetchImpl, () => {}, async (channel, target, path) => {
    order.push("voz");
    sent.push([channel, target, path]);
  });
  assert.deepEqual(order, ["backend", "voz"]);
  assert.deepEqual(sent[0], ["whatsapp", "+573001234567", "C:/estado/voice/a.ogg"]);
  assert.equal(result?.text, payload.messages[0]);
});

test("si la nota de voz falla, igual entrega el texto", async () => {
  const logs: string[] = [];
  const payload = { status: "answered", messages: ["texto"], voice: { audio_path: "a.ogg" } };
  const result = await dispatch(
    EVENT,
    CONFIG,
    fakeFetch(200, payload),
    (m) => logs.push(m),
    async () => {
      throw new Error("sin conexión con +573001234567");
    },
  );
  assert.deepEqual(result, { handled: true, text: "texto" });
  assert.ok(logs.some((m) => m.includes("nota de voz")));
  assert.ok(logs.every((m) => !m.includes("3001234567"))); // el número nunca llega al log
});

test("maskDigits oculta números de teléfono y deja el resto", () => {
  assert.equal(maskDigits("fallo para +573001234567 en 30 s"), "fallo para +# en 30 s");
});

test("sin voz en la respuesta no se envía audio", async () => {
  let called = false;
  await dispatch(EVENT, CONFIG, fakeFetch(200, { status: "answered", messages: ["x"] }), () => {}, async () => {
    called = true;
  });
  assert.equal(called, false);
});

test("timeout por defecto de 90 s y depuración solo con la variable", () => {
  const config = resolveConfig({}, { VALERIA_CHANNEL_TOKEN: "t" });
  assert.equal(config.timeoutMs, 90000);
  assert.equal(config.debug, false);
  assert.equal(resolveConfig({}, { VALERIA_CHANNEL_TOKEN: "t", VALERIA_BRIDGE_DEBUG: "1" }).debug, true);
});

test("el comando de voz no admite destinatarios con caracteres de shell", () => {
  assert.deepEqual(voiceCommandArgs("whatsapp", "+573001234567", "a.ogg"), [
    "message", "send", "--channel", "whatsapp", "--target", "+573001234567", "--media", "a.ogg",
  ]);
  assert.throws(() => voiceCommandArgs("whatsapp", "+57; rm -rf /", "a.ogg"));
});

// --- spec 029: voz en cualquier posición y depuración sin contenido (T005, T007) -------------------

const HEADER = "[WhatsApp +573001234567 +1m Thu 2026-11-27 10:08 GMT-5] ";
const BLOCK = "[Audio]\nUser text:\n<media:audio>\nTranscript:\nWhen was Ingenio Manuelita founded?";

test("la nota de voz se reconoce aunque venga detrás del encabezado del gateway", () => {
  const body = buildRequest({ ...EVENT, content: HEADER + BLOCK });
  assert.equal(body?.kind, "audio");
  assert.equal(body?.input_mode, "voice");
  assert.equal(body?.text, "When was Ingenio Manuelita founded?");
  assert.doesNotMatch(String(body?.text), /\d{7,}|WhatsApp|\[Audio\]|Transcript/);
});

test("la nota de voz se reconoce cuando el bloque solo llega en body", () => {
  const body = buildRequest({ ...EVENT, content: "When was Ingenio Manuelita founded?", body: BLOCK });
  assert.equal(body?.kind, "audio");
  assert.equal(body?.text, "When was Ingenio Manuelita founded?");
  const onlyBody = detectVoice("", HEADER + BLOCK);
  assert.deepEqual(onlyBody, { voice: true, transcript: "When was Ingenio Manuelita founded?" });
});

test("el texto escrito sigue siendo texto y pierde el encabezado", () => {
  const body = buildRequest({ ...EVENT, content: HEADER + "¿Qué produce Manuelita?" });
  assert.equal(body?.kind, "text");
  assert.equal(body?.text, "¿Qué produce Manuelita?");
  assert.equal(detectVoice("¿Qué produce Manuelita?", "¿Qué produce Manuelita?").voice, false);
});

test("la depuración solo registra la forma, nunca números ni palabras del mensaje", async () => {
  const lines: string[] = [];
  const event = { ...EVENT, content: HEADER + BLOCK, body: BLOCK };
  await dispatch(event, { ...CONFIG, debug: true }, fakeFetch(200, { status: "ignored" }), (m) =>
    lines.push(m),
  );
  const debug = lines.find((line) => line.includes("forma")) ?? "";
  assert.match(debug, /content: len=\d+, \[Audio\]@\d+, Transcript:@\d+/);
  assert.doesNotMatch(debug, /3001234567|Manuelita|founded/);
  assert.match(shapeOf("x", "hola"), /^x: len=4, \[Audio\]@-1, Transcript:@-1, media@-1/);
});

// --- spec 029: el adjunto de audio de `message_received` marca la nota de voz (prueba del 2026-11-27) ----

test("con el adjunto de audio, un content de solo transcripción viaja como nota de voz", () => {
  const body = buildRequest({ ...EVENT, content: "¿Cuándo inició Ingenio Manuelita?", voice: true });
  assert.equal(body?.kind, "audio");
  assert.equal(body?.input_mode, "voice");
  assert.equal(body?.text, "¿Cuándo inició Ingenio Manuelita?");
  const untranscribed = buildRequest({ ...EVENT, content: "<media:audio>", voice: true });
  assert.equal(untranscribed?.kind, "audio");
  assert.equal(untranscribed?.text, null);
  assert.equal(buildRequest({ ...EVENT, voice: false })?.kind, "text");
});

test("reconoce adjuntos de audio por tipo o por clase", () => {
  assert.equal(hasAudio([{ contentType: "audio/ogg; codecs=opus", transcribed: true }]), true);
  assert.equal(hasAudio([{ kind: "audio" }]), true);
  assert.equal(hasAudio([{ contentType: "image/jpeg", kind: "image" }]), false);
  assert.equal(hasAudio(undefined), false);
});

test("la memoria de voz cruza por id o por sesión + contenido y se consume una vez", async () => {
  let now = 1_000;
  const memory = new VoiceMemory(60_000, 500, () => now);
  memory.remember(voiceKeys({ messageId: "A1", sessionKey: "s", content: "hola" }));
  assert.equal(await memory.waitFor(voiceKeys({ messageId: "A1" }), 0), true);
  assert.equal(await memory.waitFor(voiceKeys({ messageId: "A1" }), 0), false);
  memory.remember(voiceKeys({ sessionKey: "s", content: "¿qué produce?" }));
  assert.equal(await memory.waitFor(voiceKeys({ messageId: "B2", sessionKey: "s", content: "¿qué produce?" }), 0), true);
  memory.remember(voiceKeys({ messageId: "C3" }));
  now += 120_000;
  assert.equal(await memory.waitFor(voiceKeys({ messageId: "C3" }), 0), false); // vencida
  assert.equal(await memory.waitFor(voiceKeys({ messageId: "texto" }), 50, 10), false);
});

test("espera breve a que message_received registre el audio", async () => {
  const memory = new VoiceMemory();
  setTimeout(() => memory.remember(voiceKeys({ messageId: "late" })), 30);
  assert.equal(await memory.waitFor(voiceKeys({ messageId: "late" }), 300, 10), true);
});

// --- spec 030: con la voz entregada, por escrito solo las fuentes (T008, T015) ---------------------

const VOICE_PAYLOAD = {
  status: "answered",
  messages: ["Manuelita produce azúcar [1].\n\nFuentes:\n[1] Informe — https://manuelita.com"],
  sources_messages: ["Fuentes:\n[1] Informe — https://manuelita.com"],
  voice: { audio_path: "C:/estado/voice/a.ogg", language: "es" },
};

test("voz entregada: el texto es solo el bloque de fuentes", async () => {
  const logs: string[] = [];
  const result = await dispatch(EVENT, CONFIG, fakeFetch(200, VOICE_PAYLOAD), (m) => logs.push(m), async () => true);
  assert.deepEqual(result, { handled: true, text: VOICE_PAYLOAD.sources_messages[0] });
  assert.ok(logs.some((m) => m.includes("solo fuentes")));
});

test("voz entregada sin fuentes: no se envía texto", async () => {
  const payload = { ...VOICE_PAYLOAD, sources_messages: [] };
  const result = await dispatch(EVENT, CONFIG, fakeFetch(200, payload), () => {}, async () => true);
  assert.deepEqual(result, { handled: true });
});

test("voz no entregada o con error: la respuesta escrita completa", async () => {
  const logs: string[] = [];
  const notDelivered = await dispatch(EVENT, CONFIG, fakeFetch(200, VOICE_PAYLOAD), (m) => logs.push(m), async () => false);
  assert.equal(notDelivered?.text, VOICE_PAYLOAD.messages[0]);
  const failed = await dispatch(EVENT, CONFIG, fakeFetch(200, VOICE_PAYLOAD), () => {}, async () => {
    throw new Error("sin conexión");
  });
  assert.equal(failed?.text, VOICE_PAYLOAD.messages[0]);
  assert.ok(logs.some((m) => m.includes("voz no entregada; texto completo")));
  assert.ok(logs.every((m) => !/\d{7,}/.test(m)));
});

test("backend anterior sin sources_messages: con voz entregada sigue la respuesta completa", async () => {
  const { sources_messages: _omit, ...legacy } = VOICE_PAYLOAD;
  const result = await dispatch(EVENT, CONFIG, fakeFetch(200, legacy), () => {}, async () => true);
  assert.equal(result?.text, VOICE_PAYLOAD.messages[0]);
});

test("sin voz en la respuesta: la respuesta completa, aunque traiga sources_messages", async () => {
  const payload = { ...VOICE_PAYLOAD, voice: null };
  const result = await dispatch(EVENT, CONFIG, fakeFetch(200, payload), () => {}, async () => true);
  assert.equal(result?.text, VOICE_PAYLOAD.messages[0]);
});

// --- spec 033: cuentas identificadas solo por ID (T013) ---------------------------------------
const LID = "10000000000001@lid"; // ficticio

test("la nota de voz acepta el ID de la cuenta como destino y rechaza lo demás", () => {
  assert.deepEqual(voiceCommandArgs("whatsapp", LID, "a.ogg"), [
    "message", "send", "--channel", "whatsapp", "--target", LID, "--media", "a.ogg",
  ]);
  assert.throws(() => voiceCommandArgs("whatsapp", "abc@lid", "a.ogg"));
  assert.throws(() => voiceCommandArgs("whatsapp", "+57; rm -rf /", "a.ogg"));
  assert.ok(voiceCommandArgs("whatsapp", "+573001234567", "a.ogg").includes("+573001234567"));
});

test("una cuenta solo con ID recibe la nota de voz en su chat y el log no lleva el ID", async () => {
  const logs: string[] = [];
  const targets: string[] = [];
  const payload = {
    status: "answered",
    messages: ["Respuesta [1]\n\nFuentes:\n[1] Informe"],
    sources_messages: ["Fuentes:\n[1] Informe"],
    voice: { audio_path: "C:/estado/voice/a.ogg", language: "es" },
  };
  await dispatch({ ...EVENT, senderId: LID }, CONFIG, fakeFetch(200, payload), (m) => logs.push(m),
    async (_channel, target) => {
      targets.push(target);
      throw new Error(`fallo al enviar a ${target}`);
    });
  assert.deepEqual(targets, [LID]);
  assert.ok(logs.every((m) => !m.includes("10000000000001")));
});

// --- spec 034: stickers (T013 y T020) -----------------------------------------------------------
const STICKER_CONFIG = {
  ...CONFIG,
  timeoutMs: 90000,
  stickersDir: "C:/repo/docs/whatsapp/stickers",
  stickerThinkingMs: 8000,
};

function slowFetch(ms: number, payload: unknown) {
  return async () => {
    await new Promise((resolve) => setTimeout(resolve, ms));
    return new Response(JSON.stringify(payload), { status: 200 });
  };
}

const flush = () => new Promise((resolve) => setImmediate(resolve));

test("el sticker «antes» se envía antes de devolver el texto", async () => {
  const order: string[] = [];
  const payload = {
    status: "answered",
    messages: ["¡Hola! Soy Valer-IA."],
    sticker: { name: "valeria-hola", path: "C:/s/valeria-hola.webp", position: "before" },
  };
  const result = await dispatch(EVENT, STICKER_CONFIG, fakeFetch(200, payload), () => {}, undefined,
    async (_channel, _target, path) => {
      order.push(path);
      return true;
    });
  order.push("texto");
  assert.deepEqual(order, ["C:/s/valeria-hola.webp", "texto"]);
  assert.equal(result?.text, "¡Hola! Soy Valer-IA.");
});

test("el sticker «después» llega 1,5 s más tarde, sin retrasar el texto", async () => {
  mock.timers.enable({ apis: ["setTimeout"] });
  try {
    const sent: string[] = [];
    const payload = {
      status: "answered",
      messages: ["¡Con gusto!"],
      sticker: { name: "valeria-gracias", path: "C:/s/valeria-gracias.webp", position: "after" },
    };
    const result = await dispatch(EVENT, { ...STICKER_CONFIG, stickerThinkingMs: 0 },
      fakeFetch(200, payload), () => {}, undefined, async (_c, _t, path) => {
        sent.push(path);
        return true;
      });
    assert.equal(result?.text, "¡Con gusto!");
    assert.deepEqual(sent, []);
    mock.timers.tick(1500);
    await flush();
    assert.deepEqual(sent, ["C:/s/valeria-gracias.webp"]);
  } finally {
    mock.timers.reset();
  }
});

test("si el sticker falla, la respuesta llega igual y el log no lleva el número", async () => {
  const logs: string[] = [];
  const payload = {
    status: "answered",
    messages: ["Respuesta"],
    sticker: { name: "valeria-hola", path: "C:/s/valeria-hola.webp", position: "before" },
  };
  const result = await dispatch(EVENT, STICKER_CONFIG, fakeFetch(200, payload), (m) => logs.push(m),
    undefined, async (_c, target) => {
      throw new Error(`sin conexión con ${target}`);
    });
  assert.equal(result?.text, "Respuesta");
  assert.ok(logs.some((m) => m.includes("sticker")));
  assert.ok(logs.every((m) => !m.includes("3001234567")));
});

test("«Pensando» sale si el backend tarda y no se repite en 10 minutos (T020)", async () => {
  resetThinking();
  mock.timers.enable({ apis: ["setTimeout", "Date"], now: Date.UTC(2026, 10, 28, 13, 0, 0) });
  try {
    const sent: string[] = [];
    const sender = async (_c: string, _t: string, path: string) => {
      sent.push(path.split("/").pop() ?? "");
      return true;
    };
    const payload = { status: "answered", messages: ["Plan listo"] };
    const slow = dispatch(EVENT, STICKER_CONFIG, slowFetch(9000, payload), () => {}, undefined, sender);
    mock.timers.tick(8000);
    await flush();
    assert.deepEqual(sent, ["valeria-pensando.webp"]);
    mock.timers.tick(1000);
    assert.equal((await slow)?.text, "Plan listo");

    const fast = dispatch(EVENT, STICKER_CONFIG, slowFetch(2000, payload), () => {}, undefined, sender);
    mock.timers.tick(2000);
    await fast;
    mock.timers.tick(10000);
    await flush();
    assert.deepEqual(sent, ["valeria-pensando.webp"]);  // la rápida no lo envía

    const again = dispatch(EVENT, STICKER_CONFIG, slowFetch(9000, payload), () => {}, undefined, sender);
    mock.timers.tick(9000);
    await again;
    assert.deepEqual(sent, ["valeria-pensando.webp"]);  // dentro de los 10 minutos: no se repite
  } finally {
    mock.timers.reset();
  }
});

test("stickerThinkingMs en 0 apaga «Pensando» y la configuración se lee del plugin", async () => {
  resetThinking();
  mock.timers.enable({ apis: ["setTimeout"] });
  try {
    const sent: string[] = [];
    const payload = { status: "answered", messages: ["ok"] };
    const call = dispatch(EVENT, { ...STICKER_CONFIG, stickerThinkingMs: 0 }, slowFetch(9000, payload),
      () => {}, undefined, async (_c, _t, path) => {
        sent.push(path);
        return true;
      });
    mock.timers.tick(9000);
    await call;
    assert.deepEqual(sent, []);
  } finally {
    mock.timers.reset();
  }
  const config = resolveConfig({ stickersDir: "C:/s", stickerThinkingMs: 0 }, { VALERIA_CHANNEL_TOKEN: "t" });
  assert.equal(config.stickersDir, "C:/s");
  assert.equal(config.stickerThinkingMs, 0);
  assert.equal(resolveConfig({}, { VALERIA_CHANNEL_TOKEN: "t" }).stickerThinkingMs, 8000);
});

// --- spec 037: vías de entrega y registro (T005) -----------------------------------------------
import { findWhatsAppListener, PATCH_SYMBOL } from "../src/listener.ts";

function runtimeWith(listener: unknown, accountId?: string) {
  return {
    runtimeContexts: {
      get: (query: { channelId: string; accountId?: string; capability: string }) =>
        query.channelId === "whatsapp" &&
        query.capability === "connection-controller" &&
        (accountId === undefined || query.accountId === accountId)
          ? { getActiveListener: () => listener }
          : undefined,
    },
  };
}
const LISTENER = { sendSticker: async () => ({ messageId: "x" }) };

test("spec 037: la vía compartida va primero", async () => {
  const found = await findWhatsAppListener(runtimeWith(LISTENER, "default"), {
    globals: {},
    importListener: async () => LISTENER,
  });
  assert.equal(found.route, "compartido");
  assert.equal(found.listener, LISTENER);
});

test("spec 037: sin vía compartida se usa el runtime del parche y luego el import", async () => {
  const patched = await findWhatsAppListener({}, { globals: { [PATCH_SYMBOL]: runtimeWith(LISTENER) } });
  assert.equal(patched.route, "parche");
  const imported = await findWhatsAppListener(undefined, {
    globals: {},
    importListener: async () => LISTENER,
  });
  assert.equal(imported.route, "import");
});

test("spec 037: sin listener devuelve el motivo y el diagnóstico, sin lanzar", async () => {
  const found = await findWhatsAppListener(runtimeWith(null), {
    globals: {},
    importListener: async () => {
      throw new Error("no");
    },
  });
  assert.equal(found.listener, null);
  assert.equal(found.reason, "sin-listener");
  assert.ok(found.detail.some((line) => line.startsWith("compartido: controlador sin listener")));
  assert.ok(found.detail.includes("parche: no instalado"));
  assert.ok(found.detail.includes("import: error"));
});

test("spec 037: el log dice «enviado vía» o «no enviado: motivo», sin números", async () => {
  const payload = {
    status: "answered",
    messages: ["Hola"],
    sticker: { name: "valeria-hola", path: "C:/s/3001234567/valeria-hola.webp", position: "before" },
  };
  const ok: string[] = [];
  await dispatch(EVENT, { ...STICKER_CONFIG, stickerThinkingMs: 0 }, fakeFetch(200, payload),
    (m) => ok.push(m), undefined, async () => ({ ok: true, route: "compartido" }));
  assert.ok(ok.includes("valeria-bridge: sticker enviado (valeria-hola.webp) vía compartido"));
  const failed: string[] = [];
  const result = await dispatch(EVENT, { ...STICKER_CONFIG, stickerThinkingMs: 0 },
    fakeFetch(200, payload), (m) => failed.push(m), undefined,
    async () => ({ ok: false, reason: "sin-listener" }));
  assert.equal(result?.text, "Hola");
  assert.ok(failed.includes("valeria-bridge: sticker no enviado (valeria-hola.webp): sin-listener"));
  assert.ok([...ok, ...failed].every((m) => !m.includes("3001234567")));
});
