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


SILVER_KIND = {"education_higher": "education", "work": "work"}
_OPERATIONAL = {"education": "education_records", "work": "work_records"}


def _silver_data(db, owner_id, kind: str, rec: dict) -> tuple[dict, list]:
    """Proyección estandarizada (mayúsculas sin tildes, fechas ISO) SIN identificadores personales directos
    (documento, dirección, teléfono, correo, nombres)."""
    docs = [d["lake_object_id"] for d in db.documents.find({"user_id": owner_id, "record_id": rec["_id"], "document_status": "ready",
                                                             "lake_object_id": {"$ne": None}})]
    org = db.organizations.find_one({"_id": rec.get("organization_id")}) if rec.get("organization_id") else None
    common = {"fuente_entidad": org["source"] if org else None, "municipio_entidad": _norm(org["municipio"]) if org else None,
              "organization_status": rec.get("organization_status"), "record_status": rec.get("record_status")}
    if kind == "education":
        data = {"modalidad": rec.get("modalidad"), "graduado": rec.get("graduado"), "semestres": rec.get("semestres_aprobados"),
                "anio_terminacion": (rec.get("terminacion") or {}).get("anio"), "nombre_estudios": _norm(rec.get("nombre_estudios"))}
    else:
        data = {"categoria_tiempo": rec.get("categoria_tiempo"), "tipo_entidad": rec.get("tipo_entidad"),
                "fecha_ingreso": rec.get("fecha_ingreso"), "fecha_retiro": rec.get("fecha_retiro"), "es_actual": rec.get("es_actual")}
    return {**data, **common}, docs


def silver_sync_record(owner_id, record_type: str, record_id) -> None:
    """Sincroniza Silver con UN registro operacional: lo actualiza si existe y lo retira si ya no existe.
    Se invoca en cada creación, modificación, cambio de estado y eliminación del registro."""
    kind = SILVER_KIND.get(record_type)
    if kind is None:
        return
    db = get_db()
    rec = db[_OPERATIONAL[kind]].find_one({"_id": record_id, "user_id": owner_id})
    if rec is None:
        silver_drop_record(owner_id, kind, str(record_id))
        return
    data, docs = _silver_data(db, owner_id, kind, rec)
    silver_upsert(owner_id, kind, str(rec["_id"]), data, docs)


def refresh_silver(owner_id) -> dict:
    """Reconstruye Silver del usuario a partir de los datos operacionales vigentes y retira copias huérfanas."""
    db = get_db()
    n = 0
    live: dict[str, set[str]] = {}
    for kind, coll in _OPERATIONAL.items():
        live[kind] = set()
        for rec in db[coll].find({"user_id": owner_id}):
            data, docs = _silver_data(db, owner_id, kind, rec)
            silver_upsert(owner_id, kind, str(rec["_id"]), data, docs)
            live[kind].add(str(rec["_id"]))
            n += 1
    removed = 0
    for s in list(db.silver_records.find({"owner_id": owner_id}, {"kind": 1, "source_id": 1})):
        if s["source_id"] not in live.get(s["kind"], set()):
            silver_drop_record(owner_id, s["kind"], s["source_id"])
            removed += 1
    return {"silver_records": n, "removed": removed}


def silver_drop_record(owner_id, kind: str, source_id: str) -> None:
    """Retira la copia Silver de un registro eliminado y marca su objeto de catálogo como eliminado (el linaje conserva el hecho)."""
    db = get_db()
    cur = db.silver_records.find_one_and_delete({"owner_id": owner_id, "kind": kind, "source_id": source_id})
    if cur and cur.get("lake_object_id"):
        db.lake_objects.update_one({"_id": cur["lake_object_id"]}, {"$set": {"deleted": True, "deleted_at": _now()}})


# ------------------------------------------------------------------- Gold
def build_gold() -> dict:
    """Agrega Silver de TODOS los usuarios. Sin user_id ni datos personales.
    Umbral de privacidad: una celda se publica solo si la aportan al menos k PERSONAS distintas
    (no k registros: una persona con muchos registros no supera el umbral por sí sola)."""
    k = get_settings().gold_k_anonymity
    db = get_db()
    run_id = ObjectId()
    inputs = list(db.silver_records.find({}, {"owner_id": 1, "kind": 1, "data": 1, "lake_object_id": 1}))
    in_ids = [i["lake_object_id"] for i in inputs if i.get("lake_object_id")]
    records: dict[tuple[str, str], int] = {}
    owners: dict[tuple[str, str], set] = {}

    def add(cell: tuple[str, str], owner) -> None:
        records[cell] = records.get(cell, 0) + 1
        owners.setdefault(cell, set()).add(owner)

    for r in inputs:
        d, owner = r["data"], r["owner_id"]
        if r["kind"] == "education":
            add(("educacion_por_modalidad", str(d.get("modalidad"))), owner)
        else:
            add(("experiencia_por_categoria", str(d.get("categoria_tiempo"))), owner)
        add(("registros_por_estado_entidad", f'{r["kind"]}:{d.get("organization_status")}'), owner)
    db.gold_metrics.delete_many({})
    written = suppressed = 0
    for cell in sorted(records):
        metric, dim = cell
        personas = len(owners[cell])
        if personas < k:
            suppressed += 1
            continue
        db.gold_metrics.insert_one({"metric": metric, "dimension": dim, "value": records[cell], "personas": personas,
                                    "computed_at": _now(), "run_id": run_id, "k": k})
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
