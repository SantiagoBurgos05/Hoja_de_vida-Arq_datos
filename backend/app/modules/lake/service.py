"""Data lake lógico sobre MongoDB + almacenamiento privado.

Bronze: originales inmutables (certificados, respuestas crudas de fuentes) en Storage; catálogo en lake_objects.
Silver: datos estandarizados por propietario (silver_records) derivados de Bronze/BD operacional.
Gold:   métricas agregadas SIN datos personales (gold_metrics), con supresión por k-anonimato.
Linaje: lake_objects.derived_from (lista de ids). Duplicados: Bronze por (owner, sha256).
"""
from __future__ import annotations
import hashlib
import json
import unicodedata
from datetime import datetime, timezone
from bson import ObjectId
from ...core.config import get_settings
from ...core.db import get_db
from ...core.storage import get_storage

MONTHS = {}


def _now():
    return datetime.now(timezone.utc)


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


# ----------------------------------------------------------------- Bronze
def bronze_put(owner_id, kind: str, key: str, data: bytes, content_type: str, source_ref: dict | None = None,
               original_name: str | None = None, dedupe: bool = True) -> dict:
    """Guarda el original en Storage y lo cataloga. Devuelve el objeto del catálogo.
    Si ya existe el mismo contenido (owner, sha256, kind) devuelve el existente (control de duplicados)."""
    db = get_db()
    h = sha256(data)
    dup = db.lake_objects.find_one({"layer": "bronze", "owner_id": owner_id, "sha256": h, "kind": kind, "deleted": {"$ne": True}}) if dedupe else None
    if dup:
        dup["duplicate"] = True
        return dup
    get_storage().put(key, data, content_type)
    doc = {"layer": "bronze", "kind": kind, "owner_id": owner_id, "storage_key": key, "sha256": h, "size": len(data),
           "content_type": content_type, "source_ref": source_ref or {}, "original_name": original_name,
           "derived_from": [], "created_at": _now(), "deleted": False}
    doc["_id"] = db.lake_objects.insert_one(doc).inserted_id
    return doc


def bronze_tombstone(object_id) -> None:
    """Borrado coordinado: el objeto Bronze queda marcado como eliminado (el catálogo conserva el hecho, no el contenido)."""
    get_db().lake_objects.update_one({"_id": object_id}, {"$set": {"deleted": True, "deleted_at": _now(), "storage_key": None}})


# ----------------------------------------------------------------- Silver
def _norm(s: str | None) -> str:
    s = unicodedata.normalize("NFKD", (s or "").strip())
    return "".join(c for c in s if not unicodedata.combining(c)).upper()


def silver_upsert(owner_id, kind: str, source_id: str, data: dict, derived_from: list) -> ObjectId:
    db = get_db()
    cur = db.silver_records.find_one({"owner_id": owner_id, "kind": kind, "source_id": source_id})
    if cur and cur.get("lake_object_id"):
        lo_id = cur["lake_object_id"]
        db.lake_objects.update_one({"_id": lo_id}, {"$set": {"derived_from": derived_from, "updated_at": _now()}})
    else:
        lo_id = db.lake_objects.insert_one({"layer": "silver", "kind": kind, "owner_id": owner_id, "derived_from": derived_from,
                                            "source_id": source_id, "created_at": _now(), "deleted": False}).inserted_id
    db.silver_records.update_one({"owner_id": owner_id, "kind": kind, "source_id": source_id},
                                 {"$set": {"data": data, "lake_object_id": lo_id, "updated_at": _now()}}, upsert=True)
    return lo_id


