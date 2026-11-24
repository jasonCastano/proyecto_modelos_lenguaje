// Plugin puente de Valer-IA Caña para OpenClaw (spec 024, ADR 0028).
// Cada mensaje entrante ya autenticado (allowFrom / emparejamiento) se envía al backend FastAPI
// por loopback; si el backend falla, OpenClaw sigue con su agente nativo (modo degradado).
import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";

import { dispatch, resolveConfig } from "./src/bridge.ts";

export default definePluginEntry({
  id: "valeria-bridge",
  name: "Valer-IA bridge",
  description: "Envía los mensajes de WhatsApp a Valer-IA Caña (router, memoria, herramientas y citas).",
  register(api) {
    const config = resolveConfig(api.pluginConfig, process.env);
    if (!config.token) {
      api.logger?.warn?.("valeria-bridge: falta VALERIA_CHANNEL_TOKEN; el puente queda inactivo");
      return;
    }
    api.on("before_dispatch", (event) =>
      dispatch(event, config, fetch, (message) => api.logger?.warn?.(message)),
    );
  },
});
