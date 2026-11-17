import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "../lib/api.js";
import { useAutosave } from "../lib/useAutosave.js";
import { Badge, ConflictBanner, Icon, RequiredLegend, SaveStatus, Spinner } from "./ui.jsx";
import EntityVerifier from "./EntityVerifier.jsx";
import Documents from "./Documents.jsx";
import { recordLabel } from "../lib/format.js";

const SERVER_FIELDS = ["id", "user_id", "resume_id", "revision", "record_status", "organization_id", "organization_status",
                       "program_status", "program", "created_at", "updated_at"];
const RECORD_KIND = { supported: "ok", declared: "info", draft: "neutral" };

// Tarjeta genérica de un registro (formación superior / experiencia). `toPayload` limpia campos del servidor.
export default function RecordCard({ path, recordType, record, sourcesFor, renderFields, title, subtitle, icon = "doc", onDelete, onRefresh, label, isNew }) {
  const [form, setForm] = useState(record);
  const [org, setOrg] = useState(null);
  const [confirming, setConfirming] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const ref = useRef(null);
  // Registro recién agregado: se lleva a la vista y se enfoca su primer campo.
  useEffect(() => {
    if (!isNew || !ref.current) return;
    ref.current.scrollIntoView({ behavior: "smooth", block: "start" });
    const t = setTimeout(() => ref.current?.querySelector(".record-body input, .record-body select")?.focus({ preventScroll: true }), 350);
    return () => clearTimeout(t);
  }, [isNew]);

  // Campos gestionados por el servidor se refrescan sin pisar lo que el usuario escribe.
  useEffect(() => {
    setForm((f) => ({ ...f, ...Object.fromEntries(SERVER_FIELDS.map((k) => [k, record[k]])) }));
  }, [record.revision, record.record_status, record.organization_status, record.organization_id, record.program_status, record.program?.program_id]); // eslint-disable-line

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
    <article className={`record st-${form.record_status || "draft"}${isNew ? " new" : ""}`} ref={ref}>
      <header>
        <span className={`tile${form.record_status === "supported" ? " accent" : ""}`}><Icon name={icon} size="lg" /></span>
        <div className="meta">
          {label && <span className="record-n">{label}</span>}
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
        <div className="panel-head"><span className="step-dot" aria-hidden="true">1</span><h4>Datos del registro</h4></div>
        <RequiredLegend />
        <div className="grid">{renderFields(form, patch)}</div>
        <div className="record-panels">
          <div className="panel">
            <div className="panel-head"><span className={`step-dot${status === "verified" ? " done" : ""}`} aria-hidden="true">{status === "verified" ? <Icon name="check" /> : 2}</span><h4>Verificación de la entidad</h4></div>
            <EntityVerifier recordType={recordType} recordId={record.id} sources={sourcesFor(form)} status={status} organization={org}
                            onChanged={() => onRefresh?.()}
                            study={recordType === "education_higher" ? { name: form.nombre_estudios, modalidad: form.modalidad,
                                                                         programStatus: form.program_status, program: form.program } : null} />
          </div>
          <div className="panel">
            <Documents recordType={recordType} recordId={record.id} orgStatus={status} onChanged={() => onRefresh?.()} step={3} />
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
