#!/usr/bin/env python3
"""Comprobación de la API desplegada (Render) SIN crear usuarios ni datos en la base real.

  1. /api/health responde 200 con db ok (tolera el arranque en frío del plan gratuito)
  2. cabeceras de seguridad (nosniff, no-referrer, no-store)
  3. rutas protegidas sin sesión -> 401; administración sin token -> 403
  4. CORS: el origen de GitHub Pages está permitido y uno ajeno no
  5. (opcional, con ADMIN_TOKEN en el entorno o .env) mantenimiento completo: toca Mongo, Supabase y Gold

Uso:
    python scripts/check_deploy.py https://hoja-de-vida-api.onrender.com --origin https://USUARIO.github.io
El token de administración nunca se imprime.
"""
from __future__ import annotations
import argparse
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from check_atlas import load_env_file  # noqa: E402

import httpx  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("api_url")
    ap.add_argument("--origin", default="", help="URL de GitHub Pages (solo esquema y host)")
    a = ap.parse_args()
    load_env_file(ROOT / ".env")
    api = a.api_url.rstrip("/")
    token = os.getenv("ADMIN_TOKEN", "").strip()
    ok_all = True
    c = httpx.Client(timeout=90, follow_redirects=False)

    def step(name, fn):
        nonlocal ok_all
        t = time.perf_counter()
        try:
            msg = fn() or ""
            print(f"OK     {name} ({round((time.perf_counter() - t) * 1000)} ms) {msg}")
        except Exception as e:
            ok_all = False
            text = str(e).replace(token, "<TOKEN>") if token else str(e)
            print(f"FALLA  {name}: {type(e).__name__}: {text[:300]}")

    def health():
        last = None
        for i in range(6):                       # Render free: hasta ~1 min para despertar
            try:
                r = c.get(f"{api}/api/health")
                if r.status_code == 200 and r.json().get("db") == "ok":
                    return "API y MongoDB disponibles" + (f" (tras {i} reintentos)" if i else "")
                last = f"HTTP {r.status_code} {r.text[:120]}"
            except httpx.HTTPError as e:
                last = type(e).__name__
            time.sleep(15)
        raise AssertionError(f"no saludable: {last}")
    step("health", health)

    def cabeceras():
        h = c.get(f"{api}/api/health").headers
        faltan = [k for k, v in (("x-content-type-options", "nosniff"), ("referrer-policy", "no-referrer"), ("cache-control", "no-store"))
                  if h.get(k) != v]
        assert not faltan, f"faltan o difieren: {faltan}"
        return "nosniff, no-referrer, no-store"
    step("cabeceras de seguridad", cabeceras)

    def protegidas():
        codes = {p: c.get(f"{api}{p}").status_code for p in ("/api/resume", "/api/education", "/api/documents/usage")}
        assert set(codes.values()) == {401}, f"esperado 401: {codes}"
        adm = c.post(f"{api}/api/admin/maintenance").status_code
        assert adm == 403, f"administración sin token devolvió {adm}"
        return "401 sin sesión; 403 sin token de administración"
    step("autorización", protegidas)

    if a.origin:
        def cors():
            origin = a.origin.rstrip("/")
            pre = {"Access-Control-Request-Method": "PUT", "Access-Control-Request-Headers": "authorization,content-type"}
            ok = c.options(f"{api}/api/resume", headers={"Origin": origin, **pre})
            assert ok.headers.get("access-control-allow-origin") == origin, \
                f"el origen {origin} no está permitido (revise CORS_ORIGINS en Render)"
            bad = c.options(f"{api}/api/resume", headers={"Origin": "https://ajeno.example.com", **pre})
            assert bad.headers.get("access-control-allow-origin") is None, "un origen ajeno quedó permitido"
            return f"permitido {origin}; origen ajeno rechazado"
        step("CORS", cors)
    else:
        print("OMITIDO CORS: indique --origin https://USUARIO.github.io")

    if token:
        def mantenimiento():
            r = c.post(f"{api}/api/admin/maintenance", headers={"X-Admin-Token": token})
            res = r.json().get("results", {})
            fallidos = [k for k, v in res.items() if not v.get("ok", True)]
            assert r.status_code == 200 and not fallidos, f"HTTP {r.status_code}; pasos con error: {fallidos} " \
                f"{[res[k].get('error') for k in fallidos]}"
            return "todos los pasos correctos (Mongo, Supabase y Gold)"
        step("mantenimiento (admin)", mantenimiento)
    else:
        print("OMITIDO mantenimiento: agregue ADMIN_TOKEN (el de Render) a .env para probarlo")

    c.close()
    print("\nResultado:", "todo correcto" if ok_all else "hay fallos (vea arriba)")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
