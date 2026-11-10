from __future__ import annotations
import json
from datetime import datetime, timezone
from bson import ObjectId
from ...core.db import get_db
from ...core.errors import bad, conflict
from ..resume import service as resume
from ..lake import service as lake
from .connectors.base import ConnectorDisabled, ConnectorError
from .connectors.registry import get_connector

# Fuentes válidas por tipo de registro
SOURCES_BY_RECORD = {"education_basic": {"due"}, "education_higher": {"snies", "siet"}, "work": {"rues", "sigep"}}


def _now():
    return datetime.now(timezone.utc)


def search(user_id, source: str, query, municipio, official_id) -> dict:
    """Presenta coincidencias. NO concede verificación: solo lista candidatos."""
    try:
        c = get_connector(source)
    except KeyError:
        raise bad("fuente_desconocida", "Fuente no soportada")
    if not (query or official_id):
        raise bad("criterio_requerido", "Indique nombre (y municipio) o un identificador oficial.")
    try:
        cands = c.search(query, municipio, official_id)
    except ConnectorDisabled as e:
        return {"organization_status": "pending", "candidates": [], "message": str(e) + " Puede continuar con el borrador sin verificación."}
    except ConnectorError as e:
        return {"organization_status": "error", "candidates": [], "message": f"No fue posible consultar la fuente ({e}). El borrador se conserva sin verificación."}
    return {"organization_status": "pending", "candidates": [x.to_dict() for x in cands],
            "message": "Seleccione la entidad correcta y verifíquela." if cands else "Sin coincidencias."}


def _set_record_status(user_id, record_type, record_id, status: str, org_id=None) -> None:
    coll = get_db()[resume.RECORD_COLLECTIONS[record_type]]
    rec = resume.get_record(user_id, record_type, record_id)
    if status != "verified" and rec.get("organization_status") == "verified":
        return  # un fallo transitorio no revoca una verificación previa
    upd = {"organization_status": status, "updated_at": _now()}
    if status == "verified":
        upd["organization_id"] = org_id
    coll.update_one({"_id": record_id}, {"$set": upd})


def verify(user_id, source: str, official_id: str, record_type: str | None, record_id: ObjectId | None) -> dict:
    """Verifica EN EL BACKEND por identificador oficial (consulta exacta). La similitud de nombre no basta."""
    db = get_db()
    if record_type:
        if record_type not in SOURCES_BY_RECORD or source not in SOURCES_BY_RECORD[record_type]:
            raise bad("fuente_incompatible", "La fuente no corresponde a este tipo de registro.")
        if record_id is None:
            raise bad("registro_requerido", "Indique el registro a vincular.")
        rec = resume.get_record(user_id, record_type, record_id)  # 404 si es ajeno
        if record_type == "work":
            expected = "sigep" if rec.get("tipo_entidad") == "publica" else "rues" if rec.get("tipo_entidad") == "privada" else None
            if expected is None:
                raise bad("tipo_entidad_requerido", "Indique si la entidad es pública o privada antes de verificar.")
            if source != expected:
                raise bad("fuente_incompatible", f"Para este tipo de entidad la fuente es {expected.upper()}.")
        if rec.get("organization_status") == "verified" and rec.get("organization_id"):
            cur = db.organizations.find_one({"_id": rec["organization_id"]})
            if cur and (cur["source"], cur["official_id"]) != (source, official_id.strip()) and \
                    db.documents.count_documents({"user_id": user_id, "record_id": record_id, "document_status": "ready"}):
                raise conflict("soportes_existentes", "Elimine los soportes antes de cambiar la entidad verificada.")
    official_id = official_id.strip()
    if not official_id:
        raise bad("identificador_requerido", "Falta el identificador oficial.")
    try:
        c = get_connector(source)
    except KeyError:
        raise bad("fuente_desconocida", "Fuente no soportada")

    def fail(status: str, msg: str) -> dict:
        db.org_verifications.insert_one({"user_id": user_id, "source": source, "official_id": official_id,
                                         "organization_status": status, "queried_at": _now(), "message": msg})
        if record_type:
            _set_record_status(user_id, record_type, record_id, status)
        return {"organization_status": status, "organization": None, "message": msg + " El borrador se conserva sin verificación."}

    try:
        matches, evidence = c.get_by_official_id(official_id)
    except ConnectorDisabled as e:
        return fail("pending", str(e))
    except ConnectorError as e:
        return fail("error", f"La fuente no respondió correctamente ({e}).")
    if len(matches) == 0:
        return fail("not_found", "El identificador no existe en la fuente oficial.")
    if len(matches) > 1:
        return fail("pending", "El identificador devolvió varios registros (ambiguo).")
    m = matches[0]
    raw = json.dumps(evidence, ensure_ascii=False, sort_keys=True).encode()
    ev = lake.bronze_put(user_id, "org_evidence", f"bronze/{user_id}/org_evidence/{lake.sha256(raw)}.json", raw,
                         "application/json", {"source": source, "official_id": official_id})
    org_doc = {"source": source, "official_id": m.official_id, "name": m.name, "municipio": m.municipio,
               "departamento": m.departamento, "estado_registral": m.estado_registral, "status": "verified",
               "verified_at": _now(), "evidence_id": ev["_id"], "evidence_sha256": ev["sha256"]}
    db.organizations.update_one({"source": source, "official_id": m.official_id}, {"$set": org_doc}, upsert=True)
    org = db.organizations.find_one({"source": source, "official_id": m.official_id})
    db.org_verifications.insert_one({"user_id": user_id, "source": source, "official_id": official_id, "organization_id": org["_id"],
                                     "organization_status": "verified", "queried_at": _now(), "evidence_id": ev["_id"]})
    if record_type:
        _set_record_status(user_id, record_type, record_id, "verified", org["_id"])
    out = resume.serialize(org)
    out["evidence_id"] = str(org["evidence_id"])
    return {"organization_status": "verified", "organization": out,
            "message": "Entidad verificada en la fuente oficial. Esto NO acredita que usted haya estudiado o trabajado allí ni autentica ningún certificado."}
