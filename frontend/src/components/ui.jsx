import React from "react";

// ---------------------------------------------------------------- íconos (SVG en línea, sin dependencias)
const PATHS = {
  user: ["M4 21c0-4 3.6-6.5 8-6.5s8 2.5 8 6.5", { c: [12, 8, 4] }],
  cap: ["M22 9.5 12 4.5 2 9.5l10 5 10-5Z", "M6 11.6v5.2c3.6 2.4 8.4 2.4 12 0v-5.2", "M22 9.5v5"],
  briefcase: [{ r: [3, 7, 18, 13, 2] }, "M8 7V5.5A2.5 2.5 0 0 1 10.5 3h3A2.5 2.5 0 0 1 16 5.5V7", "M3 12.5h18"],
  pdf: ["M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8Z", "M14 3v5h5", "M12 11v6", "m9 14 3 3 3-3"],
  check: ["m5 12.5 4.5 4.5L19 7.5"],
  shield: ["M12 3 20 6v6c0 5-3.5 8.2-8 9-4.5-.8-8-4-8-9V6Z", "m9 12 2 2 4-4"],
  search: [{ c: [11, 11, 7] }, "m20 20-3.5-3.5"],
  upload: ["M12 16V4", "m7 9 5-5 5 5", "M5 20h14"],
  file: ["M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8Z", "M14 3v5h5", "M9 13h6", "M9 17h4"],
  trash: ["M4 7h16", "M10 11v6", "M14 11v6", "M6 7l1 13h10l1-13", "M9 7V4h6v3"],
  plus: ["M12 5v14", "M5 12h14"],
  alert: ["M12 3.5 22 20.5H2Z", "M12 10v4", "M12 17.3v.2"],
  clock: [{ c: [12, 12, 9] }, "M12 7v5l3 2"],
  cloud: ["M7 18a5 5 0 0 1-.4-10A6 6 0 0 1 18 9.5 4.3 4.3 0 0 1 17.5 18Z"],
  logout: ["M15 4h3a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-3", "m10 8-4 4 4 4", "M6 12h10"],
  eye: ["M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12Z", { c: [12, 12, 3] }],
  eyeOff: ["M2 12s3.6-7 10-7c2 0 3.8.7 5.2 1.6M22 12s-3.6 7-10 7c-2 0-3.8-.7-5.2-1.6", "M3 3l18 18"],
  building: [{ r: [4, 3, 16, 18, 1.5] }, "M9 7h2", "M13 7h2", "M9 11h2", "M13 11h2", "M10 21v-4h4v4"],
  school: ["m3 10 9-6 9 6", "M5 10v8", "M19 10v8", "M9.5 10v8", "M14.5 10v8", "M3 20h18"],
  info: [{ c: [12, 12, 9] }, "M12 11v5", "M12 7.6v.2"],
  lock: [{ r: [5, 11, 14, 10, 2] }, "M8 11V8a4 4 0 0 1 8 0v3"],
  globe: [{ c: [12, 12, 9] }, "M3 12h18", "M12 3c3 3.2 3 14.8 0 18-3-3.2-3-14.8 0-18Z"],
  mail: [{ r: [3, 5, 18, 14, 2] }, "m3 7 9 6 9-6"],
  doc: ["M7 3h7l5 5v11a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Z", "M14 3v5h5"],
  x: ["M6 6l12 12", "M18 6 6 18"],
  calendar: [{ r: [3, 5, 18, 16, 2] }, "M3 10h18", "M8 3v4", "M16 3v4"],
  sparkle: ["M12 3v4", "M12 17v4", "M3 12h4", "M17 12h4", "m6 6 2.5 2.5", "m15.5 15.5 2.5 2.5", "m6 18 2.5-2.5", "m15.5 8.5 2.5-2.5"],
  map: ["M12 21s-7-6.2-7-11.5A7 7 0 0 1 19 9.5C19 14.8 12 21 12 21Z", { c: [12, 9.5, 2.5] }],
  id: [{ r: [3, 5, 18, 14, 2] }, { c: [9, 11, 2] }, "M6 16c.6-1.6 1.6-2.4 3-2.4s2.4.8 3 2.4", "M15 10h3", "M15 13.5h3"],
  phone: ["M5 4h3l2 5-2.5 1.5a11 11 0 0 0 6 6L15 14l5 2v3a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2Z"],
  download: ["M12 4v12", "m7 11 5 5 5-5", "M5 20h14"],
  refresh: ["M20 11a8 8 0 1 0-2.3 5.7", "M20 4v7h-7"],
  arrow: ["M5 12h14", "m13 6 6 6-6 6"],
};

