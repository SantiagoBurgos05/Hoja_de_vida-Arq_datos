// Guardado diferido y serializado, independiente de React (se prueba en node).
//
// - schedule(): marca cambios pendientes y (re)programa el guardado tras `delay` ms.
// - flush(): guarda YA lo pendiente. Si hay un guardado en curso, no lanza otro en paralelo
//   (evitaría un 409 por revisión contra sí mismo): encola una vuelta más y devuelve la misma promesa.
// - dispose(): al desmontar NO descarta cambios: si había algo pendiente lo guarda y luego se da de baja.
// Todos los guardadores vivos quedan en un registro: flushAll() permite guardar antes de navegar,
// exportar o cerrar sesión, y hasPending() alimenta el aviso de `beforeunload`.

const registry = new Set();

export function createSaver({ save, onStatus = () => {}, delay = 1200 }) {
  let timer = null;
  let dirty = false;
  let inflight = null;
  let disposed = false;

  const saver = {
    get dirty() { return dirty; },
    get busy() { return inflight !== null; },
    pending() { return dirty || inflight !== null; },

    schedule() {
      dirty = true;
      onStatus("dirty");
      clearTimeout(timer);
      timer = setTimeout(() => { saver.flush(); }, delay);
    },

    flush() {
      clearTimeout(timer); timer = null;
      if (inflight) return inflight;          // la vuelta en curso recogerá `dirty` al terminar
      if (!dirty) return Promise.resolve(true);
      inflight = (async () => {
        let ok = true;
        while (dirty) {
          dirty = false;
          onStatus("saving");
          try {
            await save();
            if (!dirty) onStatus("saved");
          } catch (e) {
            ok = false;
            dirty = e?.status === 0;           // sin conexión: el cambio sigue pendiente en pantalla
            onStatus("error", e);
            break;
          }
        }
        return ok;
      })().finally(() => {
        inflight = null;
        if (disposed && !dirty) registry.delete(saver);
      });
      return inflight;
    },

    saveNow() {                                // reintento explícito (también tras un error o conflicto)
      dirty = true;
      return saver.flush();
    },

    revive() {                                 // React StrictMode monta, desmonta y vuelve a montar
      disposed = false;
      registry.add(saver);
    },

    dispose() {
      disposed = true;
      if (dirty || inflight) { saver.flush(); return; }   // se da de baja al terminar
      registry.delete(saver);
    },
  };
  registry.add(saver);
  return saver;
}

export async function flushAll() {
  const results = await Promise.all([...registry].map((s) => s.flush().catch(() => false)));
  return results.every(Boolean);
}

export const hasPending = () => [...registry].some((s) => s.pending());

export const _registrySize = () => registry.size;   // solo pruebas
