import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "../lib/api.js";
import { useAutosave } from "../lib/useAutosave.js";
import { Badge, ConflictBanner, Icon, SaveStatus, Spinner } from "./ui.jsx";
import EntityVerifier from "./EntityVerifier.jsx";
import Documents from "./Documents.jsx";
import { recordLabel } from "../lib/format.js";

const SERVER_FIELDS = ["id", "user_id", "resume_id", "revision", "record_status", "organization_id", "organization_status", "created_at", "updated_at"];
const RECORD_KIND = { supported: "ok", declared: "info", draft: "neutral" };

// Tarjeta genérica de un registro (formación superior / experiencia). `toPayload` limpia campos del servidor.
export default function RecordCard({ path, recordType, record, sourcesFor, renderFields, title, subtitle, icon = "doc", onDelete, onRefresh }) {
  const [form, setForm] = useState(record);
  const [org, setOrg] = useState(null);
  const [confirming, setConfirming] = useState(false);
  const [deleting, setDeleting] = useState(false);

  // Campos gestionados por el servidor se refrescan sin pisar lo que el usuario escribe.
  useEffect(() => {
    setForm((f) => ({ ...f, ...Object.fromEntries(SERVER_FIELDS.map((k) => [k, record[k]])) }));
  }, [record.revision, record.record_status, record.organization_status, record.organization_id]); // eslint-disable-line

  useEffect(() => {
    if (record.organization_id) api.get(`/api/organizations/${record.organization_id}`).then(setOrg).catch(() => setOrg(null));
    else setOrg(null);
  }, [record.organization_id]);

  const formRef = useRef(form);
  formRef.current = form;
  const save = useCallback(async () => {
    const v = formRef.current;
    const body = Object.fromEntries(Object.entries(v).filter(([k]) => !SERVER_FIELDS.includes(k)));
    const saved = await api.put(`${path}/${record.id}`, { ...body, revision: v.revision });
    const server = { revision: saved.revision, record_status: saved.record_status,
                     organization_status: saved.organization_status, organization_id: saved.organization_id };
    formRef.current = { ...formRef.current, ...server };     // un guardado encadenado usa ya la revisión nueva
    setForm((f) => ({ ...f, ...server }));
    if (server.organization_status !== v.organization_status) onRefresh?.();   // p. ej. verificación invalidada
  }, [path, record.id, onRefresh]);

  // Solo cambios de campos editables disparan el autoguardado (no los campos que gestiona el servidor).
  const editable = useMemo(() => JSON.stringify(Object.fromEntries(Object.entries(form).filter(([k]) => !SERVER_FIELDS.includes(k)))), [form]);
  const auto = useAutosave({ value: editable, loaded: true, save });
  const patch = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  const status = form.organization_status;

  async function remove() {
    setDeleting(true);
    try { await onDelete(record.id); } finally { setDeleting(false); setConfirming(false); }
  }

  return (
    <article className="record">
      <header>
        <span className={`tile${form.record_status === "supported" ? " accent" : ""}`}><Icon name={icon} size="lg" /></span>
        <div className="meta">
          <h3>{title(form)}</h3>
          {subtitle && <p>{subtitle(form)}</p>}
        </div>
        <div className="chips">
          <Badge kind={RECORD_KIND[form.record_status] || "neutral"}>{recordLabel(form.record_status)}</Badge>
        </div>
      </header>
      <div className="record-body">
        {auto.status === "conflict" && (
          <div style={{ marginBottom: 16 }}>
            <ConflictBanner
              onUseServer={() => { if (auto.conflict) setForm(auto.conflict); auto.clearConflict(); onRefresh?.(); }}
              onKeepMine={() => { setForm((f) => ({ ...f, revision: auto.conflict?.revision ?? f.revision })); auto.clearConflict(); setTimeout(auto.saveNow, 0); }} />
          </div>
        )}
        <div className="grid">{renderFields(form, patch)}</div>
        <div className="record-panels">
          <div className="panel">
            <div className="panel-head"><Icon name="shield" /><h4>Verificación de la entidad</h4></div>
            <EntityVerifier recordType={recordType} recordId={record.id} sources={sourcesFor(form)} status={status} organization={org}
                            onChanged={() => onRefresh?.()} />
          </div>
          <div className="panel">
            <Documents recordType={recordType} recordId={record.id} orgStatus={status} onChanged={() => onRefresh?.()} />
          </div>
        </div>
      </div>
      <footer>
        <SaveStatus status={auto.status} message={auto.message} onRetry={auto.saveNow} />
        {confirming ? (
          <span className="confirm" role="alert">
            ¿Eliminar este registro y sus soportes?
            <button className="danger sm" onClick={remove} disabled={deleting}>{deleting ? <Spinner /> : <Icon name="trash" />}Sí, eliminar</button>
            <button className="secondary sm" onClick={() => setConfirming(false)} disabled={deleting}>Cancelar</button>
          </span>
        ) : (
          <button className="ghost danger sm" onClick={() => setConfirming(true)}><Icon name="trash" />Eliminar registro</button>
        )}
      </footer>
    </article>
  );
}
