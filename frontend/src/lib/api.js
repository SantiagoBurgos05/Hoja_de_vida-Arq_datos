// Cliente de la API. El navegador NUNCA habla con MongoDB ni con el almacenamiento.
// Token de sesión en sessionStorage (se borra al cerrar la pestaña). Compromiso documentado en docs/seguridad.md:
// protege de CSRF (no hay cookies) pero un XSS podría leerlo; por eso no se renderiza HTML de usuario con dangerouslySetInnerHTML.
export const API = (import.meta.env?.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");
const KEY = "hv_token";

export class ApiError extends Error {
  constructor(status, detail) {
    super(typeof detail === "string" ? detail : detail?.message || `Error ${status}`);
    this.status = status;
    this.detail = detail;
    this.code = typeof detail === "object" ? detail?.code : undefined;
  }
}

export const token = {
  get: () => { try { return sessionStorage.getItem(KEY); } catch { return null; } },
  set: (t) => { try { sessionStorage.setItem(KEY, t); } catch { /* sin almacenamiento: sesión solo en memoria */ } },
  clear: () => { try { sessionStorage.removeItem(KEY); } catch { /* noop */ } },
};

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let onUnauthorized = () => {};
export const setUnauthorizedHandler = (fn) => { onUnauthorized = fn; };
let onWaking = () => {};
export const setWakingHandler = (fn) => { onWaking = fn; };

// Render (plan gratuito) se duerme: reintentar lecturas ante errores de red/502/503/504 con espera creciente.
export async function request(method, path, { json, form, headers = {}, raw = false } = {}) {
  const h = { ...headers };
  const t = token.get();
  if (t) h.Authorization = `Bearer ${t}`;
  let body;
  if (json !== undefined) { h["Content-Type"] = "application/json"; body = JSON.stringify(json); }
  if (form) body = form;
  const attempts = method === "GET" ? 4 : 1;
  let lastErr;
  for (let i = 0; i < attempts; i++) {
    try {
      const res = await fetch(`${API}${path}`, { method, headers: h, body });
      if ([502, 503, 504].includes(res.status) && i < attempts - 1) { onWaking(true); await sleep(2000 * (i + 1)); continue; }
      onWaking(false);
      if (res.status === 401 && t) onUnauthorized();
      if (!res.ok) {
        let d; try { d = (await res.json()).detail; } catch { d = res.statusText; }
        throw new ApiError(res.status, d);
      }
      if (raw) return res;
      return res.status === 204 ? null : await res.json();
    } catch (e) {
      if (e instanceof ApiError) throw e;
      lastErr = e;
      if (i < attempts - 1) { onWaking(true); await sleep(2000 * (i + 1)); continue; }
    }
  }
  onWaking(false);
  throw new ApiError(0, "Sin conexión con el servidor. Sus cambios no se han perdido: siguen en pantalla.");
}

export const api = {
  get: (p) => request("GET", p),
  post: (p, json) => request("POST", p, { json }),
  put: (p, json) => request("PUT", p, { json }),
  del: (p) => request("DELETE", p),
};

export async function downloadBlob(path, filename) {
  const res = await request("GET", path, { raw: true });
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename; document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 5000);
  return res.headers.get("X-Export-Warnings");
}
