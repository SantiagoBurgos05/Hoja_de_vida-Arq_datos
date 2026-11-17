import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, token, setUnauthorizedHandler, setWakingHandler } from "./lib/api.js";
import { useAutosave } from "./lib/useAutosave.js";
import { flushAll, hasPending } from "./lib/saver.js";
import { getPath } from "./lib/format.js";
import { Banner, BrandMark, ConflictBanner, Icon, PageHeader, SaveStatus, Spinner } from "./components/ui.jsx";
import Auth from "./pages/Auth.jsx";
import Personal from "./pages/Personal.jsx";
import Formacion from "./pages/Formacion.jsx";
import Experiencia from "./pages/Experiencia.jsx";
import Exportar from "./pages/Exportar.jsx";

// Secciones. `name` es el nombre accesible del enlace (lo usan lectores de pantalla y las pruebas E2E).
const TABS = [
  { key: "personal", n: "1", name: "1 · Datos personales", label: "Datos personales", icon: "user", eyebrow: "Sección 1 del formato",
    title: "Datos personales", desc: "Identificación, nacimiento y datos de contacto. Todo se guarda automáticamente mientras escribe." },
  { key: "formacion", n: "2", name: "2 · Formación", label: "Formación", icon: "cap", eyebrow: "Sección 2 del formato",
    title: "Formación académica", desc: "Educación básica, estudios superiores e idiomas. Verifique cada institución para poder adjuntar sus certificados." },
  { key: "experiencia", n: "3-4", name: "3-4 · Experiencia", label: "Experiencia", icon: "briefcase", eyebrow: "Secciones 3 y 4 del formato",
    title: "Experiencia laboral", desc: "Empleos actuales y anteriores. El tiempo total se calcula solo, sin contar dos veces los periodos que se cruzan." },
  { key: "exportar", n: "5-6", name: "5-6 · Exportar", label: "Exportar", icon: "pdf", eyebrow: "Secciones 5 y 6 del formato",
    title: "Revisar y exportar", desc: "Compruebe qué le falta y descargue el Formato Único de Hoja de Vida en PDF, listo para firmar." },
];
const PERSONAL_KEYS = ["primer_apellido", "nombres", "tipo_documento", "numero_documento", "sexo", "nacionalidad",
                       "nacimiento.fecha", "correspondencia.direccion", "correspondencia.telefono", "correspondencia.email"];

function useHashTab() {
  const read = () => (TABS.find((t) => `#/${t.key}` === window.location.hash) || TABS[0]).key;
  const [tab, setTab] = useState(read);
  useEffect(() => {
    const f = () => { flushAll(); setTab(read()); window.scrollTo({ top: 0 }); };   // guardar lo pendiente al cambiar de sección
    window.addEventListener("hashchange", f);
    return () => window.removeEventListener("hashchange", f);
  }, []);
  return tab;
}

function useProgress(resume, edu, work) {
  return useMemo(() => {
    if (!resume) return {};
    const filled = PERSONAL_KEYS.filter((k) => { const v = getPath(resume.personal || {}, k); return v !== undefined && v !== null && v !== ""; }).length;
    const eb = resume.education_basic || {};
    const basic = !!(eb.titulo_obtenido || eb.ultimo_grado);
    const personal = Math.round((filled / PERSONAL_KEYS.length) * 100);
    const formacion = (basic ? 50 : 0) + (edu.length ? 50 : 0);
    const experiencia = work.length ? 100 : 0;
    return {
      personal: { pct: personal, hint: `${personal}% completo` },
      formacion: { pct: formacion, hint: edu.length ? `${edu.length} ${edu.length === 1 ? "estudio" : "estudios"}` : basic ? "Básica lista" : "Sin estudios" },
      experiencia: { pct: experiencia, hint: work.length ? `${work.length} ${work.length === 1 ? "empleo" : "empleos"}` : "Sin empleos" },
      exportar: { pct: 0, hint: "PDF oficial" },
      overall: Math.round((personal + formacion + experiencia) / 3),
    };
  }, [resume?.personal, resume?.education_basic, edu.length, work.length]); // eslint-disable-line
}

function initials(user, resume) {
  const p = resume?.personal || {};
  const a = (p.nombres || "").trim()[0], b = (p.primer_apellido || "").trim()[0];
  return ((a || "") + (b || "")).toUpperCase() || user.email[0].toUpperCase();
}

