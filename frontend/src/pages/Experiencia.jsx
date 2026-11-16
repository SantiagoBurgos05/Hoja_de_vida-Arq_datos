import React, { useEffect, useState } from "react";
import { api } from "../lib/api.js";
import { Card, EmptyState, Icon, Note, Select, Spinner, Text } from "../components/ui.jsx";
import RecordCard from "../components/RecordCard.jsx";
import { SOURCES } from "../components/EntityVerifier.jsx";

const CATS = [["servidor_publico", "Servidor público"], ["empleado_privado", "Empleado del sector privado"], ["independiente", "Trabajador independiente"]];
const fmtT = (t) => `${t.anios} ${t.anios === 1 ? "año" : "años"} ${t.meses} ${t.meses === 1 ? "mes" : "meses"}`;

function Tiempo({ refreshKey }) {
  const [s, setS] = useState(null);
  useEffect(() => { api.get("/api/resume/experience-summary").then(setS).catch(() => setS(null)); }, [refreshKey]);
  if (!s) return null;
  return (
    <Card icon="clock" tone="accent" title="Tiempo total de experiencia" desc="Sección 4 del formato · los periodos que se cruzan cuentan una sola vez.">
      <div className="stats">
        {CATS.map(([k, l]) => <div className="stat" key={k}><small>{l}</small><b>{fmtT(s[k])}</b></div>)}
        <div className="stat total"><small>Total</small><b>{fmtT(s.total)}</b></div>
      </div>
      <table className="time">
        <thead><tr><th>Ocupación</th><th>Años</th><th>Meses</th></tr></thead>
        <tbody>
          {CATS.map(([k, l]) => <tr key={k}><td>{l}</td><td>{s[k].anios}</td><td>{s[k].meses}</td></tr>)}
          <tr className="total"><td>Total (sin contar dos veces los períodos traslapados)</td><td>{s.total.anios}</td><td>{s.total.meses}</td></tr>
        </tbody>
      </table>
      <div style={{ marginTop: 12 }}><Note>{s.nota}</Note></div>
    </Card>
  );
}

export default function Experiencia({ work, reloadWork }) {
  const [tick, setTick] = useState(0);
  const [adding, setAdding] = useState(false);
  const refresh = async () => { await reloadWork(); setTick((t) => t + 1); };
  async function add() {
    setAdding(true);
    try { await api.post("/api/work", { categoria_tiempo: "empleado_privado", tipo_entidad: "privada" }); await refresh(); } finally { setAdding(false); }
  }
  async function del(id) { await api.del(`/api/work/${id}`); refresh(); }
  const addBtn = (cls = "") => <button className={cls} onClick={add} disabled={adding}>{adding ? <Spinner /> : <Icon name="plus" />}Agregar experiencia</button>;
  return (
    <div className="stack">
      <Card icon="briefcase" title="Experiencia laboral" desc="Comience por el empleo actual. La plantilla imprime 4 experiencias por hoja y se repite la hoja si hay más."
            actions={work.length > 0 && addBtn("secondary sm")}>
        {work.length === 0 ? (
          <EmptyState icon="briefcase" title="Sin experiencia registrada" action={addBtn()}>
            Agregue cada empleo o contrato. Verifique la empresa en RUES o la entidad pública en SIGEP para adjuntar su certificado laboral.
          </EmptyState>
        ) : work.map((r) => (
          <RecordCard key={r.id} path="/api/work" recordType="work" record={r} onDelete={del} onRefresh={refresh} icon={r.tipo_entidad === "publica" ? "building" : "briefcase"}
            title={(f) => `${f.es_actual ? "Actual" : "Anterior"} — ${f.empresa_declarada || "sin entidad"}`}
            subtitle={(f) => [f.cargo, f.fecha_ingreso && `${f.fecha_ingreso} → ${f.es_actual ? "hoy" : f.fecha_retiro || "…"}`].filter(Boolean).join(" · ") || "Complete los datos del empleo"}
            sourcesFor={(f) => (f.tipo_entidad === "publica" ? SOURCES.work_publica : SOURCES.work_privada)}
            renderFields={(f, p) => (<>
              <Text label="Empresa o entidad (declarada)" value={f.empresa_declarada} onChange={(v) => p("empresa_declarada", v)} wide />
              <Select label="Tipo de entidad" value={f.tipo_entidad} onChange={(v) => p("tipo_entidad", v)} options={[["publica", "Pública"], ["privada", "Privada"]]}
                      hint="Define la fuente de verificación: SIGEP o RUES." />
              <Select label="Categoría para tiempo total" value={f.categoria_tiempo} onChange={(v) => p("categoria_tiempo", v)} options={CATS} />
              <Select label="¿Es el empleo actual?" value={f.es_actual ? "si" : "no"} onChange={(v) => p("es_actual", v === "si")} options={[["si", "Sí"], ["no", "No"]]} />
              <Text label="Fecha de ingreso" type="date" value={f.fecha_ingreso} onChange={(v) => p("fecha_ingreso", v || null)} />
              {!f.es_actual && <Text label="Fecha de retiro" type="date" value={f.fecha_retiro} onChange={(v) => p("fecha_retiro", v || null)} />}
              <Text label="Cargo o contrato" value={f.cargo} onChange={(v) => p("cargo", v)} />
              <Text label="Dependencia" value={f.dependencia} onChange={(v) => p("dependencia", v)} />
              <Text label="Dirección" value={f.direccion} onChange={(v) => p("direccion", v)} wide />
              <Text label="País" value={f.pais} onChange={(v) => p("pais", v)} />
              <Text label="Departamento" value={f.departamento} onChange={(v) => p("departamento", v)} />
              <Text label="Municipio" value={f.municipio} onChange={(v) => p("municipio", v)} />
              <Text label="Correo de la entidad" type="email" value={f.correo_entidad} onChange={(v) => p("correo_entidad", v || null)} />
              <Text label="Teléfonos" type="tel" value={f.telefonos} onChange={(v) => p("telefonos", v)} />
            </>)} />
        ))}
      </Card>
      <Tiempo refreshKey={tick} />
    </div>
  );
}
