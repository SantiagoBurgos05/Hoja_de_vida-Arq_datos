import { useCallback, useEffect, useRef, useState } from "react";

// Autoguardado con revisión (control optimista). Estados: idle | dirty | saving | saved | offline | conflict | error
export function useAutosave({ value, loaded, save, delay = 1200 }) {
  const [status, setStatus] = useState("idle");
  const [message, setMessage] = useState("");
  const [conflict, setConflict] = useState(null);
  const timer = useRef();
  const first = useRef(true);
  const latest = useRef(value);
  latest.current = value;

  const run = useCallback(async () => {
    setStatus("saving");
    try {
      await save(latest.current);
      setStatus("saved"); setMessage("");
    } catch (e) {
      if (e.status === 409) { setStatus("conflict"); setConflict(e.detail?.current || null); setMessage(e.message); }
      else if (e.status === 0) { setStatus("offline"); setMessage(e.message); }
      else { setStatus("error"); setMessage(e.message); }
    }
  }, [save]);

  useEffect(() => {
    if (!loaded) return;
    if (first.current) { first.current = false; return; }       // no guardar al cargar
    setStatus("dirty");
    clearTimeout(timer.current);
    timer.current = setTimeout(run, delay);
    return () => clearTimeout(timer.current);
  }, [value, loaded]); // eslint-disable-line react-hooks/exhaustive-deps

  return { status, message, conflict, saveNow: run, clearConflict: () => { setConflict(null); setStatus("idle"); } };
}
