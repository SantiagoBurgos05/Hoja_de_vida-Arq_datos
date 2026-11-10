import { describe, it, expect } from "vitest";
import { setPath, getPath, checkFile, orgLabel, recordLabel, fmtBytes, MAX_UPLOAD } from "../src/lib/format.js";

describe("format", () => {
  it("setPath no muta el original y crea rutas anidadas", () => {
    const a = { x: { y: 1 } };
    const b = setPath(a, "x.z.w", 2);
    expect(a).toEqual({ x: { y: 1 } });
    expect(b.x.z.w).toBe(2);
    expect(getPath(b, "x.y")).toBe(1);
    expect(getPath(b, "no.existe")).toBeUndefined();
  });
  it("checkFile valida tipo y tamaño (5 MB)", () => {
    expect(checkFile({ size: 10, type: "application/pdf" })).toBeNull();
    expect(checkFile({ size: 10, type: "image/png" })).toBeNull();
    expect(checkFile({ size: MAX_UPLOAD + 1, type: "application/pdf" })).toMatch(/5 MB/);
    expect(checkFile({ size: 10, type: "text/plain" })).toMatch(/PDF, JPG o PNG/);
    expect(checkFile(null)).toMatch(/Seleccione/);
  });
  it("las etiquetas distinguen entidad verificada, antecedente declarado y soporte adjunto", () => {
    expect(orgLabel("verified")).toMatch(/verificada/);
    expect(orgLabel("error")).toMatch(/borrador conservado/);
    expect(recordLabel("declared")).toBe("Antecedente declarado");
    expect(recordLabel("supported")).toBe("Con soporte adjunto");
    expect(recordLabel("draft")).toBe("Borrador");
  });
  it("fmtBytes", () => { expect(fmtBytes(2048)).toBe("2 KB"); expect(fmtBytes(2 * 1048576)).toBe("2.0 MB"); });
});
