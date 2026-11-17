import React, { useEffect, useState } from "react";
import { api } from "../lib/api.js";
import { Badge, Banner, Icon, Spinner } from "./ui.jsx";
import { MODALIDADES, orgLabel, programLabel } from "../lib/format.js";

// Fuentes por tipo de registro. Cualquiera puede estar deshabilitada en el servidor (DISABLED_SOURCES): se conserva el borrador.
export const SOURCES = {
  education_basic: [["due", "DUE / Buscando Colegio"]],
  education_higher: [["snies", "SNIES (educación superior)"], ["siet", "SIET (educación para el trabajo)"]],
  work_privada: [["rues", "RUES (empresa privada)"]],
  work_publica: [["sigep", "SIGEP (entidad pública)"]],
};
const STATUS_KIND = { verified: "ok", pending: "warn", not_found: "bad", error: "bad" };
const HINT = {
  due: "Busque el colegio por nombre y municipio, o por código DANE.",
  snies: "Busque la institución por nombre y municipio, o por código SNIES o NIT. Si escribe también el programa, verá directamente los programas que coinciden.",
  siet: "Busque la institución por nombre y municipio, o por código SIET o NIT. Si escribe también el programa, verá directamente los programas que coinciden.",
  rues: "Busque la empresa por razón social, o mejor por NIT (con o sin dígito de verificación).",
  sigep: "Busque la entidad por nombre, o por código SIGEP o NIT.",
};
const PROGRAM_SOURCES = new Set(["snies", "siet"]);

// Lista de programas candidatos (institución, título oficial, nivel, municipio y estado).
function ProgramList({ items, busyId, disabled, onVerify, label }) {
  return (
    <ul className="candidates programs">
      {items.map((c) => (
        <li key={`${c.institution_id}-${c.program_id}`}>
          <div>
            <strong>{c.name}</strong>
            <span>{c.institution_name} · ID {c.institution_id}</span>
            <span style={{ display: "block" }}>{[c.level, c.municipio, c.estado].filter(Boolean).join(" · ")}</span>
          </div>
          <button type="button" className="sm" disabled={disabled} onClick={() => onVerify(c)}>
            {busyId === `${c.institution_id}-${c.program_id}` ? <Spinner /> : <Icon name="check" />}{label}
          </button>
        </li>
      ))}
    </ul>
  );
}

// Paso 2 (estudios superiores): el programa dentro de la institución ya verificada.
function ProgramPanel({ source, institutionId, recordId, study, onChanged, autoSearch }) {
  const [typed, setQ] = useState(null);                 // null = sin editar: sigue al nombre de los estudios declarado
  const q = typed ?? (study.name || "");
  const [levelOnly, setLevelOnly] = useState(true);
  const [res, setRes] = useState(null);
  const [busy, setBusy] = useState(false);
  const [busyId, setBusyId] = useState(null);
  const [msg, setMsg] = useState("");
  const st = study.programStatus || "pending";
  const p = study.program;
  const [open, setOpen] = useState(st !== "verified");
  // Recién verificada la institución: se buscan de inmediato los programas que coinciden con el estudio declarado.
  useEffect(() => { if (autoSearch && st !== "verified") search(); }, [autoSearch]); // eslint-disable-line react-hooks/exhaustive-deps

  async function search(e) {
    e?.preventDefault();
    setBusy(true); setMsg(""); setRes(null);
    try {
      setRes(await api.post("/api/organizations/programs/search", {
        source, institution_id: institutionId, program_query: q.trim() || null, modalidad: levelOnly ? study.modalidad : null }));
    } catch (e2) { setMsg(e2.message); } finally { setBusy(false); }
  }
  async function verify(c) {
    setBusy(true); setBusyId(`${c.institution_id}-${c.program_id}`); setMsg("");
    try {
      const r = await api.post("/api/organizations/programs/verify", { source, institution_id: c.institution_id, program_id: c.program_id, record_id: recordId });
      if (r.program_status !== "verified") setMsg(r.message); else setRes(null);
      onChanged?.(r);
    } catch (e) { setMsg(e.message); } finally { setBusy(false); setBusyId(null); }
  }

  return (
    <div className="program">
      <div className="entity-status">
        <Badge kind={STATUS_KIND[st] || "neutral"}>{programLabel(st)}</Badge>
      </div>
      {st === "verified" && p && (
        <div className="entity-card">
          <Icon name="cap" size="lg" />
          <div>
            <strong>{p.name}</strong>
            <span>{[p.level, p.municipio, p.estado].filter(Boolean).join(" · ")}</span>
            <span style={{ display: "block" }}>{(p.source || "").toUpperCase()} · consultado {String(p.verified_at || "").slice(0, 10)}</span>
          </div>
        </div>
      )}
      <details className="finder" open={open} onToggle={(e) => setOpen(e.currentTarget.open)}>
        <summary><Icon name="search" />{st === "verified" ? "Cambiar programa" : "Buscar programa en esta institución"}</summary>
        <form className="finder-body" onSubmit={search}>
          <p className="muted small">Se precarga con el nombre de los estudios que declaró. Escriba otras palabras del programa (por ejemplo «análisis desarrollo software») o déjelo vacío para ver todos los programas de la institución.</p>
          <label className="field"><span>Programa</span>
            <input value={q} placeholder="Ej.: ingeniería de sistemas" onChange={(e) => setQ(e.target.value)} />
          </label>
          {study.modalidad && (
            <label className="check">
              <input type="checkbox" checked={levelOnly} onChange={(e) => setLevelOnly(e.target.checked)} />
              <span>Solo programas de nivel {MODALIDADES[study.modalidad] || study.modalidad}</span>
            </label>
          )}
          <div><button type="submit" disabled={busy}>{busy && !busyId ? <Spinner /> : <Icon name="search" />}{busy && !busyId ? "Consultando…" : "Buscar programa"}</button></div>
          {res && (
            <div>
              {res.program_status === "error" ? <Banner kind="bad">{res.message}</Banner> : <p className="muted small" style={{ marginBottom: 8 }}>{res.message}</p>}
              {res.candidates.length > 0 && <ProgramList items={res.candidates} busyId={busyId} disabled={busy} onVerify={verify} label="Verificar este programa" />}
            </div>
          )}
        </form>
      </details>
      {msg && <p className="muted small" role="status" style={{ marginTop: 10 }}>{msg}</p>}
    </div>
  );
}

