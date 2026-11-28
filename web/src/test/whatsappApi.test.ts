/**
 * Spec 032: `fetchWhatsAppLink` rechaza respuestas sin la forma esperada (un backend viejo devuelve la página
 * HTML en esa ruta) y nunca deja un enlace a medias.
 */
import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchWhatsAppLink } from "../lib/api";

function respond(body: unknown, ok = true) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({ ok, status: ok ? 200 : 500, json: () => Promise.resolve(body) }),
  );
}

afterEach(() => vi.unstubAllGlobals());

describe("fetchWhatsAppLink (spec 032)", () => {
  it("una respuesta que no es JSON es un error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: true, status: 200, json: () => Promise.reject(new Error("html")) }),
    );
    await expect(fetchWhatsAppLink()).rejects.toMatchObject({ apiError: { code: "invalid_response" } });
  });

  it("un objeto sin `available` es un error", async () => {
    respond({ hola: 1 });
    await expect(fetchWhatsAppLink()).rejects.toMatchObject({ apiError: { code: "invalid_response" } });
  });

  it("available sin enlaces se trata como no disponible", async () => {
    respond({ available: true, mode: "open", message: "Hola, Valer-IA", web_url: null, app_url: null });
    const link = await fetchWhatsAppLink();
    expect(link.available).toBe(false);
    expect(link.web_url).toBeNull();
    expect(link.qr_svg).toBeNull();
  });

  it("una respuesta válida pasa completa", async () => {
    respond({
      available: true,
      mode: "closed",
      message: "Hola, Valer-IA",
      web_url: "https://web.whatsapp.com/send?phone=570000000000",
      app_url: "https://wa.me/570000000000",
      qr_svg: "<svg></svg>",
    });
    const link = await fetchWhatsAppLink();
    expect(link).toMatchObject({ available: true, mode: "closed", qr_svg: "<svg></svg>" });
  });
});
