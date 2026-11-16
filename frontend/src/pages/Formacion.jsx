import React, { useState } from "react";
import { api } from "../lib/api.js";
import { Card, EmptyState, Icon, LevelPicker, Note, Select, Spinner, Text } from "../components/ui.jsx";
import RecordCard from "../components/RecordCard.jsx";
import EntityVerifier, { SOURCES } from "../components/EntityVerifier.jsx";
import Documents from "../components/Documents.jsx";
import { MODALIDADES, getPath, setPath } from "../lib/format.js";

function Basica({ resume, setResume, reloadResume }) {
  const eb = resume.education_basic || {};
  const set = (path, v) => setResume((r) => ({ ...r, education_basic: setPath(r.education_basic || {}, path, v) }));
  return (
    <Card icon="school" tone="accent" title="Educación básica y media" desc="Último grado aprobado y colegio donde lo cursó.">
      <div className="grid">
        <Select label="Último grado aprobado" value={eb.ultimo_grado == null ? "" : String(eb.ultimo_grado)} onChange={(v) => set("ultimo_grado", v == null ? null : Number(v))}
                options={Array.from({ length: 11 }, (_, i) => [String(i + 1), `${i + 1}º`])} />
        <Text label="Título obtenido" value={eb.titulo_obtenido} onChange={(v) => set("titulo_obtenido", v)} placeholder="Ej.: Bachiller académico" />
        <Text label="Mes de grado (1-12)" type="number" min={1} max={12} value={getPath(eb, "fecha_grado.mes")} onChange={(v) => set("fecha_grado.mes", v === "" ? null : Number(v))} />
        <Text label="Año de grado" type="number" min={1900} max={2100} value={getPath(eb, "fecha_grado.anio")} onChange={(v) => set("fecha_grado.anio", v === "" ? null : Number(v))} />
        <Text label="Colegio (declarado)" value={eb.institucion_declarada} onChange={(v) => set("institucion_declarada", v)} wide />
      </div>
      <div className="record-panels">
        <div className="panel">
          <div className="panel-head"><Icon name="shield" /><h4>Verificación del colegio</h4></div>
          <EntityVerifier recordType="education_basic" recordId={resume.id} sources={SOURCES.education_basic} status={resume.organization_status || "pending"}
                          organization={null} onChanged={reloadResume} />
        </div>
        <div className="panel">
          <Documents recordType="education_basic" recordId={resume.id} orgStatus={resume.organization_status || "pending"} onChanged={reloadResume} />
        </div>
      </div>
    </Card>
  );
}

function Idiomas({ resume, setResume }) {
  const langs = resume.languages || [];
  const upd = (i, k, v) => setResume((r) => ({ ...r, languages: langs.map((l, j) => (j === i ? { ...l, [k]: v } : l)) }));
  const add = () => setResume((r) => ({ ...r, languages: [...langs, { idioma: "", habla: "B", lee: "B", escribe: "B" }] }));
  return (
    <Card icon="globe" title="Idiomas diferentes al español" desc="R = regular · B = bien · MB = muy bien"
          actions={langs.length > 0 && <button className="secondary sm" onClick={add}><Icon name="plus" />Agregar idioma</button>}>
      {langs.length === 0 ? (
        <EmptyState icon="globe" title="Aún no ha agregado idiomas" action={<button onClick={add}><Icon name="plus" />Agregar idioma</button>}>
          Si habla, lee o escribe otro idioma, agréguelo e indique su nivel en cada habilidad.
        </EmptyState>
      ) : langs.map((l, i) => (
        <div className="lang" key={i}>
          <Text label="Idioma" value={l.idioma} onChange={(v) => upd(i, "idioma", v)} placeholder="Ej.: Inglés" />
          {["habla", "lee", "escribe"].map((k) => <LevelPicker key={k} name={`lang-${i}-${k}`} label={`Lo ${k}`} value={l[k]} onChange={(v) => upd(i, k, v)} />)}
          <button className="ghost danger sm" onClick={() => setResume((r) => ({ ...r, languages: langs.filter((_, j) => j !== i) }))} aria-label={`Quitar ${l.idioma || "idioma"}`}>
            <Icon name="trash" />Quitar
          </button>
        </div>
      ))}
      {langs.length > 2 && <div style={{ marginTop: 12 }}><Note icon="alert">La plantilla oficial imprime hasta 2 idiomas; los demás quedan guardados pero no aparecen en el PDF.</Note></div>}
    </Card>
  );
}

