import React, { useState } from "react";
import { api, token } from "../lib/api.js";
import { Banner, BrandMark, Icon, Note, Spinner } from "../components/ui.jsx";

const FEATURES = [
  ["cloud", "Se guarda solo", "Cada cambio queda guardado y lo retoma en cualquier sesión o dispositivo."],
  ["shield", "Entidades verificadas", "Universidades, colegios, empresas y entidades públicas en fuentes oficiales."],
  ["lock", "Certificados privados", "Sus soportes quedan en almacenamiento privado y solo usted los descarga."],
  ["pdf", "Formato oficial en PDF", "Exporta el Formato Único de Hoja de Vida listo para imprimir y firmar."],
];
const MIN = 10;

export default function Auth({ onLogin }) {
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const register = mode === "register";

  async function submit(e) {
    e.preventDefault();
    setErr(""); setBusy(true);
    try {
      if (register) await api.post("/api/auth/register", { email, password });
      const r = await api.post("/api/auth/login", { email, password });
      token.set(r.token); onLogin(r.user);
    } catch (ex) {
      setErr(ex.status === 429 ? "Demasiados intentos. Espere unos minutos e intente de nuevo."
        : ex.status === 422 ? "Revise el correo y use una contraseña de al menos 10 caracteres."
        : ex.status === 401 ? "Correo o contraseña incorrectos."
        : ex.message);
    } finally { setBusy(false); }
  }
  const switchTo = (m) => { setMode(m); setErr(""); };
  const pct = Math.min(100, Math.round((password.length / MIN) * 100));

  return (
    <div className="auth-shell">
      <aside className="auth-hero">
        <div className="brand"><BrandMark /> Hoja de Vida <b>Digital</b></div>
        <h1>Su hoja de vida, <span>verificada</span> y siempre a mano</h1>
        <p>Diligencie el Formato Único de Hoja de Vida – Persona Natural (Colombia). Sus datos quedan guardados y podrá retomarlos en cualquier momento.</p>
        <ul className="features">
          {FEATURES.map(([ic, t, d]) => (
            <li key={t}><span className="tile"><Icon name={ic} size="lg" /></span><div><strong>{t}</strong><span>{d}</span></div></li>
          ))}
        </ul>
        <p className="legal">Proyecto académico · Arquitectura de software · Minuto de Dios</p>
      </aside>

      <main className="auth-panel">
        <div className="auth-card">
          <div className="segmented" role="group" aria-label="Tipo de acceso">
            <button type="button" aria-pressed={!register} onClick={() => switchTo("login")}>Ingresar</button>
            <button type="button" aria-pressed={register} onClick={() => switchTo("register")}>Crear una cuenta</button>
          </div>
          <h2>{register ? "Cree su cuenta" : "Bienvenido de nuevo"}</h2>
          <p>{register ? "Solo necesita un correo y una contraseña. Empiece a diligenciar en segundos." : "Ingrese para continuar con su hoja de vida."}</p>

          <form onSubmit={submit}>
            <div className="field">
              <label htmlFor="email" className="field-label">Correo electrónico</label>
              <div className="input-wrap">
                <Icon name="mail" />
                <input id="email" type="email" required autoComplete="username" placeholder="nombre@correo.com" value={email} onChange={(e) => setEmail(e.target.value)} />
              </div>
            </div>
            <div className="field">
              <label htmlFor="pw" className="field-label">Contraseña (mínimo 10 caracteres)</label>
              <div className="input-wrap">
                <Icon name="lock" />
                <input id="pw" type={show ? "text" : "password"} required minLength={MIN} autoComplete={register ? "new-password" : "current-password"}
                       value={password} onChange={(e) => setPassword(e.target.value)} />
                <button type="button" className="ghost reveal" onClick={() => setShow((v) => !v)} aria-label={show ? "Ocultar la clave" : "Mostrar la clave"} aria-pressed={show}>
                  <Icon name={show ? "eyeOff" : "eye"} />
                </button>
              </div>
              {register && (
                <div className={`pw-meter${password.length >= MIN ? " ok" : ""}`} aria-live="polite">
                  <div className="bar"><i style={{ width: `${pct}%` }} /></div>
                  <span>{password.length >= MIN ? "Longitud suficiente" : `${password.length}/${MIN} caracteres`}</span>
                </div>
              )}
            </div>
            {err && <Banner kind="bad" role="alert">{err}</Banner>}
            <button className="block" disabled={busy}>
              {busy && <Spinner />}{register ? "Crear cuenta" : "Iniciar sesión"}
            </button>
          </form>
          <div style={{ marginTop: 18 }}>
            <Note>Aviso: no suba documentos reales en ambientes de prueba. Esta aplicación no autentica certificados.</Note>
          </div>
        </div>
      </main>
    </div>
  );
}
