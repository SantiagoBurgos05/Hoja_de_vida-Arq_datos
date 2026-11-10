import { describe, it, expect, vi, beforeEach } from "vitest";

// Entorno node: se simula sessionStorage y fetch.
const store = new Map();
globalThis.sessionStorage = { getItem: (k) => store.get(k) ?? null, setItem: (k, v) => store.set(k, v), removeItem: (k) => store.delete(k) };
const { api, ApiError, token, setUnauthorizedHandler } = await import("../src/lib/api.js");

const resp = (status, body) => ({ ok: status >= 200 && status < 300, status, statusText: "x", json: async () => body, headers: new Headers() });

beforeEach(() => { store.clear(); vi.restoreAllMocks(); });

describe("api", () => {
  it("envía el token Bearer y devuelve JSON", async () => {
    token.set("abc");
    const f = vi.fn().mockResolvedValue(resp(200, { ok: 1 }));
    globalThis.fetch = f;
    expect(await api.get("/api/x")).toEqual({ ok: 1 });
    expect(f.mock.calls[0][1].headers.Authorization).toBe("Bearer abc");
  });
  it("409 lleva la versión actual del servidor", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(resp(409, { detail: { code: "revision_obsoleta", message: "cambió", current: { revision: 5 } } }));
    await expect(api.put("/api/resume", {})).rejects.toMatchObject({ status: 409, code: "revision_obsoleta", detail: { current: { revision: 5 } } });
  });
  it("401 con sesión activa invoca el manejador de sesión vencida", async () => {
    token.set("abc");
    const h = vi.fn(); setUnauthorizedHandler(h);
    globalThis.fetch = vi.fn().mockResolvedValue(resp(401, { detail: "no" }));
    await expect(api.get("/api/x")).rejects.toBeInstanceOf(ApiError);
    expect(h).toHaveBeenCalled();
  });
  it("error de red en POST no reintenta y no pierde datos (status 0)", async () => {
    globalThis.fetch = vi.fn().mockRejectedValue(new TypeError("fail"));
    await expect(api.post("/api/x", {})).rejects.toMatchObject({ status: 0 });
    expect(globalThis.fetch).toHaveBeenCalledTimes(1);
  });
});
