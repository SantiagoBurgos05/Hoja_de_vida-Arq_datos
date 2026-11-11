import { useEffect, useRef, useState } from "react";
import { createSaver } from "./saver.js";

// Autoguardado con revisión (control optimista). Estados: idle | dirty | saving | saved | offline | conflict | error
// Los cambios pendientes NO se descartan al desmontar el componente (p. ej. al cambiar de sección o eliminar
// una tarjeta): se guardan de inmediato. Los guardados se serializan (nunca dos PUT simultáneos del mismo recurso).
export function useAutosave({ value, loaded, save, delay = 1200 }) {
  const [status, setStatus] = useState("idle");
  const [message, setMessage] = useState("");
  const [conflict, setConflict] = useState(null);
  const first = useRef(true);
  const saveRef = useRef(save);
  saveRef.current = save;

  const saverRef = useRef(null);
  if (!saverRef.current) {
    saverRef.current = createSaver({
      delay,
      save: () => saveRef.current(),
      onStatus: (st, e) => {
        if (st !== "error") { setStatus(st); if (st === "saved") setMessage(""); return; }
        if (e?.status === 409 && e?.code === "revision_obsoleta") { setStatus("conflict"); setConflict(e.detail?.current || null); setMessage(e.message); }
        else if (e?.status === 0) { setStatus("offline"); setMessage(e.message); }
        else { setStatus("error"); setMessage(e?.message || "No se pudo guardar."); }
      },
    });
  }

  useEffect(() => {
    if (!loaded) return;
    if (first.current) { first.current = false; return; }       // no guardar al cargar
    saverRef.current.schedule();
  }, [value, loaded]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    saverRef.current.revive();
    return () => saverRef.current.dispose();                    // al desmontar: guardar lo pendiente, no cancelarlo
  }, []);

  return {
    status, message, conflict,
    saveNow: () => saverRef.current.saveNow(),
    flush: () => saverRef.current.flush(),
    clearConflict: () => { setConflict(null); setStatus("idle"); },
  };
}
