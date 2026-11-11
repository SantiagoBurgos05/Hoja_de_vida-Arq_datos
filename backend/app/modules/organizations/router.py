from __future__ import annotations
from typing import Literal, Optional
from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field
from ...core.config import get_settings
from ...core.deps import CurrentUser, oid
from ...core.ratelimit import enforce
from . import service

router = APIRouter(prefix="/api/organizations", tags=["organizations"])
Source = Literal["snies", "siet", "due", "rues", "sigep"]


class SearchIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: Source
    query: Optional[str] = Field(None, max_length=120)
    municipio: Optional[str] = Field(None, max_length=60)
    official_id: Optional[str] = Field(None, max_length=40)


class VerifyIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: Source
    official_id: str = Field(..., min_length=1, max_length=40)
    record_type: Optional[Literal["education_basic", "education_higher", "work"]] = None
    record_id: Optional[str] = None


@router.get("/{org_id}")
def get_org(org_id: str, user=CurrentUser):
    """Datos públicos de una entidad ya verificada (provienen de fuentes oficiales abiertas)."""
    from ...core.db import get_db
    from ...core.errors import not_found
    from ..resume.service import serialize
    o = get_db().organizations.find_one({"_id": oid(org_id)})
    if not o:
        raise not_found()
    out = serialize(o)
    out["evidence_id"] = str(o["evidence_id"])
    return out


@router.post("/search")
def search(b: SearchIn, user=CurrentUser):
    enforce("lookup", str(user["_id"]), get_settings().rate_lookup)     # cada búsqueda consulta una fuente externa
    return service.search(user["_id"], b.source, b.query, b.municipio, b.official_id)


@router.post("/verify")
def verify(b: VerifyIn, user=CurrentUser):
    enforce("lookup", str(user["_id"]), get_settings().rate_lookup)
    return service.verify(user["_id"], b.source, b.official_id, b.record_type, oid(b.record_id) if b.record_id else None)
