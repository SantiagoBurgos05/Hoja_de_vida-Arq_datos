#!/usr/bin/env python3
"""Comprobación de Supabase Storage para la API, SIN mostrar secretos.

Lee SUPABASE_URL, SUPABASE_SERVICE_KEY y SUPABASE_BUCKET del entorno o de `.env` (ignorado por git) y,
con el mismo adaptador que usa la API (`SupabaseStorage`), comprueba:
  1. que el bucket exista y sea PRIVADO
  2. carga de un PDF sintético
  3. tamaño (HEAD) igual al cargado
  4. descarga idéntica byte a byte (misma huella SHA-256)
  5. que SIN credenciales el objeto no sea accesible (ni por URL pública ni autenticada)
  6. borrado y que el objeto ya no exista
  7. que el bucket admita la evidencia JSON de las verificaciones de entidades
Solo toca la clave `check/<aleatorio>.pdf`, que borra al final. La clave de servicio nunca se imprime.

Uso:  python scripts/check_supabase.py
"""
from __future__ import annotations
import hashlib
import os
import sys
import time
import uuid
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))

from check_atlas import load_env_file  # noqa: E402

PDF = b"%PDF-1.4\n% documento sintetico de comprobacion\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n" + b"x" * 512


def main(transport=None) -> int:
    load_env_file(ROOT / ".env")
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_SERVICE_KEY", "").strip()
    bucket = os.getenv("SUPABASE_BUCKET", "certificados").strip()
    missing = [n for n, v in (("SUPABASE_URL", url), ("SUPABASE_SERVICE_KEY", key)) if not v]
    if missing:
        print("FALTA  " + ", ".join(missing) + ": defínalas en .env (raíz del proyecto).")
        return 2
    if not url.startswith("https://"):
        print("FALLA  SUPABASE_URL debe empezar con https:// (la Project URL de Supabase).")
        return 2
    print(f"Destino: host {urlparse(url).hostname}, bucket {bucket} (la clave no se muestra)")

    import httpx
    from app.core.storage import SupabaseStorage

    st = SupabaseStorage(url, key, bucket, transport=transport)
    obj = f"check/{uuid.uuid4().hex}.pdf"
    base = url.rstrip("/") + "/storage/v1"
    ok_all = True

    def step(name, fn):
        nonlocal ok_all
        t = time.perf_counter()
        try:
            msg = fn() or ""
            print(f"OK     {name} ({round((time.perf_counter() - t) * 1000)} ms) {msg}")
            return True
        except Exception as e:
            ok_all = False
            print(f"FALLA  {name}: {type(e).__name__}: {str(e).replace(key, '<CLAVE>')[:300]}")
            return False

    def bucket_privado():
        with st._c() as c:
            r = c.get(f"{base}/bucket/{bucket}")
        if r.status_code in (401, 403):
            raise AssertionError(f"HTTP {r.status_code}: la clave no tiene permisos de servicio (¿copió la anon/publishable?)")
        if r.status_code != 200:
            raise AssertionError(f"HTTP {r.status_code}: ¿existe el bucket «{bucket}»?")
        if r.json().get("public") is not False:
            raise AssertionError("el bucket es PÚBLICO: debe ser privado")
        return "existe y es privado"

    if not step("bucket", bucket_privado):
        print("\nRevise: Project URL, clave de servicio (service_role o secret) y nombre del bucket.")
        return 1

    uploaded = step("carga", lambda: st.put(obj, PDF, "application/pdf"))
    if uploaded:
        def tamano():
            n = st.size(obj)
            assert n == len(PDF), f"tamaño informado {n}, esperado {len(PDF)}"
            return f"{n} bytes"
        step("tamaño (HEAD)", tamano)

        def descarga():
            data = st.get(obj)
            assert hashlib.sha256(data).hexdigest() == hashlib.sha256(PDF).hexdigest(), "el contenido descargado no coincide"
            return "idéntica (SHA-256)"
        step("descarga", descarga)

        def sin_credenciales():
            with httpx.Client(timeout=20, transport=transport) as c:
                pub = c.get(f"{base}/object/public/{bucket}/{obj}")
                auth = c.get(f"{base}/object/authenticated/{bucket}/{obj}")
            leaked = [n for n, r in (("pública", pub), ("autenticada", auth)) if r.status_code == 200]
            assert not leaked, f"el objeto es accesible sin credenciales por la ruta {', '.join(leaked)}"
            return f"denegado (HTTP {pub.status_code} / {auth.status_code})"
        step("acceso sin credenciales", sin_credenciales)

        def borrado():
            st.delete(obj)
            assert st.size(obj) is None, "el objeto sigue existiendo después de borrarlo"
            return "borrado y ausente"
        step("borrado", borrado)

    def evidencia_json():
        # La API también guarda en el bucket la evidencia de cada verificación de entidad (application/json).
        k = f"check/{uuid.uuid4().hex}.json"
        try:
            st.put(k, b'{"sintetico": true}', "application/json")
        except Exception as e:
            raise AssertionError("el bucket rechaza JSON: en sus restricciones de tipo agregue application/json "
                                 "(o quítelas); sin esto ninguna verificación de entidad se concede") from e
        st.delete(k)
        return "admitida y borrada"
    step("evidencia de verificación (JSON)", evidencia_json)

    print("\nResultado:", "todo correcto" if ok_all else "hay fallos (vea arriba)")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
