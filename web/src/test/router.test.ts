import { afterEach, describe, expect, it, vi } from "vitest";
import { act, renderHook } from "@testing-library/react";

import { navigate, parseRoute, useRoute } from "../lib/router";

afterEach(() => {
  window.history.replaceState(null, "", "/");
});

describe("router (spec 026, R2)", () => {
  it("reconoce las cuatro áreas", () => {
    expect(parseRoute("/")).toEqual({ route: "/", notFound: false });
    expect(parseRoute("/agente")).toEqual({ route: "/agente", notFound: false });
    expect(parseRoute("/planificacion")).toEqual({ route: "/planificacion", notFound: false });
    expect(parseRoute("/evidencia/")).toEqual({ route: "/evidencia", notFound: false });
  });

  it("manda las rutas desconocidas a la entrada con aviso", () => {
    expect(parseRoute("/gerencia")).toEqual({ route: "/", notFound: true });
  });

  it("navigate usa pushState y notifica a los suscriptores", () => {
    const push = vi.spyOn(window.history, "pushState");
    const { result } = renderHook(() => useRoute());
    act(() => navigate("/planificacion"));
    expect(push).toHaveBeenCalledWith(null, "", "/planificacion");
    expect(result.current.route).toBe("/planificacion");
    push.mockRestore();
  });

  it("popstate actualiza la ruta (botón atrás)", () => {
    const { result } = renderHook(() => useRoute());
    act(() => {
      window.history.replaceState(null, "", "/evidencia");
      window.dispatchEvent(new PopStateEvent("popstate"));
    });
    expect(result.current.route).toBe("/evidencia");
  });
});
