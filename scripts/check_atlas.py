#!/usr/bin/env python3
"""Comprobación de MongoDB Atlas (u otro MongoDB remoto) para la API, SIN mostrar secretos.

Lee MONGO_URI y MONGO_DB del entorno o del archivo `.env` de la raíz (ignorado por git) y comprueba:
  1. conexión y versión del servidor
  2. init_db (crear colecciones con $jsonSchema e índices) — lo mismo que hace la API al arrancar
  3. init_db por SEGUNDA vez (usa collMod: requiere privilegios de dbAdmin en la base)
  4. el validador $jsonSchema rechaza un documento inválido (segunda barrera además de Pydantic)
  5. índices clave: único (source, official_id), parcial de idempotencia y TTL de sesiones
  6. escritura y borrado de un documento sintético
No borra la base ni datos existentes. La cadena de conexión nunca se imprime (solo el host).

Uso:  python scripts/check_atlas.py
"""
from __future__ import annotations
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


def load_env_file(path: Path) -> None:
    """Carga KEY=VALUE de .env sin sobrescribir variables ya definidas (sin dependencias extra)."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.split(" #", 1)[0].strip().strip('"').strip("'")
        os.environ.setdefault(k.strip(), v)


def main() -> int:
    load_env_file(ROOT / ".env")
    uri = os.getenv("MONGO_URI", "")
    if not uri:
        print("FALTA  MONGO_URI: defínala en .env (raíz del proyecto) o en el entorno.")
        return 2
    host = urlparse(uri).hostname or "?"
    dbname = os.getenv("MONGO_DB", "hoja_de_vida")
    print(f"Destino: host {host}, base {dbname} (la cadena completa no se muestra)")

    from pymongo.errors import WriteError
    from app.core import config, db as dbmod

    config.set_settings(config.Settings(mongo_uri=uri, mongo_db=dbname))
    dbmod.close_client()
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
            text = str(e).replace(uri, "<MONGO_URI>")[:300]
            print(f"FALLA  {name}: {type(e).__name__}: {text}")
            return False

    def conectar():
        info = dbmod.get_client().server_info()
        return f"MongoDB {info.get('version')}"

    if not step("conexión", conectar):
        print("\nRevise: usuario/contraseña, Network Access (su IP o 0.0.0.0/0) y que la contraseña no tenga caracteres sin codificar.")
        return 1

    db = dbmod.get_db()
    step("init_db (crear colecciones, validadores e índices)", lambda: dbmod.init_db(db))
    step("init_db repetido (collMod: privilegio dbAdmin)", lambda: dbmod.init_db(db))

    def validador():
        try:
            db.documents.insert_one({"user_id": "x", "record_type": "work", "record_id": "x", "document_status": "ready",
                                     "authenticity": "validated", "sha256": "z", "size": 1})
        except WriteError:
            return "documento inválido rechazado por $jsonSchema"
        raise AssertionError("el servidor ACEPTÓ un documento inválido: $jsonSchema no está activo")
    step("validador $jsonSchema activo", validador)

    def indices():
        def uniq(c):
            return {tuple(k for k, _ in i["key"]) for i in db[c].index_information().values() if i.get("unique")}
        assert ("source", "official_id") in uniq("organizations"), "falta índice único de organizations"
        assert ("user_id", "idempotency_key") in uniq("documents"), "falta índice parcial de idempotencia"
        assert any(i.get("expireAfterSeconds") == 0 for i in db.sessions.index_information().values()), "falta TTL de sesiones"
        return "único, parcial y TTL presentes"
    step("índices clave", indices)

    def escritura():
        r = db.audit_events.insert_one({"event": "check_atlas", "at": datetime.now(timezone.utc), "data": {"sintetico": True}})
        db.audit_events.delete_one({"_id": r.inserted_id})
        return "insertado y borrado un evento sintético"
    step("escritura y borrado", escritura)

    dbmod.close_client()
    print("\nResultado:", "todo correcto" if ok_all else "hay fallos (vea arriba)")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
