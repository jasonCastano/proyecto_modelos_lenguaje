/// <reference types="vite/client" />
import { describe, expect, it } from "vitest";

import credits from "../../public/media/fotos/CREDITOS.md?raw";

import { ALLOWED_LICENSES, PHOTOS, photoSrc } from "../data/photos";
import { PLATFORMS, PRODUCTS } from "../data/products";
import { PRODUCT_GLYPHS } from "../components/brand/ProductGlyphs";

// Archivos presentes en public/media/fotos (Vite los lista en tiempo de prueba, sin Node).
const FILES = Object.keys(import.meta.glob("../../public/media/fotos/*.webp")).map((key) =>
  key.replace("../../public", ""),
);

describe("fotos sustitutas (spec 031, SC-007)", () => {
  it.each(Object.values(PHOTOS))("$id tiene autor, licencia libre, fuente y texto alternativo", (photo) => {
    expect(photo.author.trim()).not.toBe("");
    expect(ALLOWED_LICENSES).toContain(photo.license);
    expect(photo.sourceUrl).toMatch(/^https:\/\/commons\.wikimedia\.org\/wiki\/File:/);
    expect(photo.alt.trim().length).toBeGreaterThan(10);
    expect(photo.standIn).toBe(true);
  });

  it.each(Object.values(PHOTOS))("$id está en public/media/fotos en sus dos tamaños", (photo) => {
    for (const width of [700, 1400] as const) {
      expect(FILES).toContain(photoSrc(photo.id, width));
    }
  });

  it("cada foto figura en CREDITOS.md con su fuente", () => {
    for (const photo of Object.values(PHOTOS)) {
      expect(credits).toContain(photo.commons);
    }
  });
});

describe("productos (spec 031, US4)", () => {
  it("cada producto tiene color y glifo propios", () => {
    for (const product of PRODUCTS) {
      expect(product.color).toMatch(/^var\(--[a-z-]+\)$/);
      expect(PRODUCT_GLYPHS[product.key]).toBeTypeOf("function");
    }
    expect(new Set(PRODUCTS.map((p) => p.color)).size).toBe(PRODUCTS.length);
  });

  it("cada plataforma usa productos conocidos y una foto con créditos", () => {
    for (const platform of PLATFORMS) {
      expect(PHOTOS[platform.photo]).toBeDefined();
      for (const key of platform.products) {
        expect(PRODUCTS.some((p) => p.key === key)).toBe(true);
      }
    }
  });
});
