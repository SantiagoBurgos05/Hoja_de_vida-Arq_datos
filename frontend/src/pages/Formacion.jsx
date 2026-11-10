import React from "react";
import { api } from "../lib/api.js";
import { Section, Select, Text } from "../components/ui.jsx";
import RecordCard from "../components/RecordCard.jsx";
import EntityVerifier, { SOURCES } from "../components/EntityVerifier.jsx";
import Documents from "../components/Documents.jsx";
import { MODALIDADES, NIVELES, getPath, setPath } from "../lib/format.js";

function Basica({ resume, setResume, reloadResume }) {
  const eb = resume.education_basic || {};
  const set = (path, v) => setResume((r) => ({ ...r, education_basic: setPath(r.education_basic || {}, path, v) }));
  return (
    <div className="record">
      <h3>Educación básica y media</h3>
      <div className="grid">
        <Select label="Último grado aprobado" value={eb.ultimo_grado == null ? "" : String(eb.ultimo_grado)} onChange={(v) => set("ultimo_grado", v == null ? null : Number(v))}
                options={Array.from({ length: 11 }, (_, i) => [String(i + 1), `${i + 1}º`])} />
        <Text label="Título obtenido" value={eb.titulo_obtenido} onChange={(v) => set("titulo_obtenido", v)} />
        <Text label="Mes de grado (1-12)" type="number" value={getPath(eb, "fecha_grado.mes")} onChange={(v) => set("fecha_grado.mes", v === "" ? null : Number(v))} />
        <Text label="Año de grado" type="number" value={getPath(eb, "fecha_grado.anio")} onChange={(v) => set("fecha_grado.anio", v === "" ? null : Number(v))} />
        <Text label="Colegio (declarado)" value={eb.institucion_declarada} onChange={(v) => set("institucion_declarada", v)} wide />
      </div>
      <EntityVerifier recordType="education_basic" recordId={resume.id} sources={SOURCES.education_basic} status={resume.organization_status || "pending"}
                      organization={null} onChanged={reloadResume} />
      <Documents recordType="education_basic" recordId={resume.id} orgStatus={resume.organization_status || "pending"} onChanged={reloadResume} />
    </div>
  );
}

function Idiomas({ resume, setResume }) {
  const langs = resume.languages || [];
  const upd = (i, k, v) => setResume((r) => ({ ...r, languages: langs.map((l, j) => (j === i ? { ...l, [k]: v } : l)) }));
  return (
    <div className="record">
      <h3>Idiomas diferentes al español</h3>
      <p className="muted">R = regular, B = bien, MB = muy bien. La plantilla oficial imprime hasta 2 idiomas.</p>
      {langs.map((l, i) => (
        <div className="grid" key={i}>
          <Text label="Idioma" value={l.idioma} onChange={(v) => upd(i, "idioma", v)} />
          {["habla", "lee", "escribe"].map((k) => <Select key={k} label={`Lo ${k}`} value={l[k]} onChange={(v) => upd(i, k, v)} options={NIVELES.map((n) => [n, n])} />)}
          <button className="link danger" onClick={() => setResume((r) => ({ ...r, languages: langs.filter((_, j) => j !== i) }))}>Quitar</button>
        </div>
      ))}
      <button onClick={() => setResume((r) => ({ ...r, languages: [...langs, { idioma: "", habla: "B", lee: "B", escribe: "B" }] }))}>Agregar idioma</button>
    </div>
  );
}

export default function Formacion({ resume, setResume, reloadResume, edu, reloadEdu }) {
  async function add() { await api.post("/api/education", { modalidad: "UN" }); reloadEdu(); }
  async function del(id) { await api.del(`/api/education/${id}`); reloadEdu(); }
  return (
    <Section n="2" title="Formación académica">
      <Basica resume={resume} setResume={setResume} reloadResume={reloadResume} />
      <h3>Educación superior (orden cronológico)</h3>
      {edu.map((r) => (
        <RecordCard key={r.id} path="/api/education" recordType="education_higher" record={r} onDelete={del} onRefresh={reloadEdu}
          title={(f) => `${MODALIDADES[f.modalidad] || "Estudio"} — ${f.nombre_estudios || "sin nombre"}`} sourcesFor={() => SOURCES.education_higher}
          renderFields={(f, p) => (<>
            <Select label="Modalidad" value={f.modalidad} onChange={(v) => p("modalidad", v)} options={Object.entries(MODALIDADES).map(([k, v]) => [k, `${k} – ${v}`])} />
            <Text label="Nombre de los estudios o título" value={f.nombre_estudios} onChange={(v) => p("nombre_estudios", v)} wide />
            <Text label="Institución (declarada)" value={f.institucion_declarada} onChange={(v) => p("institucion_declarada", v)} wide />
            <Text label="Semestres aprobados" type="number" value={f.semestres_aprobados} onChange={(v) => p("semestres_aprobados", v === "" ? null : Number(v))} />
            <Select label="Graduado" value={f.graduado == null ? "" : f.graduado ? "si" : "no"} onChange={(v) => p("graduado", v == null ? null : v === "si")} options={[["si", "Sí"], ["no", "No"]]} />
            <Text label="Mes de terminación" type="number" value={f.terminacion?.mes} onChange={(v) => p("terminacion", { ...f.terminacion, mes: v === "" ? null : Number(v) })} />
            <Text label="Año de terminación" type="number" value={f.terminacion?.anio} onChange={(v) => p("terminacion", { ...f.terminacion, anio: v === "" ? null : Number(v) })} />
            <Text label="N.º de tarjeta profesional" value={f.tarjeta_profesional} onChange={(v) => p("tarjeta_profesional", v)} />
          </>)} />
      ))}
      <button onClick={add}>Agregar estudio superior</button>
      <Idiomas resume={resume} setResume={setResume} />
    </Section>
  );
}
