import React, { useCallback, useEffect, useRef, useState } from "react";
import { api, downloadBlob, request } from "../lib/api.js";
import { Badge, Banner, Icon, Spinner } from "./ui.jsx";
import { checkFile, fmtBytes } from "../lib/format.js";

// Soportes de un registro. La carga solo se habilita con la entidad verificada.
export default function Documents({ recordType, recordId, orgStatus, onChanged }) {
  const [docs, setDocs] = useState([]);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [usage, setUsage] = useState(null);
  const [over, setOver] = useState(false);
  const [confirmId, setConfirmId] = useState(null);
  const input = useRef();
  const enabled = orgStatus === "verified";

  const load = useCallback(async () => {
    try { setDocs(await api.get(`/api/documents?record_type=${recordType}&record_id=${recordId}`)); } catch (e) { setErr(e.message); }
  }, [recordType, recordId]);
  useEffect(() => { load(); }, [load]);
  // Espacio usado frente a la cuota del usuario (solo donde se puede cargar).
  const loadUsage = useCallback(() => api.get("/api/documents/usage").then(setUsage).catch(() => setUsage(null)), []);
  useEffect(() => { if (enabled) loadUsage(); }, [enabled, loadUsage]);

  async function upload(file) {
    const bad = checkFile(file);
    if (bad) { setErr(bad); return; }
    setBusy(true); setErr("");
    const form = new FormData();
    form.append("record_type", recordType); form.append("record_id", recordId); form.append("file", file);
    try {
      await request("POST", "/api/documents", { form, headers: { "Idempotency-Key": crypto.randomUUID() } });
      await load(); loadUsage(); onChanged?.();
    } catch (e) { setErr(e.message); } finally { setBusy(false); if (input.current) input.current.value = ""; }
  }
  async function remove(id) {
    setBusy(true); setErr("");
    try { await api.del(`/api/documents/${id}`); await load(); loadUsage(); onChanged?.(); } catch (e) { setErr(e.message); } finally { setBusy(false); setConfirmId(null); }
  }
  function onDrop(e) {
    e.preventDefault(); setOver(false);
    if (!enabled || busy) return;
    const f = e.dataTransfer?.files?.[0];
    if (f) upload(f);
  }
  const pct = usage ? Math.min(100, Math.round((usage.used_bytes / usage.quota_bytes) * 100)) : 0;

  return (
    <div className="docs">
      <div className="panel-head"><Icon name="file" /><h4>Soportes (certificados)</h4></div>
      {docs.length > 0 && (
        <ul className="doc-list">
          {docs.map((d) => (
            <li key={d.id}>
              <span className="tile"><Icon name="file" /></span>
              <div className="doc-name"><strong>{d.filename}</strong><span>{fmtBytes(d.size)}</span></div>
              <div className="chips">
                <Badge kind="ok">Soporte adjunto</Badge> <Badge kind="neutral" plain>Autenticidad no validada</Badge>
              </div>
              {confirmId === d.id ? (
                <span className="confirm">
                  <button className="danger sm" disabled={busy} onClick={() => remove(d.id)}>Sí, eliminar</button>
                  <button className="secondary sm" disabled={busy} onClick={() => setConfirmId(null)}>Cancelar</button>
                </span>
              ) : (
                <span style={{ display: "inline-flex", gap: 4 }}>
                  <button className="ghost sm" onClick={() => downloadBlob(`/api/documents/${d.id}/download`, d.filename).catch((e) => setErr(e.message))}>
                    <Icon name="download" />Descargar
                  </button>
                  <button className="ghost danger sm" disabled={busy} onClick={() => setConfirmId(d.id)} aria-label={`Eliminar ${d.filename}`}>
                    <Icon name="trash" />Eliminar
                  </button>
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
      {docs.length === 0 && enabled && <p className="muted small" style={{ marginBottom: 10 }}>Sin soportes cargados.</p>}

      <label className={`dropzone${enabled ? "" : " disabled"}${over ? " over" : ""}`}
             onDragOver={(e) => { e.preventDefault(); if (enabled) setOver(true); }} onDragLeave={() => setOver(false)} onDrop={onDrop}>
        <span className="tile">{busy ? <Spinner /> : <Icon name={enabled ? "upload" : "lock"} size="lg" />}</span>
        <div>
          <strong>{!enabled ? "Verifique primero la entidad" : busy ? "Subiendo…" : "Arrastre su certificado o haga clic para elegirlo"}</strong>
          <span>{enabled ? "PDF, JPG o PNG · máx. 5 MB" : "La carga de certificados se habilita cuando la entidad está verificada."}</span>
        </div>
        <input ref={input} type="file" accept="application/pdf,image/jpeg,image/png" disabled={!enabled || busy}
               onChange={(e) => e.target.files[0] && upload(e.target.files[0])} aria-label="Cargar certificado (PDF, JPG o PNG hasta 5 MB)" />
      </label>

      {usage && enabled && (
        <div className="usage">
          <div className={`usage-bar${pct >= 80 ? " high" : ""}`}><i style={{ width: `${pct}%` }} /></div>
          <small><span>Espacio usado {fmtBytes(usage.used_bytes)} de {fmtBytes(usage.quota_bytes)}</span><span>{pct}%</span></small>
        </div>
      )}
      {err && <div style={{ marginTop: 10 }}><Banner kind="bad" role="alert">{err}</Banner></div>}
    </div>
  );
}
