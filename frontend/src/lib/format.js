export const MODALIDADES = { TC: "Técnica", TL: "Tecnológica", TE: "Tecnológica especializada", UN: "Universitaria", ES: "Especialización", MG: "Maestría o magíster", DOC: "Doctorado o PhD" };
export const NIVELES = ["R", "B", "MB"];

export function setPath(obj, path, value) {
  const keys = path.split(".");
  const copy = Array.isArray(obj) ? [...obj] : { ...obj };
  let cur = copy;
  keys.forEach((k, i) => {
    if (i === keys.length - 1) cur[k] = value;
    else { cur[k] = { ...(cur[k] || {}) }; cur = cur[k]; }
  });
  return copy;
}
export const getPath = (obj, path) => path.split(".").reduce((o, k) => (o == null ? undefined : o[k]), obj);

// Estado de la entidad (verificación) en lenguaje claro. Verificar la entidad NO acredita nada más.
export function orgLabel(status) {
  return ({
    verified: "Entidad verificada en fuente oficial",
    pending: "Entidad sin verificar",
    not_found: "No se encontró en la fuente oficial",
    error: "No se pudo consultar la fuente (borrador conservado)",
  })[status] || "Entidad sin verificar";
}
export function recordLabel(status) {
  return ({ draft: "Borrador", declared: "Antecedente declarado", supported: "Con soporte adjunto" })[status] || "Borrador";
}
export const fmtBytes = (n) => (n >= 1048576 ? `${(n / 1048576).toFixed(1)} MB` : `${Math.max(1, Math.round(n / 1024))} KB`);
export const MAX_UPLOAD = 5 * 1024 * 1024;
export function checkFile(file) {
  if (!file) return "Seleccione un archivo.";
  if (file.size > MAX_UPLOAD) return "El archivo supera 5 MB.";
  if (!["application/pdf", "image/jpeg", "image/png"].includes(file.type)) return "Solo se permiten PDF, JPG o PNG.";
  return null;
}
