"""Soportes (certificados). Protocolo de consistencia:

  1 validar (tamaño, firma de archivo, propietario, entidad verificada)
  2 idempotencia / duplicado
  3 insertar metadatos en estado `uploading`
  4 escribir en Storage privado
  5 comprobar que el objeto existe y su tamaño coincide
  6 catalogar en Bronze y pasar a `ready`
Cualquier fallo antes de 6 deja el documento en `rejected` (nunca `ready`) y limpia el objeto.
Borrado coordinado: delete_pending -> Storage -> catálogo -> metadatos; si Storage falla, queda delete_pending (reintentable).
"""
from __future__ import annotations
import re
from datetime import datetime, timedelta, timezone
from bson import ObjectId
from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError
from ...core.config import get_settings
from ...core.db import get_db
from ...core.errors import bad, conflict, not_found
from ...core.storage import StorageError, get_storage
from ..lake import service as lake
from ..resume import service as resume

ALLOWED = {"application/pdf": "pdf", "image/jpeg": "jpg", "image/png": "png"}


def _now():
    return datetime.now(timezone.utc)


def sniff(data: bytes) -> str | None:
    """Detecta el tipo real por firma (no confiamos en extensión ni en Content-Type)."""
    if data.startswith(b"%PDF-"):
        return "application/pdf"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    return None


def safe_name(name: str | None, ext: str) -> str:
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", (name or "certificado").rsplit(".", 1)[0])[:60].strip("._") or "certificado"
    return f"{base}.{ext}"


def public(d: dict) -> dict:
    return {"id": str(d["_id"]), "record_type": d["record_type"], "record_id": str(d["record_id"]),
            "filename": d.get("filename"), "content_type": d.get("content_type"), "size": d["size"], "sha256": d["sha256"],
            "document_status": d["document_status"], "authenticity": d["authenticity"],
            "organization_id": str(d["organization_id"]) if d.get("organization_id") else None,
            "reason": d.get("reason"), "created_at": d["created_at"].isoformat()}


def upload(user_id, record_type: str, record_id: ObjectId, filename: str | None, declared_type: str | None,
           data: bytes, idempotency_key: str | None) -> tuple[dict, str]:
    """Devuelve (documento, resultado) con resultado in {created, idempotent, duplicate}."""
    db, s = get_db(), get_settings()
    if not data:
        raise bad("archivo_vacio", "El archivo está vacío.")
    if len(data) > s.max_upload_bytes:
        raise bad("archivo_grande", "El archivo supera 5 MB.", 413)
    real = sniff(data)
    if real is None:
        raise bad("tipo_no_permitido", "Solo se permiten PDF, JPG o PNG.", 415)
    if declared_type and declared_type.split(";")[0].strip().lower() not in ALLOWED:
        raise bad("tipo_no_permitido", "Solo se permiten PDF, JPG o PNG.", 415)
    if declared_type and declared_type.split(";")[0].strip().lower() != real:
        raise bad("tipo_inconsistente", "El contenido no coincide con el tipo declarado.", 415)

    rec = resume.get_record(user_id, record_type, record_id)       # 404 si es ajeno
    if rec.get("organization_status") != "verified" or not rec.get("organization_id"):
        raise conflict("entidad_no_verificada", "Verifique la entidad antes de cargar certificados.")

    h = lake.sha256(data)
    if idempotency_key:
        prev = db.documents.find_one({"user_id": user_id, "idempotency_key": idempotency_key})
        if prev:
            if prev["sha256"] != h:
                raise conflict("idempotency_key_reutilizada", "Esa clave de idempotencia ya se usó con otro archivo.")
            return prev, "idempotent"
    dup = db.documents.find_one({"user_id": user_id, "record_id": record_id, "sha256": h, "document_status": {"$in": ["uploading", "ready"]}})
    if dup:
        return dup, "duplicate"

    doc_id = ObjectId()
    ext = ALLOWED[real]
    key = f"bronze/{user_id}/certificates/{doc_id}.{ext}"       # la clave no contiene nombre de archivo del usuario
    other = db.documents.find_one({"user_id": user_id, "sha256": h, "document_status": "ready"})
    doc = {"_id": doc_id, "user_id": user_id, "record_type": record_type, "record_id": record_id,
           "organization_id": rec["organization_id"], "filename": safe_name(filename, ext), "content_type": real,
           "size": len(data), "sha256": h, "storage_key": key, "document_status": "uploading",
           "authenticity": "not_validated", "idempotency_key": idempotency_key, "lake_object_id": None,
           "same_content_as": other["_id"] if other else None, "created_at": _now()}
    if not idempotency_key:
        doc.pop("idempotency_key")
    try:
        db.documents.insert_one(doc)
    except DuplicateKeyError:                                      # carrera: otra petición idéntica ganó
        again = db.documents.find_one({"user_id": user_id, "record_id": record_id, "sha256": h,
                                       "document_status": {"$in": ["uploading", "ready"]}}) or \
                (db.documents.find_one({"user_id": user_id, "idempotency_key": idempotency_key}) if idempotency_key else None)
        if again:
            return again, "idempotent" if idempotency_key else "duplicate"
        raise

    def reject(reason: str):
        try:
            get_storage().delete(key)
        except Exception:
            pass
        db.documents.update_one({"_id": doc_id}, {"$set": {"document_status": "rejected", "reason": reason, "rejected_at": _now()}})

    try:
        get_storage().put(key, data, real)
        sz = get_storage().size(key)
    except Exception as e:                                         # StorageError, red, etc.
        reject(f"almacenamiento: {type(e).__name__}")
        raise HTTPException(502, {"code": "almacenamiento_fallo", "message": "No se pudo guardar el archivo. No quedó registrado como cargado; intente de nuevo."})
    if sz != len(data):
        reject("tamaño no coincide tras escritura")
        raise HTTPException(502, {"code": "almacenamiento_inconsistente", "message": "El archivo no se verificó tras guardarse. Intente de nuevo."})

    lo = db.lake_objects.insert_one({"layer": "bronze", "kind": "certificate", "owner_id": user_id, "storage_key": key,
                                     "sha256": h, "size": len(data), "content_type": real, "source_ref": {"document_id": str(doc_id)},
                                     "derived_from": [], "created_at": _now(), "deleted": False}).inserted_id
    db.documents.update_one({"_id": doc_id}, {"$set": {"document_status": "ready", "lake_object_id": lo}})
    resume.refresh_status(user_id, record_type, record_id)
    return db.documents.find_one({"_id": doc_id}), "created"


