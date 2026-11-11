import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { createSaver, flushAll, hasPending, _registrySize } from "../src/lib/saver.js";

const deferred = () => { let resolve, reject; const p = new Promise((a, b) => { resolve = a; reject = b; }); return { p, resolve, reject }; };

beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());

describe("saver (autoguardado)", () => {
  it("al desmontar con cambios pendientes guarda en lugar de descartar", async () => {
    const save = vi.fn().mockResolvedValue({});
    const s = createSaver({ save, delay: 1200 });
    s.schedule();                       // el usuario escribe…
    vi.advanceTimersByTime(300);        // …y cambia de sección antes de 1,2 s
    s.dispose();
    await vi.runAllTimersAsync();
    expect(save).toHaveBeenCalledTimes(1);
    expect(hasPending()).toBe(false);
  });

  it("serializa: nunca dos guardados simultáneos y no pierde el último cambio", async () => {
    const d1 = deferred();
    let active = 0, maxActive = 0;
    const save = vi.fn(async () => { active++; maxActive = Math.max(maxActive, active); if (save.mock.calls.length === 1) await d1.p; active--; });
    const s = createSaver({ save, delay: 10 });
    s.schedule(); vi.advanceTimersByTime(10);          // primer guardado en curso
    s.schedule(); vi.advanceTimersByTime(10);          // cambio durante el guardado
    expect(save).toHaveBeenCalledTimes(1);
    d1.resolve();
    await vi.runAllTimersAsync();
    expect(save).toHaveBeenCalledTimes(2);
    expect(maxActive).toBe(1);
    s.dispose();
  });

  it("flushAll guarda lo pendiente de todos los formularios (antes de exportar o salir)", async () => {
    const a = vi.fn().mockResolvedValue({}), b = vi.fn().mockResolvedValue({});
    const sa = createSaver({ save: a, delay: 5000 }), sb = createSaver({ save: b, delay: 5000 });
    sa.schedule(); sb.schedule();
    expect(hasPending()).toBe(true);
    expect(await flushAll()).toBe(true);
    expect(a).toHaveBeenCalledTimes(1); expect(b).toHaveBeenCalledTimes(1);
    sa.dispose(); sb.dispose();
    expect(_registrySize()).toBe(0);
  });

  it("sin conexión el cambio sigue pendiente y flushAll informa el fallo", async () => {
    const save = vi.fn().mockRejectedValueOnce(Object.assign(new Error("offline"), { status: 0 })).mockResolvedValue({});
    const statuses = [];
    const s = createSaver({ save, delay: 5000, onStatus: (st) => statuses.push(st) });
    s.schedule();
    expect(await flushAll()).toBe(false);
    expect(s.pending()).toBe(true);
    expect(statuses).toContain("error");
    expect(await s.flush()).toBe(true);
    expect(s.pending()).toBe(false);
    s.dispose();
  });

  it("sin cambios no envía nada", async () => {
    const save = vi.fn();
    const s = createSaver({ save });
    expect(await s.flush()).toBe(true);
    expect(save).not.toHaveBeenCalled();
    s.dispose();
  });
});
