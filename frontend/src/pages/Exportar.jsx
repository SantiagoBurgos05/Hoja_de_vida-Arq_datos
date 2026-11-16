import React, { useEffect, useState } from "react";
import { api, downloadBlob } from "../lib/api.js";
import { flushAll } from "../lib/saver.js";
import { Banner, Card, Icon, Note, Spinner } from "../components/ui.jsx";

export default function Exportar({ resume, edu = [], work = [], progress = {} }) {
  const [warnings, setWarnings] = useState([]);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  useEffect(() => { flushAll().then(() => api.get("/api/export/preview")).then((r) => setWarnings(r.warnings)).catch((e) => setErr(e.message)); }, []);
  async function go() {
    setBusy(true); setErr(""); setDone(false);
    try {
      if (!(await flushAll())) throw new Error("Hay cambios sin guardar. Revise los avisos de guardado antes de exportar.");
      await downloadBlob("/api/export/pdf", "hoja_de_vida.pdf");
      setDone(true);
    } catch (e) { setErr(e.message); } finally { setBusy(false); }
  }
  const verifiedEdu = edu.filter((e) => e.organization_status === "verified").length;
  const verifiedWork = work.filter((w) => w.organization_status === "verified").length;
  const items = [
    { ok: (progress.personal?.pct || 0) >= 100, t: "Datos personales", d: progress.personal?.hint || "", href: "#/personal" },
    { ok: !!(resume?.education_basic?.titulo_obtenido || resume?.education_basic?.ultimo_grado), t: "Educación básica y media", d: resume?.education_basic?.titulo_obtenido || "Sin diligenciar", href: "#/formacion" },
    { ok: edu.length > 0, t: "Educación superior", d: edu.length ? `${edu.length} registrado(s) · ${verifiedEdu} con entidad verificada` : "Opcional si no tiene estudios superiores", href: "#/formacion" },
    { ok: work.length > 0, t: "Experiencia laboral", d: work.length ? `${work.length} registrada(s) · ${verifiedWork} con entidad verificada` : "Agregue al menos un empleo si aplica", href: "#/experiencia" },
  ];

  return (
    <div className="export-grid">
      <div className="stack">
        <Card icon="check" tone="accent" title="Antes de exportar" desc="Lo que llevará el PDF. Puede exportar en cualquier momento; lo incompleto queda en blanco.">
          <ul className="checklist">
            {items.map((i) => (
              <li key={i.t} className={i.ok ? "ok" : ""}>
                <span className="tick">{i.ok ? <Icon name="check" /> : null}</span>
                <div><strong>{i.t}</strong><span>{i.d}</span></div>
                {!i.ok && <a href={i.href}>Completar <Icon name="arrow" /></a>}
              </li>
            ))}
          </ul>
          {warnings.length > 0 && <div className="stack" style={{ gap: 8, marginTop: 14 }}>{warnings.map((w, i) => <Banner key={i} kind="warn" role="status">{w}</Banner>)}</div>}
        </Card>
        <Card icon="sparkle" tone="warn" title="Secciones que se completan a mano">
          <div className="stack" style={{ gap: 10 }}>
            <Note icon="info"><strong>5 · Firma y declaración:</strong> la declaración de inhabilidad, la ciudad y fecha de diligenciamiento y la firma no se completan automáticamente; se diligencian a mano sobre el PDF impreso.</Note>
            <Note icon="building"><strong>6 · Observaciones del Jefe de Recursos Humanos y/o Contratos:</strong> este espacio es de uso exclusivo de la entidad receptora y se deja en blanco.</Note>
          </div>
        </Card>
      </div>

      <div className="card cta">
        <div className="doc-art"><Icon name="doc" size="xl" /></div>
        <h2>Formato Único de Hoja de Vida</h2>
        <p>Persona Natural · 3 páginas sobre la plantilla oficial, con sus datos y el tiempo total de experiencia calculado.</p>
        <button className="block" onClick={go} disabled={busy}>{busy ? <Spinner /> : <Icon name="download" />}{busy ? "Generando…" : "Descargar PDF sobre el formato oficial"}</button>
        {done && <div style={{ marginTop: 12 }}><Banner kind="ok" role="status">PDF generado. Revíselo, imprímalo y fírmelo.</Banner></div>}
        {err && <div style={{ marginTop: 12 }}><Banner kind="bad" role="alert">{err}</Banner></div>}
      </div>
    </div>
  );
}
