"""Mantenimiento por línea de comandos (misma operación que POST /api/admin/maintenance).

Uso (con las variables de entorno de la API: MONGO_URI, MONGO_DB, STORAGE_BACKEND, ...):
    cd backend && python -m app.maintenance
Salida: JSON con el resultado de cada paso. Código 0 si todo terminó bien; 1 si algún paso falló.
"""
from __future__ import annotations
import json
import sys
from .core.db import close_client, init_db
from .modules.admin.service import run_maintenance


def main() -> int:
    init_db()
    try:
        r = run_maintenance("cli")
    finally:
        close_client()
    print(json.dumps(r, indent=2, ensure_ascii=False))
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
