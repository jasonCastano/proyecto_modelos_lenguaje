/**
 * Procesador de captura del dictado (spec 023, research R5).
 *
 * El `AudioWorkletProcessor` corre en otro hilo y no puede importar módulos de la app, así que su
 * código va como texto y se registra desde una URL `blob:`. Así no depende de cómo Vite empaquete
 * los worklets y funciona igual en desarrollo, en `web/dist` y en las pruebas.
 *
 * Publica bloques `Float32Array` de unos 20 ms (canal 0) por `port.postMessage`; no escribe nada en
 * su salida, así que el micrófono no se escucha por los altavoces.
 */

export const CAPTURE_PROCESSOR = "dictation-capture";

export const WORKLET_SOURCE = `
class DictationCapture extends AudioWorkletProcessor {
  constructor() {
    super();
    this.size = Math.max(128, Math.round(sampleRate * 0.02));
    this.buffer = new Float32Array(this.size);
    this.filled = 0;
  }
  process(inputs) {
    const channel = inputs[0] && inputs[0][0];
    if (channel) {
      let offset = 0;
      while (offset < channel.length) {
        const take = Math.min(channel.length - offset, this.size - this.filled);
        this.buffer.set(channel.subarray(offset, offset + take), this.filled);
        this.filled += take;
        offset += take;
        if (this.filled === this.size) {
          this.port.postMessage(this.buffer.slice(0));
          this.filled = 0;
        }
      }
    }
    return true;
  }
}
registerProcessor("${CAPTURE_PROCESSOR}", DictationCapture);
`;

let cachedUrl: string | null = null;

/** URL `blob:` del procesador (se crea una vez por página). */
export function workletUrl(): string {
  if (!cachedUrl) {
    cachedUrl = URL.createObjectURL(new Blob([WORKLET_SOURCE], { type: "application/javascript" }));
  }
  return cachedUrl;
}
