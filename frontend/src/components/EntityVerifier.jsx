import React, { useState } from "react";
import { api } from "../lib/api.js";
import { Badge } from "./ui.jsx";
import { orgLabel } from "../lib/format.js";

// Fuentes por tipo de registro. RUES/SIGEP pueden estar deshabilitadas en el servidor (sin vía oficial verificada).
export const SOURCES = {
  education_basic: [["due", "DUE / Buscando Colegio"]],
  education_higher: [["snies", "SNIES (educación superior)"], ["siet", "SIET (educación para el trabajo)"]],
  work_privada: [["rues", "RUES (empresa privada)"]],
  work_publica: [["sigep", "SIGEP (entidad pública)"]],
};

export default function EntityVerifier({ recordType, recordId, sources, status, organization, onChanged }) {
  const [source, setSource] = useState(sources[0]?.[0]);
  const [q, setQ] = useState({ query: "", municipio: "", official_id: "" });
  const [res, setRes] = useState(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  async function search() {
    setBusy(true); setMsg("");
    try {
      const body = { source };
      if (q.official_id.trim()) body.official_id = q.official_id.trim();
      else { body.query = q.query.trim(); if (q.municipio.trim()) body.municipio = q.municipio.trim(); }
      setRes(await api.post("/api/organizations/search", body));
    } catch (e) { setMsg(e.message); } finally { setBusy(false); }
  }
  async function verify(official_id) {
    setBusy(true); setMsg("");
    try {
      const r = await api.post("/api/organizations/verify", { source, official_id, record_type: recordType, record_id: recordId });
      setMsg(r.message); setRes(null); onChanged?.(r);
    } catch (e) { setMsg(e.message); } finally { setBusy(false); }
  }

  return (
    <div className="entity">
      <div className="entity-head">
        <Badge kind={status === "verified" ? "ok" : status === "pending" ? "neutral" : "bad"}>{orgLabel(status)}</Badge>
        {status === "verified" && organization && (
          <span className="muted"> {organization.name} · {organization.source.toUpperCase()} {organization.official_id} · consultada {organization.verified_at?.slice(0, 10)}{organization.estado_registral ? ` · estado: ${organization.estado_registral}` : ""}</span>
        )}
      </div>
      {status === "verified" && (
        <p className="note">Esto confirma que la entidad existe en la fuente oficial. <strong>No</strong> acredita que usted haya estudiado o trabajado allí ni autentica sus certificados.</p>
      )}
      <details>
        <summary>{status === "verified" ? "Cambiar entidad" : "Buscar y verificar entidad"}</summary>
        <div className="grid">
          <label className="field"><span>Fuente</span>
            <select value={source} onChange={(e) => setSource(e.target.value)}>{sources.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select>
          </label>
          <label className="field"><span>Nombre</span><input value={q.query} onChange={(e) => setQ({ ...q, query: e.target.value })} /></label>
          <label className="field"><span>Municipio</span><input value={q.municipio} onChange={(e) => setQ({ ...q, municipio: e.target.value })} /></label>
          <label className="field"><span>o identificador oficial (NIT/código)</span><input value={q.official_id} onChange={(e) => setQ({ ...q, official_id: e.target.value })} /></label>
        </div>
        <button disabled={busy || !(q.query.trim() || q.official_id.trim())} onClick={search}>{busy ? "Consultando…" : "Buscar"}</button>
        {res && (
          <div>
            <p className={res.organization_status === "error" ? "banner bad" : "muted"}>{res.message}</p>
            <ul className="candidates">
              {res.candidates.map((c) => (
                <li key={c.official_id}>
                  <div><strong>{c.name}</strong><br /><span className="muted">{c.municipio}{c.departamento ? `, ${c.departamento}` : ""} · ID {c.official_id}{c.estado_registral ? ` · ${c.estado_registral}` : ""}</span></div>
                  <button disabled={busy} onClick={() => verify(c.official_id)}>Verificar esta</button>
                </li>
              ))}
            </ul>
          </div>
        )}
        {msg && <p className="muted" role="status">{msg}</p>}
      </details>
    </div>
  );
}
