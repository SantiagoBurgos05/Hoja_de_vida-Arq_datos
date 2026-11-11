import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "../lib/api.js";
import { useAutosave } from "../lib/useAutosave.js";
import { Badge, ConflictBanner, SaveStatus } from "./ui.jsx";
import EntityVerifier from "./EntityVerifier.jsx";
import Documents from "./Documents.jsx";
import { recordLabel } from "../lib/format.js";

const SERVER_FIELDS = ["id", "user_id", "resume_id", "revision", "record_status", "organization_id", "organization_status", "created_at", "updated_at"];

// Tarjeta genérica de un registro (formación superior / experiencia). `toPayload` limpia campos del servidor.
export default function RecordCard({ path, recordType, record, sourcesFor, renderFields, title, onDelete, onRefresh }) {
  const [form, setForm] = useState(record);
  const [org, setOrg] = useState(null);

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

  return (
    <article className="record">
      <header>
        <h3>{title(form)}</h3>
        <Badge kind={form.record_status === "supported" ? "ok" : form.record_status === "declared" ? "info" : "neutral"}>{recordLabel(form.record_status)}</Badge>
      </header>
      {auto.status === "conflict" && (
        <ConflictBanner
          onUseServer={() => { if (auto.conflict) setForm(auto.conflict); auto.clearConflict(); onRefresh?.(); }}
          onKeepMine={() => { setForm((f) => ({ ...f, revision: auto.conflict?.revision ?? f.revision })); auto.clearConflict(); setTimeout(auto.saveNow, 0); }} />
      )}
      <div className="grid">{renderFields(form, patch)}</div>
      <SaveStatus status={auto.status} message={auto.message} onRetry={auto.saveNow} />
      <EntityVerifier recordType={recordType} recordId={record.id} sources={sourcesFor(form)} status={status} organization={org}
                      onChanged={() => onRefresh?.()} />
      <Documents recordType={recordType} recordId={record.id} orgStatus={status} onChanged={() => onRefresh?.()} />
      <footer><button className="danger" onClick={() => window.confirm("¿Eliminar este registro y sus soportes?") && onDelete(record.id)}>Eliminar registro</button></footer>
    </article>
  );
}
