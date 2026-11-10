import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, token, setUnauthorizedHandler, setWakingHandler } from "./lib/api.js";
import { useAutosave } from "./lib/useAutosave.js";
import { ConflictBanner, SaveStatus } from "./components/ui.jsx";
import Auth from "./pages/Auth.jsx";
import Personal from "./pages/Personal.jsx";
import Formacion from "./pages/Formacion.jsx";
import Experiencia from "./pages/Experiencia.jsx";
import Exportar from "./pages/Exportar.jsx";

const TABS = [["personal", "1 · Datos personales"], ["formacion", "2 · Formación"], ["experiencia", "3-4 · Experiencia"], ["exportar", "5-6 · Exportar"]];

function useHashTab() {
  const read = () => (TABS.find(([k]) => `#/${k}` === window.location.hash) || TABS[0])[0];
  const [tab, setTab] = useState(read);
  useEffect(() => { const f = () => setTab(read()); window.addEventListener("hashchange", f); return () => window.removeEventListener("hashchange", f); }, []);
  return tab;
}

function Workspace({ user, onLogout }) {
  const tab = useHashTab();
  const [resume, setResume] = useState(null);
  const [edu, setEdu] = useState([]);
  const [work, setWork] = useState([]);
  const [loadErr, setLoadErr] = useState("");

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
    setResume((r) => ({ ...r, revision: saved.revision }));
  }, []);
  const editable = useMemo(() => (resume ? JSON.stringify([resume.personal, resume.education_basic, resume.languages]) : ""), [resume?.personal, resume?.education_basic, resume?.languages]); // eslint-disable-line
  const auto = useAutosave({ value: editable, loaded: !!resume, save: saveResume });

  if (loadErr) return <main className="card"><p className="banner bad" role="alert">{loadErr}</p><button onClick={() => window.location.reload()}>Reintentar</button></main>;
  if (!resume) return <main className="card"><p>Cargando su hoja de vida…</p></main>;

  return (
    <>
      <header className="top">
        <strong>Hoja de Vida Digital</strong>
        <nav aria-label="Secciones">{TABS.map(([k, l]) => <a key={k} href={`#/${k}`} aria-current={tab === k ? "page" : undefined}>{l}</a>)}</nav>
        <span className="muted">{user.email}</span>
        <button className="link" onClick={onLogout}>Salir</button>
      </header>
      <main>
        {(tab === "personal" || tab === "formacion") && (
          <>
            <SaveStatus status={auto.status} message={auto.message} onRetry={auto.saveNow} />
            {auto.status === "conflict" && <ConflictBanner onUseServer={async () => { const r = await api.get("/api/resume"); setResume(r); auto.clearConflict(); }}
              onKeepMine={async () => { const r = await api.get("/api/resume"); setResume((c) => ({ ...c, revision: r.revision })); auto.clearConflict(); setTimeout(auto.saveNow, 0); }} />}
          </>
        )}
        {tab === "personal" && <Personal resume={resume} setResume={setResume} />}
        {tab === "formacion" && <Formacion resume={resume} setResume={setResume} reloadResume={reloadResume} edu={edu} reloadEdu={reloadEdu} />}
        {tab === "experiencia" && <Experiencia work={work} reloadWork={reloadWork} />}
        {tab === "exportar" && <Exportar />}
      </main>
    </>
  );
}

export default function App() {
  const [user, setUser] = useState(null);
  const [checked, setChecked] = useState(false);
  const [waking, setWaking] = useState(false);

  const logout = useCallback(async () => { try { await api.post("/api/auth/logout"); } catch { /* noop */ } token.clear(); setUser(null); }, []);
  useEffect(() => {
    setUnauthorizedHandler(() => { token.clear(); setUser(null); });
    setWakingHandler(setWaking);
    if (!token.get()) { setChecked(true); return; }
    api.get("/api/auth/me").then(setUser).catch(() => token.clear()).finally(() => setChecked(true));
  }, []);

  return (
    <>
      {waking && <div className="banner warn" role="status">El servidor está despertando (plan gratuito); puede tardar cerca de un minuto. Sus datos no se pierden.</div>}
      {!checked ? <main className="card">Cargando…</main> : user ? <Workspace user={user} onLogout={logout} /> : <Auth onLogin={setUser} />}
    </>
  );
}
