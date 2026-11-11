from __future__ import annotations
from fastapi import APIRouter, Header, HTTPException
from ...core.config import get_settings
from ...core.db import get_db
from ...core.deps import AdminOnly, CurrentUser, oid
from . import service

router = APIRouter(prefix="/api/lake", tags=["lake"])


@router.get("/catalog")
def catalog(user=CurrentUser):
    """Catálogo del propio usuario (Bronze/Silver). Sin contenido, solo metadatos y linaje."""
    out = []
    for o in get_db().lake_objects.find({"owner_id": user["_id"]}).sort("created_at", 1):
        out.append({"id": str(o["_id"]), "layer": o["layer"], "kind": o["kind"], "sha256": o.get("sha256"),
                    "size": o.get("size"), "deleted": o.get("deleted", False),
                    "derived_from": [str(x) for x in o.get("derived_from", [])],
                    "created_at": o["created_at"].isoformat()})
    return out


@router.get("/lineage/{object_id}")
def lineage(object_id: str, user=CurrentUser):
    res = service.lineage(oid(object_id), user["_id"])
    if not res:
        raise HTTPException(404, "No encontrado")
    return res


@router.post("/refresh-silver")
def refresh(user=CurrentUser):
    return service.refresh_silver(user["_id"])


@router.get("/gold")
def gold(user=CurrentUser):
    return [{"metric": g["metric"], "dimension": g["dimension"], "value": g["value"], "personas": g.get("personas"), "k": g.get("k")}
            for g in get_db().gold_metrics.find({}).sort([("metric", 1), ("dimension", 1)])]


@router.post("/build-gold", dependencies=[AdminOnly])
def build_gold():
    """Operación de administración: requiere ADMIN_TOKEN configurado (desactivada si está vacío)."""
    return service.build_gold()