def refresh_silver(owner_id) -> dict:
    """Reconstruye Silver del usuario a partir de datos operacionales (estandarizados: mayúsculas sin tildes, fechas ISO).
    Excluye identificadores personales directos (documento, dirección, teléfono, correo, nombres)."""
    db = get_db()
    n = 0
    for e in db.education_records.find({"user_id": owner_id}):
        docs = [d["lake_object_id"] for d in db.documents.find({"user_id": owner_id, "record_id": e["_id"], "document_status": "ready", "lake_object_id": {"$ne": None}})]
        org = db.organizations.find_one({"_id": e.get("organization_id")}) if e.get("organization_id") else None
        data = {"modalidad": e.get("modalidad"), "graduado": e.get("graduado"), "semestres": e.get("semestres_aprobados"),
                "anio_terminacion": (e.get("terminacion") or {}).get("anio"),
                "nombre_estudios": _norm(e.get("nombre_estudios")),
                "fuente_entidad": org["source"] if org else None, "municipio_entidad": _norm(org["municipio"]) if org else None,
                "organization_status": e.get("organization_status"), "record_status": e.get("record_status")}
        silver_upsert(owner_id, "education", str(e["_id"]), data, docs)
        n += 1
    for w in db.work_records.find({"user_id": owner_id}):
        docs = [d["lake_object_id"] for d in db.documents.find({"user_id": owner_id, "record_id": w["_id"], "document_status": "ready", "lake_object_id": {"$ne": None}})]
        org = db.organizations.find_one({"_id": w.get("organization_id")}) if w.get("organization_id") else None
        data = {"categoria_tiempo": w.get("categoria_tiempo"), "tipo_entidad": w.get("tipo_entidad"),
                "fecha_ingreso": w.get("fecha_ingreso"), "fecha_retiro": w.get("fecha_retiro"), "es_actual": w.get("es_actual"),
                "fuente_entidad": org["source"] if org else None, "municipio_entidad": _norm(org["municipio"]) if org else None,
                "organization_status": w.get("organization_status"), "record_status": w.get("record_status")}
        silver_upsert(owner_id, "work", str(w["_id"]), data, docs)
        n += 1
    return {"silver_records": n}


def silver_drop_record(owner_id, kind: str, source_id: str) -> None:
    get_db().silver_records.delete_one({"owner_id": owner_id, "kind": kind, "source_id": source_id})


# ------------------------------------------------------------------- Gold
def build_gold() -> dict:
    """Agrega Silver de TODOS los usuarios. Sin user_id ni datos personales.
    Celdas con menos de k registros se suprimen (no se escriben)."""
    k = get_settings().gold_k_anonymity
    db = get_db()
    run_id = ObjectId()
    inputs = list(db.silver_records.find({}, {"data": 1, "lake_object_id": 1}))
    in_ids = [i["lake_object_id"] for i in inputs if i.get("lake_object_id")]
    counts: dict[tuple[str, str], int] = {}
    for r in db.silver_records.find({}):
        d = r["data"]
        if r["kind"] == "education":
            counts[("educacion_por_modalidad", str(d.get("modalidad")))] = counts.get(("educacion_por_modalidad", str(d.get("modalidad"))), 0) + 1
        else:
            counts[("experiencia_por_categoria", str(d.get("categoria_tiempo")))] = counts.get(("experiencia_por_categoria", str(d.get("categoria_tiempo"))), 0) + 1
        st = ("registros_por_estado_entidad", f'{r["kind"]}:{d.get("organization_status")}')
        counts[st] = counts.get(st, 0) + 1
    db.gold_metrics.delete_many({})
    written = suppressed = 0
    for (metric, dim), v in sorted(counts.items()):
        if v < k:
            suppressed += 1
            continue
        db.gold_metrics.insert_one({"metric": metric, "dimension": dim, "value": v, "computed_at": _now(), "run_id": run_id, "k": k})
        written += 1
    lo = db.lake_objects.insert_one({"layer": "gold", "kind": "metrics", "owner_id": None, "derived_from": in_ids,
                                     "run_id": run_id, "created_at": _now(), "deleted": False,
                                     "stats": {"written": written, "suppressed": suppressed, "inputs": len(inputs)}})
    return {"run_id": str(run_id), "written": written, "suppressed": suppressed, "inputs": len(inputs), "lake_object_id": str(lo.inserted_id)}


def lineage(object_id: ObjectId, owner_id, depth: int = 5) -> dict:
    """Linaje ascendente de un objeto del propietario."""
    db = get_db()
    o = db.lake_objects.find_one({"_id": object_id, "owner_id": owner_id})
    if not o:
        return {}
    node = {"id": str(o["_id"]), "layer": o["layer"], "kind": o["kind"], "sha256": o.get("sha256"), "derived_from": []}
    if depth > 0:
        for p in o.get("derived_from", []):
            sub = lineage(p, owner_id, depth - 1)
            if sub:
                node["derived_from"].append(sub)
    return node