export default function EntityVerifier({ recordType, recordId, sources, status, organization, onChanged, study }) {
  const [source, setSource] = useState(sources[0]?.[0]);
  const [qs, setQ] = useState({ query: "", municipio: "", official_id: "", program: null });
  // Mientras la persona no edite «Programa», se precarga con el nombre de los estudios declarado (aunque cambie después).
  const q = { ...qs, program: qs.program ?? (study?.name || "") };
  const [justVerified, setJustVerified] = useState(false);
  const [res, setRes] = useState(null);
  const [progRes, setProgRes] = useState(null);
  const [busy, setBusy] = useState(false);
  const [verifying, setVerifying] = useState(null);
  const [msg, setMsg] = useState("");
  const src = sources.find(([v]) => v === source) ? source : sources[0]?.[0];   // si cambia el tipo de entidad, cambia la fuente
  const withPrograms = !!study && PROGRAM_SOURCES.has(src);

  async function search(e) {
    e?.preventDefault();
    setBusy(true); setMsg(""); setRes(null); setProgRes(null);
    try {
      if (withPrograms && q.program.trim()) {
        // Búsqueda combinada: institución + programa → candidatos a nivel de programa.
        const body = { source: src, program_query: q.program.trim(), modalidad: study.modalidad || null };
        if (q.official_id.trim()) body.institution_id = q.official_id.trim();      // código o NIT (el backend resuelve el NIT)
        else { body.institution_query = q.query.trim() || null; if (q.municipio.trim()) body.municipio = q.municipio.trim(); }
        setProgRes(await api.post("/api/organizations/programs/search", body));
        return;
      }
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
      setMsg(r.message); setRes(null);
      if (r.organization_status === "verified") setJustVerified(true);
      onChanged?.(r);
    } catch (e) { setMsg(e.message); } finally { setBusy(false); setVerifying(null); }
  }
  async function verifyProgram(c) {
    const key = `${c.institution_id}-${c.program_id}`;
    setBusy(true); setVerifying(key); setMsg("");
    try {
      const r = await api.post("/api/organizations/programs/verify", { source: src, institution_id: c.institution_id, program_id: c.program_id, record_id: recordId });
      setMsg(r.message); if (r.program_status === "verified") setProgRes(null); onChanged?.(r);
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
            <label className="field span-6"><span>Nombre</span><input value={q.query} placeholder="Ej.: minuto de dios" onChange={(e) => setQ({ ...qs, query: e.target.value })} /></label>
            <label className="field span-6"><span>Municipio</span><input value={q.municipio} placeholder="Opcional" onChange={(e) => setQ({ ...qs, municipio: e.target.value })} /></label>
          </div>
          <div className="or">o</div>
          <label className="field"><span>o identificador oficial (NIT/código)</span><input value={q.official_id} inputMode="numeric" placeholder="Ej.: 890903938" onChange={(e) => setQ({ ...qs, official_id: e.target.value })} /></label>
          {withPrograms && (
            <label className="field"><span>Programa (opcional)</span>
              <small className="muted">Precargado con sus estudios: se listan los programas de la institución que coinciden. Bórrelo para buscar solo la institución.</small>
              <input value={q.program} placeholder="Ej.: análisis y desarrollo de software" onChange={(e) => setQ({ ...q, program: e.target.value })} />
              {study.name && !q.program && (
                <button type="button" className="ghost sm chip-btn" onClick={() => setQ({ ...q, program: study.name })}>
                  <Icon name="plus" />Usar «{study.name}»
                </button>
              )}
            </label>
          )}
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
          {progRes && (
            <div>
              {progRes.program_status === "error" ? <Banner kind="bad">{progRes.message}</Banner>
                : <p className="muted small" style={{ marginBottom: 8 }}>{progRes.message} Al elegir un programa se verifican la institución y el programa.</p>}
              {progRes.candidates.length > 0 && <ProgramList items={progRes.candidates} busyId={verifying} disabled={busy} onVerify={verifyProgram} label="Verificar programa" />}
            </div>
          )}
        </form>
      </details>
      {msg && status !== "verified" && <p className="muted small" role="status" style={{ marginTop: 10 }}>{msg}</p>}

      {study && PROGRAM_SOURCES.has(organization?.source) && status === "verified" && (
        <div className="program-step">
          <div className="panel-head"><Icon name="cap" /><h4>Programa académico</h4></div>
          <ProgramPanel key={organization.official_id} source={organization.source} institutionId={organization.official_id} recordId={recordId}
            study={study} onChanged={onChanged} autoSearch={justVerified} />
        </div>
      )}
      {study && status !== "verified" && (
        <p className="muted small" style={{ marginTop: 10 }}><Icon name="cap" /> El programa se verifica después de la institución, o junto con ella si lo escribe en la búsqueda.</p>
      )}
    </div>
  );
}
