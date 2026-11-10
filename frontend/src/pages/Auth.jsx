import React, { useState } from "react";
import { api, token } from "../lib/api.js";

export default function Auth({ onLogin }) {
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setErr(""); setBusy(true);
    try {
      if (mode === "register") await api.post("/api/auth/register", { email, password });
      const r = await api.post("/api/auth/login", { email, password });
      token.set(r.token); onLogin(r.user);
    } catch (ex) {
      setErr(ex.status === 429 ? "Demasiados intentos. Espere unos minutos." : ex.status === 422 ? "Revise el correo y use una contraseña de al menos 10 caracteres." : ex.message);
    } finally { setBusy(false); }
  }

  return (
    <main className="auth card">
      <h1>Hoja de Vida Digital</h1>
      <p className="muted">Formato Único de Hoja de Vida – Persona Natural (Colombia). Sus datos quedan guardados y podrá retomarlos en cualquier momento.</p>
      <form onSubmit={submit}>
        <label className="field"><span>Correo electrónico</span><input type="email" required autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} /></label>
        <label className="field"><span>Contraseña (mínimo 10 caracteres)</span><input type="password" required minLength={10} autoComplete={mode === "login" ? "current-password" : "new-password"} value={password} onChange={(e) => setPassword(e.target.value)} /></label>
        {err && <p className="banner bad" role="alert">{err}</p>}
        <button disabled={busy}>{mode === "login" ? "Iniciar sesión" : "Crear cuenta"}</button>{" "}
        <button type="button" className="link" onClick={() => setMode(mode === "login" ? "register" : "login")}>{mode === "login" ? "Crear una cuenta" : "Ya tengo cuenta"}</button>
      </form>
      <p className="note">Aviso: no suba documentos reales en ambientes de prueba. Esta aplicación no autentica certificados.</p>
    </main>
  );
}