export function Icon({ name, size, className = "", title }) {
  const parts = PATHS[name] || [];
  return (
    <svg className={`icon ${size || ""} ${className}`} viewBox="0 0 24 24" aria-hidden={title ? undefined : "true"} role={title ? "img" : undefined}>
      {title && <title>{title}</title>}
      {parts.map((p, i) => typeof p === "string" ? <path key={i} d={p} />
        : p.c ? <circle key={i} cx={p.c[0]} cy={p.c[1]} r={p.c[2]} />
        : <rect key={i} x={p.r[0]} y={p.r[1]} width={p.r[2]} height={p.r[3]} rx={p.r[4]} />)}
    </svg>
  );
}

export function BrandMark() {
  return <span className="brand-mark"><Icon name="doc" /></span>;
}

// ---------------------------------------------------------------- formularios
// `required`: asterisco visible (fuera del nombre accesible) y borde ámbar mientras esté vacío.
export function Field({ label, children, hint, wide, required, missing }) {
  return (
    <label className={`field${wide ? " wide" : ""}${required && missing ? " missing" : ""}`}>
      <span>{label}{required && <span className="req" aria-hidden="true">*</span>}</span>
      {children}
      {hint && <small>{hint}</small>}
    </label>
  );
}

export function Text({ label, value, onChange, type = "text", maxLength, wide, hint, required, ...rest }) {
  return (
    <Field label={label} wide={wide} hint={hint} required={required} missing={value == null || value === ""}>
      <input type={type} value={value ?? ""} maxLength={maxLength} onChange={(e) => onChange(e.target.value)}
             aria-required={required || undefined} aria-label={required && typeof label === "string" ? label : undefined} {...rest} />
    </Field>
  );
}

