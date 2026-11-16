import React, { useState } from "react";
import { api } from "../lib/api.js";
import { Badge, Banner, Icon, Spinner } from "./ui.jsx";
import { orgLabel } from "../lib/format.js";

// Fuentes por tipo de registro. Cualquiera puede estar deshabilitada en el servidor (DISABLED_SOURCES): se conserva el borrador.
export const SOURCES = {
  education_basic: [["due", "DUE / Buscando Colegio"]],
  education_higher: [["snies", "SNIES (educación superior)"], ["siet", "SIET (educación para el trabajo)"]],
  work_privada: [["rues", "RUES (empresa privada)"]],
  work_publica: [["sigep", "SIGEP (entidad pública)"]],
};
const STATUS_KIND = { verified: "ok", pending: "neutral", not_found: "warn", error: "bad" };
const HINT = {
  due: "Busque el colegio por nombre y municipio, o por código DANE.",
  snies: "Busque la institución por nombre y municipio, o por código SNIES o NIT.",
  siet: "Busque la institución por nombre y municipio, o por código SIET o NIT.",
  rues: "Busque la empresa por razón social, o mejor por NIT (con o sin dígito de verificación).",
  sigep: "Busque la entidad por nombre, o por código SIGEP o NIT.",
};

export default function EntityVerifier({ recordType, recordId, sources, status, organization, onChanged }) {
  const [source, setSource] = useState(sources[0]?.[0]);
  const [q, setQ] = useState({ query: "", municipio: "", official_id: "" });
  const [res, setRes] = useState(null);
  const [busy, setBusy] = useState(false);
  const [verifying, setVerifying] = useState(null);
  const [msg, setMsg] = useState("");
  const src = sources.find(([v]) => v === source) ? source : sources[0]?.[0];   // si cambia el tipo de entidad, cambia la fuente

  async function search(e) {
    e?.preventDefault();
    setBusy(true); setMsg(""); setRes(null);
    try {
      const body = { source: src };
      if (q.official_id.trim()) body.official_id = q.official_id.trim();
      else { body.query = q.query.trim(); if (q.municipio.trim()) body.municipio = q.municipio.trim(); }
      setRes(await api.post("/api/organizations/search", body));
    } catch (e2) { setMsg(e2.message); } finally { setBusy(false); }
  }
  async function verify(official_id) {
    setBusy(true); setVerifying(official_id); setMsg("");
    try {
      const r = await api.post("/api/organizations/verify", { source: src, official_id, record_type: recordType, record_id: recordId });
      setMsg(r.message); setRes(null); onChanged?.(r);
    } catch (e) { setMsg(e.message); } finally { setBusy(false); setVerifying(null); }
  }
  const canSearch = q.query.trim() || q.official_id.trim();

  return (
    <div className="entity">
      <div className="entity-status">
        <Badge kind={STATUS_KIND[status] || "neutral"}>{orgLabel(status)}</Badge>
      </div>
      {status === "verified" && organization && (
        <div className="entity-card">
          <Icon name="shield" size="lg" />
          <div>
            <strong>{organization.name}</strong>
            <span>{organization.source.toUpperCase()} · ID {organization.official_id} · consultada {organization.verified_at?.slice(0, 10)}</span>
            {organization.estado_registral && <span style={{ display: "block" }}>Estado: {organization.estado_registral}</span>}
          </div>
        </div>
      )}
      {status === "verified" && (
        <p className="note"><Icon name="info" /><span>Esto confirma que la entidad existe en la fuente oficial. <strong>No</strong> acredita que usted haya estudiado o trabajado allí ni autentica sus certificados.</span></p>
      )}
      {status !== "verified" && (
        <p className="muted small">Verifique la entidad en su fuente oficial para habilitar la carga de certificados. Buscar no verifica: debe elegir la coincidencia correcta.</p>
      )}

      <details className="finder">
        <summary><Icon name="search" />{status === "verified" ? "Cambiar entidad" : "Buscar y verificar entidad"}</summary>
        <form className="finder-body" onSubmit={search}>
          {sources.length > 1 ? (
            <div className="segmented" role="group" aria-label="Fuente oficial">
              {sources.map(([v, l]) => <button type="button" key={v} aria-pressed={src === v} onClick={() => setSource(v)} title={l}>{v.toUpperCase()}</button>)}
            </div>
          ) : (
            <Badge kind="info" plain>Fuente: {sources[0]?.[1]}</Badge>
          )}
          <p className="muted small">{HINT[src]}</p>
          <div className="grid">
            <label className="field"><span>Nombre</span><input value={q.query} placeholder="Ej.: minuto de dios" onChange={(e) => setQ({ ...q, query: e.target.value })} /></label>
            <label className="field"><span>Municipio</span><input value={q.municipio} placeholder="Opcional" onChange={(e) => setQ({ ...q, municipio: e.target.value })} /></label>
          </div>
          <div className="or">o</div>
          <label className="field"><span>o identificador oficial (NIT/código)</span><input value={q.official_id} inputMode="numeric" placeholder="Ej.: 890903938" onChange={(e) => setQ({ ...q, official_id: e.target.value })} /></label>
          <div><button type="submit" disabled={busy || !canSearch}>{busy && !verifying ? <Spinner /> : <Icon name="search" />}{busy && !verifying ? "Consultando…" : "Buscar"}</button></div>

          {res && (
            <div>
              {res.organization_status === "error" ? <Banner kind="bad">{res.message}</Banner>
                : <p className="muted small" style={{ marginBottom: 8 }}>{res.message}</p>}
              {res.candidates.length > 0 && (
                <ul className="candidates">
                  {res.candidates.map((c) => (
                    <li key={c.official_id}>
                      <div>
                        <strong>{c.name}</strong>
                        <span>{c.municipio}{c.departamento ? `, ${c.departamento}` : ""} · ID {c.official_id}{c.extra?.nit ? ` · NIT ${c.extra.nit}` : ""}</span>
                        {c.estado_registral && <span style={{ display: "block" }}>{c.estado_registral}</span>}
                      </div>
                      <button type="button" className="sm" disabled={busy} onClick={() => verify(c.official_id)}>
                        {verifying === c.official_id ? <Spinner /> : <Icon name="check" />}Verificar esta
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </form>
      </details>
      {msg && status !== "verified" && <p className="muted small" role="status" style={{ marginTop: 10 }}>{msg}</p>}
    </div>
  );
}