function Workspace({ user, onLogout }) {
  const tab = useHashTab();
  const [resume, setResume] = useState(null);
  const [edu, setEdu] = useState([]);
  const [work, setWork] = useState([]);
  const [loadErr, setLoadErr] = useState("");
  const [leaving, setLeaving] = useState(false);

  const reloadResume = useCallback(async () => {
    const r = await api.get("/api/resume");
    setResume((cur) => (cur ? { ...cur, revision: r.revision, organization_status: r.organization_status, organization_id: r.organization_id } : r));
    return r;
  }, []);
  const reloadEdu = useCallback(async () => setEdu(await api.get("/api/education")), []);
  const reloadWork = useCallback(async () => setWork(await api.get("/api/work")), []);

  useEffect(() => {
    Promise.all([api.get("/api/resume"), api.get("/api/education"), api.get("/api/work")])
      .then(([r, e, w]) => { setResume(r); setEdu(e); setWork(w); })
      .catch((e) => setLoadErr(e.message));
  }, []);

  const resumeRef = useRef(resume);
  resumeRef.current = resume;
  const saveResume = useCallback(async () => {
    const v = resumeRef.current;
    const saved = await api.put("/api/resume", { revision: v.revision, personal: v.personal, education_basic: v.education_basic, languages: v.languages });
    resumeRef.current = { ...resumeRef.current, revision: saved.revision };   // un guardado encadenado usa ya la revisión nueva
    setResume((r) => ({ ...r, revision: saved.revision }));
  }, []);
  const editable = useMemo(() => (resume ? JSON.stringify([resume.personal, resume.education_basic, resume.languages]) : ""), [resume?.personal, resume?.education_basic, resume?.languages]); // eslint-disable-line
  const auto = useAutosave({ value: editable, loaded: !!resume, save: saveResume });
  const progress = useProgress(resume, edu, work);

  if (loadErr) return (
    <main><div className="card" style={{ maxWidth: 560, margin: "10vh auto" }}>
      <Banner kind="bad" role="alert">{loadErr}</Banner>
      <div style={{ marginTop: 14 }}><button onClick={() => window.location.reload()}><Icon name="refresh" />Reintentar</button></div>
    </div></main>
  );
  if (!resume) return <div className="loading"><div><BrandMark /><p>Cargando su hoja de vida…</p></div></div>;

  const conflict = auto.status === "conflict" && (
    <ConflictBanner onUseServer={async () => { const r = await api.get("/api/resume"); setResume(r); auto.clearConflict(); }}
      onKeepMine={async () => { const r = await api.get("/api/resume"); setResume((c) => ({ ...c, revision: r.revision })); auto.clearConflict(); setTimeout(auto.saveNow, 0); }} />
  );
  const header = (t, withSave) => (
    <>
      <PageHeader eyebrow={t.eyebrow} icon={t.icon} title={t.title}
        aside={withSave ? <SaveStatus status={auto.status} message={auto.message} onRetry={auto.saveNow} /> : null}>{t.desc}</PageHeader>
      {withSave && conflict && <div style={{ marginBottom: 18 }}>{conflict}</div>}
    </>
  );
  const [tP, tF, tE, tX] = TABS;

  return (
    <>
      <header className="app-bar">
        <div className="app-bar-top"><div className="app-bar-inner">
          <a className="brand" href="#/personal" aria-label="Hoja de Vida Digital, inicio"><BrandMark />
            <span className="brand-text"><span>Hoja de Vida <b>Digital</b></span><small>Formato Único · Persona natural</small></span></a>
          <div className="user">
            <span className="avatar" aria-hidden="true">{initials(user, resume)}</span>
            <span className="email" title={user.email}>{user.email}</span>
            <button className="ghost sm" disabled={leaving} onClick={async () => { setLeaving(true); await onLogout(); }}>
              {leaving ? <Spinner /> : <Icon name="logout" />}Salir
            </button>
          </div>
        </div></div>
        <nav className="stepper" aria-label="Secciones">
          {TABS.map((t) => {
            const pr = progress[t.key] || {};
            return (
              <a key={t.key} href={`#/${t.key}`} aria-label={t.name} aria-current={tab === t.key ? "page" : undefined}
                 className={pr.pct >= 100 && tab !== t.key ? "done" : ""}>
                <span className="step-n">{pr.pct >= 100 && tab !== t.key ? <Icon name="check" /> : t.n}</span>
                <span className="step-label"><strong>{t.label}</strong><small>{pr.hint}</small></span>
              </a>
            );
          })}
        </nav>
        <div className="progress" role="progressbar" aria-label="Avance de la hoja de vida" aria-valuemin={0} aria-valuemax={100} aria-valuenow={progress.overall}>
          <i style={{ width: `${progress.overall}%` }} />
        </div>
      </header>
      <main>
        {/* Las secciones editables permanecen montadas (solo se ocultan): cambiar de sección no descarta
            borradores ni temporizadores de autoguardado. */}
        <div hidden={tab !== "personal"}>{header(tP, true)}<Personal resume={resume} setResume={setResume} /></div>
        <div hidden={tab !== "formacion"}>{header(tF, true)}<Formacion resume={resume} setResume={setResume} reloadResume={reloadResume} edu={edu} reloadEdu={reloadEdu} /></div>
        <div hidden={tab !== "experiencia"}>{header(tE, false)}<Experiencia work={work} reloadWork={reloadWork} /></div>
        {tab === "exportar" && <div>{header(tX, false)}<Exportar resume={resume} edu={edu} work={work} progress={progress} /></div>}
      </main>
    </>
  );
}

export default function App() {
  const [user, setUser] = useState(null);
  const [checked, setChecked] = useState(false);
  const [waking, setWaking] = useState(false);

  const logout = useCallback(async () => {
    await flushAll();                                   // no perder cambios pendientes al salir
    try { await api.post("/api/auth/logout"); } catch { /* noop */ }
    token.clear(); setUser(null);
  }, []);
  useEffect(() => {
    const warn = (e) => { if (hasPending()) { flushAll(); e.preventDefault(); e.returnValue = ""; } };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, []);
  useEffect(() => {
    setUnauthorizedHandler(() => { token.clear(); setUser(null); });
    setWakingHandler(setWaking);
    if (!token.get()) { setChecked(true); return; }
    api.get("/api/auth/me").then(setUser).catch(() => token.clear()).finally(() => setChecked(true));
  }, []);

  return (
    <>
      {waking && (
        <div className="waking" role="status"><Spinner />El servidor está despertando (plan gratuito); puede tardar cerca de un minuto. Sus datos no se pierden.</div>
      )}
      {!checked ? <div className="loading"><div><BrandMark /><p>Cargando…</p></div></div>
        : user ? <Workspace user={user} onLogout={logout} /> : <Auth onLogin={setUser} />}
    </>
  );
}
