import React from "react";

export function Field({ label, children, hint, wide }) {
  return (
    <label className={`field${wide ? " wide" : ""}`}>
      <span>{label}</span>
      {children}
      {hint && <small>{hint}</small>}
    </label>
  );
}

export function Text({ label, value, onChange, type = "text", maxLength, wide, hint, ...rest }) {
  return (
    <Field label={label} wide={wide} hint={hint}>
      <input type={type} value={value ?? ""} maxLength={maxLength} onChange={(e) => onChange(e.target.value)} {...rest} />
    </Field>
  );
}

export function Select({ label, value, onChange, options, wide }) {
  return (
    <Field label={label} wide={wide}>
      <select value={value ?? ""} onChange={(e) => onChange(e.target.value === "" ? null : e.target.value)}>
        <option value="">—</option>
        {options.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
      </select>
    </Field>
  );
}

export function Badge({ kind, children }) {
  return <span className={`badge ${kind}`}>{children}</span>;
}

export function SaveStatus({ status, message, onRetry }) {
  const map = {
    idle: ["", ""], dirty: ["Cambios sin guardar…", "warn"], saving: ["Guardando…", "info"], saved: ["Guardado", "ok"],
    offline: ["Sin conexión — sus cambios siguen en pantalla", "bad"], error: ["No se pudo guardar", "bad"], conflict: ["Conflicto de versión", "bad"],
  };
  const [text, cls] = map[status] || ["", ""];
  return (
    <div className={`savestatus ${cls}`} role="status" aria-live="polite">
      {text}{message && status !== "saved" ? ` — ${message}` : ""}
      {(status === "offline" || status === "error") && <button className="link" onClick={onRetry}>Reintentar</button>}
    </div>
  );
}

export function ConflictBanner({ onUseServer, onKeepMine }) {
  return (
    <div className="banner bad" role="alert">
      <strong>Esta hoja de vida se modificó en otra sesión.</strong>
      <p>Puede cargar la versión del servidor (descarta lo que acaba de escribir) o conservar la suya y sobrescribir.</p>
      <button onClick={onUseServer}>Cargar versión del servidor</button>{" "}
      <button className="secondary" onClick={onKeepMine}>Conservar la mía y guardar</button>
    </div>
  );
}

export function Section({ n, title, children }) {
  return (
    <section className="card">
      <h2><span className="num">{n}</span>{title}</h2>
      {children}
    </section>
  );
}
