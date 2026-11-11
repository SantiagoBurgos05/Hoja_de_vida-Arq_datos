"""Mantenimiento operativo (recuperación ante fallos y Data Lake).

Una sola operación idempotente, pensada para ejecutarse de forma programada (workflow de GitHub) o a mano:
  1. expirar cargas interrumpidas (`uploading` antiguo -> `rejected`)
  2. completar borrados pendientes (`delete_pending`)
  3. retención: eliminar temporales/rechazados antiguos
  4. conciliar Silver con los registros operacionales vigentes (retira huérfanas)
  5. reconstruir Gold (umbral por personas distintas)
Cada paso se ejecuta aunque otro falle; el resultado y los errores quedan en `maintenance_runs`.
"""
from __future__ import annotations
import time
from datetime import datetime, timezone
from ...core.db import get_db
from ..documents import service as documents
from ..lake import service as lake


def _now():
    return datetime.now(timezone.utc)


def reconcile_silver() -> dict:
    db = get_db()
    owners = set(db.education_records.distinct("user_id")) | set(db.work_records.distinct("user_id")) | \
        set(db.silver_records.distinct("owner_id"))
    records = removed = 0
    for o in owners:
        r = lake.refresh_silver(o)
        records += r["silver_records"]
        removed += r["removed"]
    return {"owners": len(owners), "silver_records": records, "removed": removed}


STEPS = [
    ("expire_stale_uploads", documents.expire_stale_uploads),
    ("retry_pending_deletes", documents.retry_pending_deletes),
    ("cleanup_stale", documents.cleanup_stale),
    ("reconcile_silver", reconcile_silver),
    ("build_gold", lake.build_gold),
]


def run_maintenance(trigger: str = "manual", skip: tuple[str, ...] = ()) -> dict:
    started = _now()
    results, ok = {}, True
    for name, fn in STEPS:
        if name in skip:
            results[name] = {"skipped": True}
            continue
        t = time.perf_counter()
        try:
            results[name] = {"ok": True, **fn()}
        except Exception as e:                      # un paso fallido no impide los demás
            ok = False
            results[name] = {"ok": False, "error": f"{type(e).__name__}: {e}"[:300]}
        results[name]["ms"] = round((time.perf_counter() - t) * 1000)
    run = {"started_at": started, "finished_at": _now(), "trigger": trigger, "ok": ok, "results": results}
    run_id = get_db().maintenance_runs.insert_one(run).inserted_id
    return {"id": str(run_id), "ok": ok, "trigger": trigger, "started_at": started.isoformat(), "results": results}


def last_runs(limit: int = 10) -> list[dict]:
    out = []
    for r in get_db().maintenance_runs.find({}).sort("started_at", -1).limit(limit):
        out.append({"id": str(r["_id"]), "ok": r["ok"], "trigger": r["trigger"], "started_at": r["started_at"].isoformat(),
                    "results": r.get("results", {})})
    return out