def get_owned(user_id, doc_id: ObjectId) -> dict:
    d = get_db().documents.find_one({"_id": doc_id, "user_id": user_id})
    if not d:
        raise not_found()
    return d


def read_bytes(user_id, doc_id: ObjectId) -> tuple[dict, bytes]:
    d = get_owned(user_id, doc_id)
    if d["document_status"] != "ready":
        raise not_found()
    try:
        data = get_storage().get(d["storage_key"])
    except StorageError:
        raise HTTPException(502, {"code": "almacenamiento_no_disponible", "message": "No se pudo recuperar el archivo."})
    if lake.sha256(data) != d["sha256"]:
        raise HTTPException(502, {"code": "integridad", "message": "El archivo almacenado no coincide con su huella."})
    return d, data


def list_docs(user_id, record_type: str | None, record_id: ObjectId | None) -> list[dict]:
    q: dict = {"user_id": user_id, "document_status": {"$in": ["ready", "delete_pending"]}}
    if record_type:
        q["record_type"] = record_type
    if record_id:
        q["record_id"] = record_id
    return list(get_db().documents.find(q).sort("created_at", 1))


def delete(user_id, doc_id: ObjectId) -> None:
    db = get_db()
    d = get_owned(user_id, doc_id)
    db.documents.update_one({"_id": doc_id}, {"$set": {"document_status": "delete_pending"}})
    try:
        if d.get("storage_key"):
            get_storage().delete(d["storage_key"])
    except Exception:
        raise HTTPException(502, {"code": "borrado_pendiente", "message": "No se pudo eliminar el archivo; quedó pendiente y puede reintentar."})
    if d.get("lake_object_id"):
        lake.bronze_tombstone(d["lake_object_id"])
    db.documents.delete_one({"_id": doc_id})
    if d["record_type"] != "education_basic":
        resume.refresh_status(user_id, d["record_type"], d["record_id"])


def delete_for_record(user_id, record_type: str, record_id: ObjectId) -> None:
    for d in get_db().documents.find({"user_id": user_id, "record_type": record_type, "record_id": record_id}):
        delete(user_id, d["_id"])


def cleanup_stale(older_than_days: float | None = None) -> dict:
    """Retención de evidencia temporal: elimina `uploading`/`rejected` más antiguos que el plazo (30 días por defecto)."""
    days = get_settings().temp_retention_days if older_than_days is None else older_than_days
    cutoff = _now() - timedelta(days=days)
    db = get_db()
    n = 0
    for d in db.documents.find({"document_status": {"$in": ["uploading", "rejected"]}, "created_at": {"$lt": cutoff}}):
        try:
            if d.get("storage_key"):
                get_storage().delete(d["storage_key"])
        except Exception:
            continue
        db.documents.delete_one({"_id": d["_id"]})
        n += 1
    return {"removed": n}