export function Select({ label, value, onChange, options, wide, hint, required, placeholder = "Seleccione…" }) {
  return (
    <Field label={label} wide={wide} hint={hint} required={required} missing={value == null || value === ""}>
      <select value={value ?? ""} onChange={(e) => onChange(e.target.value === "" ? null : e.target.value)}
              aria-required={required || undefined} aria-label={required && typeof label === "string" ? label : undefined}>
        <option value="">{placeholder}</option>
        {options.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
      </select>
    </Field>
  );
}

// Mes como lista (más claro que escribir un número del 1 al 12). Guarda el número.
export const MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"];
export function MonthSelect({ label, value, onChange, ...rest }) {
  return <Select label={label} value={value == null ? "" : String(value)} onChange={(v) => onChange(v == null ? null : Number(v))}
                 options={MESES.map((m, i) => [String(i + 1), m])} {...rest} />;
}

// Leyenda de campos obligatorios.
export function RequiredLegend() {
  return <p className="legend"><span className="req" aria-hidden="true">*</span>Campo obligatorio. Los cambios se guardan automáticamente.</p>;
}

// Título de un grupo de campos dentro de una cuadrícula.
export function FieldGroup({ children }) {
  return <div className="fieldset-title" role="heading" aria-level={4}>{children}</div>;
}

// Selector de nivel R / B / MB como grupo de opciones (más rápido que una lista desplegable).
export function LevelPicker({ label, value, onChange, name }) {
  const opts = [["R", "Regular"], ["B", "Bien"], ["MB", "Muy bien"]];
  return (
    <div className="lvl" role="radiogroup" aria-label={label}>
      <span>{label}</span>
      <div className="levels">
        {opts.map(([v, t]) => (
          <label key={v} title={t}>
            <input type="radio" name={name} value={v} checked={value === v} onChange={() => onChange(v)} aria-label={`${label}: ${t}`} />
            <span>{v}</span>
          </label>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------- estados y avisos
export function Badge({ kind, children, plain }) {
  return <span className={`badge ${kind}${plain ? " plain" : ""}`}>{children}</span>;
}

export function Banner({ kind = "info", icon, children, role }) {
  const ic = icon || { bad: "alert", warn: "alert", ok: "check", info: "info" }[kind];
  return <div className={`banner ${kind}`} role={role}><Icon name={ic} /><div>{children}</div></div>;
}

export function Note({ icon = "info", children }) {
  return <p className="note"><Icon name={icon} /><span>{children}</span></p>;
}

export function SaveStatus({ status, message, onRetry }) {
  const map = {
    idle: ["", ""], dirty: ["Cambios sin guardar…", "warn"], saving: ["Guardando…", "info"], saved: ["Guardado", "ok"],
    offline: ["Sin conexión — sus cambios siguen en pantalla", "bad"], error: ["No se pudo guardar", "bad"], conflict: ["Conflicto de versión", "bad"],
  };
  const [text, cls] = map[status] || ["", ""];
  return (
    <div className={`savestatus ${cls}`} role="status" aria-live="polite">
      {text && <span className="dot" aria-hidden="true" />}
      {text && <span>{text}</span>}
      {text && message && status !== "saved" && <span className="muted small">{message}</span>}
      {(status === "offline" || status === "error") && <button className="link" onClick={onRetry}>Reintentar</button>}
    </div>
  );
}

export function ConflictBanner({ onUseServer, onKeepMine }) {
  return (
    <div className="banner bad" role="alert">
      <Icon name="alert" />
      <div>
        <p><strong>Esta hoja de vida se modificó en otra sesión.</strong></p>
        <p>Puede cargar la versión del servidor (descarta lo que acaba de escribir) o conservar la suya y sobrescribir.</p>
        <div className="actions">
          <button className="sm" onClick={onUseServer}>Cargar versión del servidor</button>
          <button className="secondary sm" onClick={onKeepMine}>Conservar la mía y guardar</button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------- estructura
export function PageHeader({ eyebrow, icon, title, children, aside }) {
  return (
    <div className="page-head">
      <div>
        {eyebrow && <div className="eyebrow">{icon && <Icon name={icon} />}{eyebrow}</div>}
        <h1>{title}</h1>
        {children && <p>{children}</p>}
      </div>
      {aside}
    </div>
  );
}

export function Card({ icon, tone, title, desc, actions, children, as: Tag = "section" }) {
  return (
    <Tag className="card">
      {(title || icon) && (
        <div className="card-head">
          {icon && <span className={`tile ${tone || ""}`}><Icon name={icon} size="lg" /></span>}
          <div>
            <h2>{title}</h2>
            {desc && <p>{desc}</p>}
          </div>
          {actions && <div className="spacer">{actions}</div>}
        </div>
      )}
      {children}
    </Tag>
  );
}

// Compatibilidad: secciones numeradas antiguas.
export function Section({ n, title, children, icon, desc }) {
  return <Card icon={icon} title={title} desc={desc}>{children}</Card>;
}

export function EmptyState({ icon, title, children, action }) {
  return (
    <div className="empty">
      <span className="tile"><Icon name={icon} size="xl" /></span>
      <h3>{title}</h3>
      <p>{children}</p>
      {action}
    </div>
  );
}

export function Spinner() { return <span className="spinner" aria-hidden="true" />; }
