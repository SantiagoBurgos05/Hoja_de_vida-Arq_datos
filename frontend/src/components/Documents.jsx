import React, { useCallback, useEffect, useRef, useState } from "react";
import { api, downloadBlob, request } from "../lib/api.js";
import { Badge } from "./ui.jsx";
import { checkFile, fmtBytes } from "../lib/format.js";

// Soportes de un registro. La carga solo se habilita con la entidad verificada.
export default function Documents({ recordType, recordId, orgStatus, onChanged }) {
  const [docs, setDocs] = useState([]);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const input = useRef();
  const enabled = orgStatus === "verified";

  const load = useCallback(async () => {
    try { setDocs(await api.get(`/api/documents?record_type=${recordType}&record_id=${recordId}`)); } catch (e) { setErr(e.message); }
  }, [recordType, recordId]);
  useEffect(() => { load(); }, [load]);

  async function upload(file) {
    const bad = checkFile(file);
    if (bad) { setErr(bad); return; }
    setBusy(true); setErr("");
    const form = new FormData();
    form.append("record_type", recordType); form.append("record_id", recordId); form.append("file", file);
    try {
      await request("POST", "/api/documents", { form, headers: { "Idempotency-Key": crypto.randomUUID() } });
      await load(); onChanged?.();
    } catch (e) { setErr(e.message); } finally { setBusy(false); if (input.current) input.current.value = ""; }
  }
  async function remove(id) {
    if (!window.confirm("¿Eliminar este soporte? Se borra también el archivo almacenado.")) return;
    setBusy(true); setErr("");
    try { await api.del(`/api/documents/${id}`); await load(); onChanged?.(); } catch (e) { setErr(e.message); } finally { setBusy(false); }
  }

  return (
    <div className="docs">
      <h4>Soportes (certificados)</h4>
      {!enabled && <p className="note">Verifique primero la entidad para habilitar la carga de certificados.</p>}
      <ul>
        {docs.map((d) => (
          <li key={d.id}>
            <span>{d.filename} <span className="muted">({fmtBytes(d.size)})</span></span>
            <Badge kind="info">Soporte adjunto</Badge> <Badge kind="neutral">Autenticidad no validada</Badge>
            <button className="link" onClick={() => downloadBlob(`/api/documents/${d.id}/download`, d.filename).catch((e) => setErr(e.message))}>Descargar</button>
            <button className="link danger" disabled={busy} onClick={() => remove(d.id)}>Eliminar</button>
          </li>
        ))}
        {docs.length === 0 && <li className="muted">Sin soportes cargados.</li>}
      </ul>
      <input ref={input} type="file" accept="application/pdf,image/jpeg,image/png" disabled={!enabled || busy}
             onChange={(e) => e.target.files[0] && upload(e.target.files[0])} aria-label="Cargar certificado (PDF, JPG o PNG hasta 5 MB)" />
      <small className="muted"> PDF, JPG o PNG · máx. 5 MB</small>
      {err && <p className="banner bad" role="alert">{err}</p>}
    </div>
  );
}
