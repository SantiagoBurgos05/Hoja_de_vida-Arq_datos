import React, { useEffect, useState } from "react";
import { api, downloadBlob } from "../lib/api.js";
import { flushAll } from "../lib/saver.js";
import { Section } from "../components/ui.jsx";

export default function Exportar() {
  const [warnings, setWarnings] = useState([]);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => { flushAll().then(() => api.get("/api/export/preview")).then((r) => setWarnings(r.warnings)).catch((e) => setErr(e.message)); }, []);
  async function go() {
    setBusy(true); setErr("");
    try {
      if (!(await flushAll())) throw new Error("Hay cambios sin guardar. Revise los avisos de guardado antes de exportar.");
      await downloadBlob("/api/export/pdf", "hoja_de_vida.pdf");
    } catch (e) { setErr(e.message); } finally { setBusy(false); }
  }
  return (
    <>
      <Section n="5" title="Firma y declaración">
        <p>La declaración de inhabilidad, la ciudad y fecha de diligenciamiento y la <strong>firma</strong> no se completan automáticamente: se diligencian a mano sobre el PDF impreso.</p>
      </Section>
      <Section n="6" title="Observaciones del Jefe de Recursos Humanos y/o Contratos">
        <p>Este espacio es de uso exclusivo de la entidad receptora y <strong>se deja en blanco</strong>.</p>
        <h3>Exportar</h3>
        {warnings.map((w, i) => <p key={i} className="banner warn" role="status">{w}</p>)}
        <button onClick={go} disabled={busy}>{busy ? "Generando…" : "Descargar PDF sobre el formato oficial"}</button>
        {err && <p className="banner bad" role="alert">{err}</p>}
      </Section>
    </>
  );
}