export default function Formacion({ resume, setResume, reloadResume, edu, reloadEdu }) {
  const [adding, setAdding] = useState(false);
  async function add() { setAdding(true); try { await api.post("/api/education", { modalidad: "UN" }); await reloadEdu(); } finally { setAdding(false); } }
  async function del(id) { await api.del(`/api/education/${id}`); reloadEdu(); }
  const addBtn = (cls = "") => <button className={cls} onClick={add} disabled={adding}>{adding ? <Spinner /> : <Icon name="plus" />}Agregar estudio superior</button>;
  return (
    <div className="stack">
      <Basica resume={resume} setResume={setResume} reloadResume={reloadResume} />

      <Card icon="cap" title="Educación superior" desc="Técnica, tecnológica, universitaria y posgrados, en orden cronológico."
            actions={edu.length > 0 && addBtn("secondary sm")}>
        {edu.length === 0 ? (
          <EmptyState icon="cap" title="Sin estudios superiores registrados" action={addBtn()}>
            Agregue cada estudio, verifique la institución en SNIES o SIET y adjunte su diploma o certificado.
          </EmptyState>
        ) : edu.map((r) => (
          <RecordCard key={r.id} path="/api/education" recordType="education_higher" record={r} onDelete={del} onRefresh={reloadEdu} icon="cap"
            title={(f) => `${MODALIDADES[f.modalidad] || "Estudio"} — ${f.nombre_estudios || "sin nombre"}`}
            subtitle={(f) => [f.institucion_declarada, f.terminacion?.anio && `Terminación ${f.terminacion.anio}`].filter(Boolean).join(" · ") || "Complete los datos del estudio"}
            sourcesFor={() => SOURCES.education_higher}
            renderFields={(f, p) => (<>
              <Select label="Modalidad" value={f.modalidad} onChange={(v) => p("modalidad", v)} options={Object.entries(MODALIDADES).map(([k, v]) => [k, `${k} – ${v}`])} />
              <Text label="Nombre de los estudios o título" value={f.nombre_estudios} onChange={(v) => p("nombre_estudios", v)} wide />
              <Text label="Institución (declarada)" value={f.institucion_declarada} onChange={(v) => p("institucion_declarada", v)} wide />
              <Text label="Semestres aprobados" type="number" min={0} max={20} value={f.semestres_aprobados} onChange={(v) => p("semestres_aprobados", v === "" ? null : Number(v))} />
              <Select label="Graduado" value={f.graduado == null ? "" : f.graduado ? "si" : "no"} onChange={(v) => p("graduado", v == null ? null : v === "si")} options={[["si", "Sí"], ["no", "No"]]} />
              <Text label="Mes de terminación" type="number" min={1} max={12} value={f.terminacion?.mes} onChange={(v) => p("terminacion", { ...f.terminacion, mes: v === "" ? null : Number(v) })} />
              <Text label="Año de terminación" type="number" min={1900} max={2100} value={f.terminacion?.anio} onChange={(v) => p("terminacion", { ...f.terminacion, anio: v === "" ? null : Number(v) })} />
              <Text label="N.º de tarjeta profesional" value={f.tarjeta_profesional} onChange={(v) => p("tarjeta_profesional", v)} />
            </>)} />
        ))}
        {edu.length > 5 && <div style={{ marginTop: 12 }}><Note icon="alert">La plantilla oficial imprime 5 estudios superiores; los demás quedan guardados pero no aparecen en el PDF.</Note></div>}
      </Card>

      <Idiomas resume={resume} setResume={setResume} />
    </div>
  );
}
