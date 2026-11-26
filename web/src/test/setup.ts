import "@testing-library/jest-dom/vitest";

// jsdom no implementa la reproducción de medios: el video pitch de la entrada (spec 028) la llama al
// montar. Cada prueba puede redefinirlas para observarlas.
Object.defineProperty(HTMLMediaElement.prototype, "play", {
  configurable: true,
  value: () => Promise.resolve(),
});
Object.defineProperty(HTMLMediaElement.prototype, "pause", { configurable: true, value: () => {} });
