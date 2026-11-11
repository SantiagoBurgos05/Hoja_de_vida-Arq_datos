from __future__ import annotations
from datetime import datetime, timezone, date
from bson import ObjectId
from pymongo import ReturnDocument
from ...core.db import get_db
from ...core.errors import conflict, not_found
from ..lake import service as lake

RECORD_COLLECTIONS = {"education_higher": "education_records", "work": "work_records", "education_basic": "resumes"}
REQUIRED = {
    "education_higher": ("modalidad", "nombre_estudios", "institucion_declarada"),
    "work": ("empresa_declarada", "fecha_ingreso", "cargo"),
}
# Campos cuyo cambio hace que la verificación de la entidad deje de corresponder al registro.
# work.tipo_entidad decide la fuente (pública -> SIGEP, privada -> RUES): una verificación hecha con
# la fuente anterior no puede seguir asociada al registro.
VERIFICATION_FIELDS = {"work": ("tipo_entidad",), "education_higher": ()}


def _now():
    return datetime.now(timezone.utc)


def _plain(d: dict) -> dict:
    """Pydantic -> dict apto para Mongo (fechas ISO)."""
    def conv(v):
        if isinstance(v, date):
            return v.isoformat()
        if isinstance(v, dict):
            return {k: conv(x) for k, x in v.items()}
        if isinstance(v, list):
            return [conv(x) for x in v]
        return v
    return conv(d)


def serialize(doc: dict | None) -> dict | None:
    if doc is None:
        return None
    out = {}
    for k, v in doc.items():
        if isinstance(v, ObjectId):
            out["id" if k == "_id" else k] = str(v)
        elif isinstance(v, datetime):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out


def empty_resume(user_id) -> dict:
    return {
        "user_id": user_id, "revision": 0,
        "personal": {}, "education_basic": {}, "languages": [],
        "organization_id": None, "organization_status": "pending",
        "created_at": _now(), "updated_at": _now(),
    }


def get_or_create_resume(user_id) -> dict:
    db = get_db()
    r = db.resumes.find_one({"user_id": user_id})
    if r:
        return r
    db.resumes.update_one({"user_id": user_id}, {"$setOnInsert": empty_resume(user_id)}, upsert=True)
    return db.resumes.find_one({"user_id": user_id})


def save_resume(user_id, data: dict) -> dict:
    """Guardado con control optimista. revision distinta => 409 y se devuelve la versión del servidor."""
    get_or_create_resume(user_id)
    rev = data.pop("revision")
    r = get_db().resumes.find_one_and_update(
        {"user_id": user_id, "revision": rev},
        {"$set": {**_plain(data), "updated_at": _now()}, "$inc": {"revision": 1}},
        return_document=ReturnDocument.AFTER,
    )
    if r is None:
        cur = get_db().resumes.find_one({"user_id": user_id})
        raise conflict("revision_obsoleta", "La hoja de vida cambió en otra sesión. Revise la versión actual.",
                       current=serialize(cur))
    return r


def _ready_docs(user_id, record_type, record_id) -> int:
    return get_db().documents.count_documents(
        {"user_id": user_id, "record_type": record_type, "record_id": record_id, "document_status": "ready"})


def derive_status(user_id, record_type: str, rec: dict) -> str:
    rid = rec["_id"] if "_id" in rec else None
    if rid is not None and _ready_docs(user_id, record_type, rid) > 0:
        return "supported"
    if all(rec.get(f) not in (None, "") for f in REQUIRED[record_type]):
        return "declared"
    return "draft"


def refresh_status(user_id, record_type: str, record_id) -> str:
    """Recalcula record_status (p. ej. al adjuntar/eliminar un soporte)."""
    if record_type == "education_basic":
        return "declared"  # la educación básica vive en el documento resumes; sin record_status propio
    coll = get_db()[RECORD_COLLECTIONS[record_type]]
    rec = coll.find_one({"_id": record_id, "user_id": user_id})
    if not rec:
        return "draft"
    st = derive_status(user_id, record_type, rec)
    coll.update_one({"_id": record_id}, {"$set": {"record_status": st}})
    lake.silver_sync_record(user_id, record_type, record_id)
    return st


def list_records(user_id, record_type: str) -> list[dict]:
    return list(get_db()[RECORD_COLLECTIONS[record_type]].find({"user_id": user_id}).sort("created_at", 1))


def get_record(user_id, record_type: str, record_id: ObjectId) -> dict:
    rec = get_db()[RECORD_COLLECTIONS[record_type]].find_one({"_id": record_id, "user_id": user_id})
    if not rec:
        raise not_found()  # propietario ajeno == inexistente
    return rec


def create_record(user_id, record_type: str, data: dict) -> dict:
    resume = get_or_create_resume(user_id)
    data.pop("revision", None)
    doc = {**_plain(data), "user_id": user_id, "resume_id": resume["_id"], "revision": 0,
           "organization_id": None, "organization_status": "pending",
           "created_at": _now(), "updated_at": _now()}
    doc["record_status"] = derive_status(user_id, record_type, doc)
    r = get_db()[RECORD_COLLECTIONS[record_type]].insert_one(doc)
    lake.silver_sync_record(user_id, record_type, r.inserted_id)
    return get_db()[RECORD_COLLECTIONS[record_type]].find_one({"_id": r.inserted_id})


def update_record(user_id, record_type: str, record_id: ObjectId, data: dict) -> dict:
    coll = get_db()[RECORD_COLLECTIONS[record_type]]
    cur = get_record(user_id, record_type, record_id)
    rev = data.pop("revision", None)
    if rev is not None and rev != cur["revision"]:
        raise conflict("revision_obsoleta", "El registro cambió en otra sesión.", current=serialize(cur))
    upd = {**_plain(data)}
    changed = [f for f in VERIFICATION_FIELDS.get(record_type, ()) if f in upd and upd[f] != cur.get(f)]
    if changed and (cur.get("organization_id") or cur.get("organization_status") != "pending"):
        if get_db().documents.count_documents({"user_id": user_id, "record_type": record_type, "record_id": record_id,
                                               "document_status": {"$in": ["uploading", "ready", "delete_pending"]}}):
            raise conflict("soportes_existentes",
                           "Elimine los soportes antes de cambiar el tipo de entidad: están asociados a la entidad verificada.")
        upd.update({"organization_id": None, "organization_status": "pending"})   # la verificación anterior deja de aplicar
    merged = {**cur, **upd}
    status = derive_status(user_id, record_type, merged)
    flt = {"_id": record_id, "user_id": user_id, "revision": cur["revision"]}
    r = coll.find_one_and_update(flt, {"$set": {**upd, "record_status": status, "updated_at": _now()},
                                       "$inc": {"revision": 1}}, return_document=ReturnDocument.AFTER)
    if r is None:
        raise conflict("revision_obsoleta", "El registro cambió en otra sesión.",
                       current=serialize(coll.find_one({"_id": record_id})))
    lake.silver_sync_record(user_id, record_type, record_id)
    return r


def delete_record(user_id, record_type: str, record_id: ObjectId) -> None:
    from ..documents import service as docs  # import tardío: evita ciclo
    get_record(user_id, record_type, record_id)
    docs.delete_for_record(user_id, record_type, record_id)  # borrado coordinado de soportes
    get_db()[RECORD_COLLECTIONS[record_type]].delete_one({"_id": record_id, "user_id": user_id})
    lake.silver_sync_record(user_id, record_type, record_id)   # retira la copia Silver: Gold no cuenta registros eliminados
